import asyncio
import logging
import random
import re
import time
from collections import OrderedDict
from functools import lru_cache

try:
    import httpx
except Exception:
    httpx = None
import anyio # Added anyio
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException

from ai_module import chat_with_providers, remove_chain_of_thought
from audio_modules.beep_sounds import play_beep, stop_beep
from config import MAIN_MODEL
# Ensure an event loop exists for synchronous contexts (fix for tests using run_until_complete)
# asyncio.set_event_loop(asyncio.new_event_loop()) # Removed this problematic line
from prompts import SEARCH_SUMMARY_PROMPT
from performance_monitor import measure_performance # Add this import

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# ──────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────

CACHE_MAX_SIZE = 64               # larger but still bounded
DUCK_MAX_RESULTS = 12
FETCH_CONCURRENCY = 5             # simultaneous downloads
PAGE_CHAR_LIMIT = 4500            # text fed to LLM
CACHE_TTL = 3600                  # seconds
TIMEOUT = httpx.Timeout(20.0, connect=7.0, read=7.0)
MAX_RETRY_ATTEMPTS = 3            # Maximum retry attempts for rate limited requests
RETRY_BACKOFF_BASE = 2            # Exponential backoff base factor

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

# ──────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────


@lru_cache(maxsize=128)
def normalize_query(query: str) -> str:
    """Normalize text so that semantically same queries hit the cache."""
    return re.sub(r"[^\w\s]", "", query.lower()).strip()


def is_similar(q1: str, q2: str, threshold: float = 0.8) -> bool:
    set1, set2 = set(q1.split()), set(q2.split())
    if not set1 or not set2:
        return False
    # Similarity based on overlap relative to smaller set
    intersection = len(set1 & set2)
    min_size = min(len(set1), len(set2))
    return (intersection / min_size) >= threshold


def random_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html; charset=utf-8",
        "Accept-Language": "pl,en-US;q=0.9,en;q=0.8",
    }


def _decode(content: bytes) -> str:
    """Best‑effort decoding using charset-normalizer."""
    detection = from_bytes(content).best()
    if detection and detection.encoding:
        try:
            return content.decode(detection.encoding, errors="replace")
        except LookupError:
            pass
    return content.decode("utf-8", errors="replace")


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    paragraphs = [p.get_text(" ", strip=True) for p in soup.select("p")[:25]]
    return " ".join(paragraphs)

# ──────────────────────────────────────────
#  Tiny time‑aware LRU cache
# ──────────────────────────────────────────

class SearchCache(OrderedDict):
    """Very small LRU cache that also tracks insertion time."""

    def __init__(self, maxlen: int):
        super().__init__()
        self._maxlen = maxlen

    def get(self, key: str, now: float):
        val = super().get(key)
        if val and now - val[0] < CACHE_TTL:
            return val[2]  # cached_result (FIFO eviction, no access-order update)
        return None

    def put(self, key: str, value):
        if key in self:
            self.move_to_end(key)
        self[key] = value
        if len(self) > self._maxlen:
            self.popitem(last=False)

_search_cache = SearchCache(CACHE_MAX_SIZE)

# DDGS instances and management
_ddgs = DDGS()
_last_ddgs_error_time = 0.0  # Track when last error occurred

def get_ddgs_instance():
    """Get a DDGS instance, recreating it if there was a recent error."""
    global _ddgs, _last_ddgs_error_time
    
    # If there was an error recently (within the last 30 seconds), create a new instance
    if time.time() - _last_ddgs_error_time < 30:
        logger.info("Creating new DDGS instance after recent error")
        _ddgs = DDGS()
        _last_ddgs_error_time = 0.0
        
    return _ddgs

# ──────────────────────────────────────────
#  Networking helpers
# ──────────────────────────────────────────

@measure_performance
async def _fetch_page(client: httpx.AsyncClient, url: str) -> str:
    for attempt in range(3):
        try:
            r = await client.get(url, headers=random_headers(), follow_redirects=True)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("text/html"):
                return extract_text(_decode(r.content))
            if r.status_code == 403:
                logger.debug("403 on %s, retry %s", url, attempt + 1)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            logger.debug("Fetch error %s on %s (attempt %s)", e, url, attempt + 1)
        await asyncio.sleep(1.5 * (attempt + 1))
    return ""


@measure_performance
async def _fetch_pages_concurrently(urls: list[str]) -> str:
    """Fetch multiple pages concurrently and concatenate their content."""
    if not urls:
        return ""
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        tasks = [_fetch_page(client, url) for url in urls[:FETCH_CONCURRENCY]] # Limit concurrency
        pages_content_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions and join successful results
    successful_content = [str(content) for content in pages_content_list if isinstance(content, str) and content]
    return " ".join(successful_content)


@measure_performance
async def _search_duckduckgo(query: str) -> list[str]:
    """Search DuckDuckGo with retry mechanism and rate limit handling."""
    global _last_ddgs_error_time
    loop = asyncio.get_running_loop()
    
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            # Get a fresh DDGS instance if there was a recent error
            ddgs_instance = get_ddgs_instance()
            
            return await loop.run_in_executor(
                None, 
                lambda: [r["href"] for r in ddgs_instance.text(query, max_results=DUCK_MAX_RESULTS) if r.get("href")]
            )
        except DuckDuckGoSearchException as e:
            _last_ddgs_error_time = time.time()  # Mark when error occurred
            
            if "Ratelimit" in str(e) and attempt < MAX_RETRY_ATTEMPTS - 1:
                # Apply exponential backoff with jitter
                backoff_time = RETRY_BACKOFF_BASE ** attempt + random.uniform(0.5, 1.5)
                logger.warning(f"DuckDuckGo rate limit hit. Retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRY_ATTEMPTS})")
                await asyncio.sleep(backoff_time)
            else:
                # If we've exhausted retries or it's another error, try fallback search
                logger.warning(f"DuckDuckGo search failed after {attempt+1} attempts: {e}")
                return await _fallback_search(query)
    
    # This shouldn't be reached due to the exception handling, but just in case
    return []

@measure_performance
async def _fallback_search(query: str) -> list[str]:
    """Fallback search method when DuckDuckGo fails."""
    try:
        # Simple direct search using Bing
        search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(search_url, headers=random_headers(), follow_redirects=True)
            
            if response.status_code != 200:
                logger.warning(f"Fallback search failed with status code {response.status_code}")
                return []
                
            # Parse response to extract URLs
            soup = BeautifulSoup(response.text, "lxml")
            results = []
            
            # Extract URLs from Bing search results
            for link in soup.select("a[href^='http']:not([href^='https://www.bing.com'])"):
                url = link.get("href")
                if url and "bing" not in url and "microsoft" not in url and url not in results:
                    results.append(url)
                    if len(results) >= DUCK_MAX_RESULTS:
                        break
                        
            logger.info(f"Fallback search found {len(results)} results")
            return results
            
    except Exception as e:
        logger.error(f"Fallback search error: {e}")
        return []

# ──────────────────────────────────────────
#  Public entrypoint
# ──────────────────────────────────────────

@measure_performance
async def search_handler(query: str, user_id: str = None) -> str: # Added user_id for consistency if needed later
    if not query:
        return "Podaj zapytanie wyszukiwania."

    normalized_query = normalize_query(query)
    now = time.time()

    # Check cache first
    cached_result = _search_cache.get(normalized_query, now)
    if cached_result:
        logger.info(f"Cache hit for query: '{query}'")
        return cached_result

    try:
        await anyio.to_thread.run_sync(play_beep, "search", True) # Changed to anyio

        search_results = await _search_duckduckgo(normalized_query)
        pages_content_str = ""

        if search_results:
            pages_content_str = await _fetch_pages_concurrently(search_results)
        
        # Fallback search if no results or no content from initial search
        fallback_content_str = ""
        if not search_results or not pages_content_str:
            logger.info(f"No results or content from initial search for '{query}'. Trying fallback.")
            fallback_urls = await _fallback_search(normalized_query) # Fallback gives URLs
            if fallback_urls:
                logger.info(f"Fallback search provided {len(fallback_urls)} URLs.")
                fallback_content_str = await _fetch_pages_concurrently(fallback_urls)
                if fallback_content_str:
                    logger.info(f"Successfully fetched content from fallback URLs for '{query}'.")
                    # Use fallback content if primary search yielded nothing
                    if not pages_content_str: # Only use fallback if primary was empty
                         pages_content_str = fallback_content_str
                else:
                    logger.warning(f"Fallback search URLs yielded no content for '{query}'.")
            else:
                logger.warning(f"Fallback search found no URLs for '{query}'.")


        if not pages_content_str: # Check if any content was actually fetched (primary or fallback)
            logger.warning(f"No content to summarize for query: '{query}' after primary and fallback attempts.")
            await anyio.to_thread.run_sync(stop_beep) # Changed to anyio
            return "Nie znaleziono wyników. Spróbuj przeformułować zapytanie lub sprawdź połączenie internetowe."

        text_to_summarize = pages_content_str[:PAGE_CHAR_LIMIT]
        
        messages = [{"role": "user", "content": SEARCH_SUMMARY_PROMPT.format(query=query, text=text_to_summarize)}]
        
        # Use a default model or allow configuration
        summary_response = await chat_with_providers(
            model_name=MAIN_MODEL, 
            messages=messages, 
            user_id=user_id # Pass user_id if chat_with_providers supports it
        )

        if summary_response and summary_response.get("message", {}).get("content"):
            final_summary = remove_chain_of_thought(summary_response["message"]["content"].strip())
            _search_cache.put(normalized_query, (now, query, final_summary))
            await anyio.to_thread.run_sync(stop_beep) # Changed to anyio
            return final_summary
        else:
            logger.error(f"Failed to get summary from provider for query: '{query}'")
            await anyio.to_thread.run_sync(stop_beep) # Changed to anyio
            return "Błąd podczas generowania podsumowania. Spróbuj ponownie później."

    except DuckDuckGoSearchException as e:
        logger.error(f"Search error for query '{query}': {e}")
        await anyio.to_thread.run_sync(stop_beep) # Changed to anyio
        # Specific message for rate limit, more generic for other DDGS errors
        if "Ratelimit" in str(e): # Check if this is how DDGS library signals rate limit
             return "Przepraszam, przekroczono limit zapytań do wyszukiwarki. Spróbuj ponownie za chwilę."
        return "Przepraszam, napotkałem chwilowy problem z wyszukiwaniem. Spróbuj ponownie za kilka minut."
    except Exception as e:
        logger.error(f"Unexpected error in search_handler for query '{query}': {e}", exc_info=True)
        await anyio.to_thread.run_sync(stop_beep) # Changed to anyio
        return "Wystąpił nieoczekiwany błąd podczas wyszukiwania. Spróbuj ponownie później."
    
# ──────────────────────────────────────────
#  Command registration – same interface
# ──────────────────────────────────────────

def register():
    return {
        "command": "search",
        "aliases": ["search", "wyszukaj", "web"],
        "description": "Wyszukuje informacje w internecie i podsumowuje wyniki.",
        "handler": search_handler,
        "prompt": SEARCH_SUMMARY_PROMPT,
        "sub_commands": {
            "search": {
                "description": "Wyszukaj informacje w internecie",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Fraza do wyszukania w internecie",
                        "required": True
                    }
                }
            }
        }
    }

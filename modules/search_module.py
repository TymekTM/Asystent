import asyncio, logging, os, re, subprocess, aiohttp, time, random
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import ollama
from config import MAIN_MODEL
from prompts import SEARCH_SUMMARY_PROMPT, SEE_SCREEN_PROMPT
from audio_modules.beep_sounds import play_beep
from ai_module import chat_with_providers, remove_chain_of_thought


logger = logging.getLogger(__name__)
beep_process = None
search_cache = {}

# Lista User-Agentów do rotacji
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


# Funkcja generująca realistyczne nagłówki przeglądarki
def get_random_headers():
    user_agent = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pl,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    return headers


def normalize_query(query: str) -> str:
    query = query.lower().strip()
    return re.sub(r'[^\w\s]', '', query)


def is_similar(q1: str, q2: str, threshold=0.8) -> bool:
    set1, set2 = set(q1.split()), set(q2.split())
    if not set1 or not set2:
        return False
    return len(set1.intersection(set2)) / len(set1.union(set2)) >= threshold


def stop_search_beep():
    global beep_process
    if beep_process:
        try:
            logger.info("Stopping search beep.")
            beep_process.terminate()
        except Exception as e:
            logger.error("Error stopping search beep: %s", e)
        beep_process = None


# Modify handler to be async
async def search_handler(params: str = "", conversation_history: list = None) -> str:
    if not params:
        return "Podaj zapytanie wyszukiwania po komendzie !search"

    # No need for inner async_search, the handler is now async
    now = time.time()
    normalized = normalize_query(params)
    # Check cache
    for cached_query, (cached_timestamp, original_query, cached_result) in search_cache.items():
        if is_similar(normalized, cached_query) and now - cached_timestamp < 3600:
            logger.info("Returning cached result for: %s", original_query)
            return cached_result

    logger.info("Searching for query: %s", params)
    # Consider making play_beep async or running in executor if it blocks significantly
    play_beep("search")
    try:
        cookie_jar = aiohttp.CookieJar(unsafe=True)
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=10)

        async with aiohttp.ClientSession(cookie_jar=cookie_jar, connector=connector, timeout=timeout) as session:
            try:
                # Run synchronous DDGS search in an executor thread
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(None, lambda: list(DDGS().text(params, max_results=10)))
            except Exception as e:
                logger.error("DuckDuckGo search error: %s", e)
                return "Błąd podczas wyszukiwania (DuckDuckGo)."

            valid_urls = [res.get("href") for res in results if res.get("href")]
            if not valid_urls:
                logger.warning("No results found.")
                return "Nie znaleziono żadnych wyników."

            async def fetch_page(url: str, max_retries=3) -> str:
                # ... (fetch_page logic remains the same)
                for attempt in range(max_retries):
                    try:
                        headers = get_random_headers()
                        if attempt > 0:
                            await asyncio.sleep(2 * attempt)
                        async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                            if response.status == 200:
                                # Handle potential encoding issues more robustly
                                try:
                                    content = await response.read() # Read bytes first
                                    # Attempt decoding with detected encoding or fallbacks
                                    detected_encoding = response.charset
                                    if detected_encoding:
                                        return content.decode(detected_encoding, errors='replace')
                                    else:
                                        # Try common encodings if detection fails
                                        try:
                                            return content.decode('utf-8', errors='replace')
                                        except UnicodeDecodeError:
                                            return content.decode('iso-8859-1', errors='replace') # Fallback
                                except Exception as decode_err:
                                     logger.warning(f"Error decoding {url}: {decode_err}")
                                     return "" # Return empty on decode error
                            elif response.status == 403:
                                logger.warning(
                                    f"Błąd 403 (próba {attempt + 1}) dla {url}, ponawiam z innymi nagłówkami")
                                if attempt < max_retries - 1:
                                    continue
                                else:
                                    logger.error(f"Osiągnięto maksymalną liczbę prób dla {url}")
                                    return ""
                            else:
                                logger.warning(f"Błąd podczas pobierania {url}, status: {response.status}")
                                return ""
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout podczas pobierania {url} (próba {attempt + 1})")
                    except aiohttp.ClientConnectorError as e:
                        logger.error(f"Connection error dla {url} (próba {attempt + 1}): {e}")
                    except ConnectionRefusedError as e:
                        logger.error(f"Connection refused dla {url} (próba {attempt + 1}): {e}")
                    except Exception as e:
                        # Log the specific exception type and message
                        logger.error(f"Wyjątek {type(e).__name__} podczas pobierania {url} (próba {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return ""

            tasks = []
            for i, url in enumerate(valid_urls[:5]): # Limit to first 5 URLs
                tasks.append(fetch_page(url))
                if i < len(valid_urls[:5]) - 1:
                    await asyncio.sleep(0.5) # Small delay between starting fetches
            pages = await asyncio.gather(*tasks)

            texts = []
            for page_content in pages:
                if page_content:
                    # Run synchronous BeautifulSoup parsing in an executor thread
                    loop = asyncio.get_running_loop()
                    text_content = await loop.run_in_executor(None, lambda pc=page_content: " ".join(p.get_text(separator=" ", strip=True) for p in BeautifulSoup(pc, "html.parser").find_all("p")))
                    texts.append(" ".join(text_content.split()))

            if texts:
                combined_text = "\n\n".join(texts)
                summary_messages = [
                    {"role": "system", "content": SEARCH_SUMMARY_PROMPT},
                    {"role": "user", "content": f"Summarize the following text based on the user query: '{params}'\n\nText:\n{combined_text}"}
                ]

                # Assuming chat_with_providers is synchronous, run it in an executor
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, lambda: chat_with_providers(MAIN_MODEL, summary_messages))

                summary = remove_chain_of_thought(response["message"]["content"].strip())
                final_result = summary if summary else "Nie udało się wygenerować podsumowania."
                search_cache[normalized] = (time.time(), params, final_result)
                return final_result
            else:
                logger.warning("Failed to fetch or parse page content.")
                return "Nie udało się pobrać ani przetworzyć treści stron."
    except Exception as e:
        logger.error("Search handler error: %s", e, exc_info=True)
        return "Błąd podczas przetwarzania wyszukiwania."
    finally:
        # Consider making stop_search_beep async or running in executor
        stop_search_beep()


def register():
    return {
        "command": "search",
        "aliases": ["search", "wyszukaj"],
        "description": "Wyszukuje informacje w internecie i podsumowuje wyniki.",
        "handler": search_handler,
        "prompt": SEARCH_SUMMARY_PROMPT
    }

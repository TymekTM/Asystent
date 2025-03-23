import asyncio, logging, os, re, subprocess, aiohttp, time, random
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import ollama
from config import MAIN_MODEL
from prompts import SEARCH_SUMMARY_PROMPT
from audio_modules.beep_sounds import play_beep


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


def search_handler(params: str = "") -> str:
    if not params:
        return "Podaj zapytanie wyszukiwania po komendzie !search"

    async def async_search():
        now = time.time()
        normalized = normalize_query(params)
        for cached_query, (cached_timestamp, original_query, cached_result) in search_cache.items():
            if is_similar(normalized, cached_query) and now - cached_timestamp < 3600:
                logger.info("Returning cached result for: %s", original_query)
                return cached_result

        logger.info("Searching for query: %s", params)
        play_beep("search")
        try:
            # Konfiguracja sesji z obsługą ciasteczek
            cookie_jar = aiohttp.CookieJar(unsafe=True)
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=10)

            async with aiohttp.ClientSession(cookie_jar=cookie_jar, connector=connector, timeout=timeout) as session:
                with DDGS() as ddgs:
                    results = ddgs.text(params, max_results=10)
                valid_urls = [res.get("href") for res in results if res.get("href")]
                if not valid_urls:
                    logger.warning("No results found.")
                    return "Nie znaleziono żadnych wyników."

                async def fetch_page(url: str, max_retries=3) -> str:
                    for attempt in range(max_retries):
                        try:
                            # Świeże nagłówki dla każdego żądania
                            headers = get_random_headers()

                            # Opóźnienie między próbami
                            if attempt > 0:
                                await asyncio.sleep(2 * attempt)  # Wykładnicze zwiększanie opóźnienia

                            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                                if response.status == 200:
                                    return await response.text()
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
                        except Exception as e:
                            logger.error(f"Wyjątek podczas pobierania {url} (próba {attempt + 1}): {e}")

                        if attempt < max_retries - 1:
                            continue
                        else:
                            return ""

                # Dodanie opóźnień między zadaniami
                tasks = []
                for i, url in enumerate(valid_urls[:5]):
                    tasks.append(fetch_page(url))
                    if i < len(valid_urls[:5]) - 1:
                        await asyncio.sleep(0.5)  # 500ms opóźnienia między uruchomieniem każdego fetch

                pages = await asyncio.gather(*tasks)
                texts = []
                for page in pages:
                    if page:
                        soup = BeautifulSoup(page, "html.parser")
                        paragraphs = soup.find_all("p")
                        text_content = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
                        texts.append(" ".join(text_content.split()))
                if texts:
                    combined_text = "\n\n".join(texts)
                    prompt_text = f"{combined_text}\n\nUżytkownik zapytał: {params}"
                    response = ollama.chat(
                        model=MAIN_MODEL,
                        messages=[
                            {"role": "system", "content": SEARCH_SUMMARY_PROMPT},
                            {"role": "user", "content": prompt_text}
                        ]
                    )
                    summary = response["message"]["content"].strip()
                    final_result = summary if summary else "Nie udało się wygenerować podsumowania."
                    search_cache[normalized] = (time.time(), params, final_result)
                    return final_result
                else:
                    logger.warning("Failed to fetch page content.")
                    return "Nie udało się pobrać wyników."
        except Exception as e:
            logger.error("Search error: %s", e)
            return "Błąd podczas wyszukiwania."
        finally:
            stop_search_beep()

    return asyncio.run(async_search())


def register():
    return {
        "command": "search",
        "aliases": ["search", "wyszukaj"],
        "description": "Wyszukuje informacje w internecie i podsumowuje wyniki.",
        "handler": search_handler
    }

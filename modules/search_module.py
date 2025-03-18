import asyncio, logging, os, re, subprocess, aiohttp, time
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import ollama
from config import MAIN_MODEL
from prompts import SEARCH_SUMMARY_PROMPT

logger = logging.getLogger(__name__)
beep_process = None
search_cache = {}

def play_search_beep():
    global beep_process
    beep_file = "search_beep.mp3"
    if os.path.exists(beep_file):
        try:
            logger.info("Playing search beep.")
            beep_process = subprocess.Popen(["ffplay", "-nodisp", "-loglevel", "quiet", "-loop", "0", beep_file])
        except Exception as e:
            logger.error("Error playing search beep: %s", e)
            beep_process = None
    else:
        logger.warning("search_beep.mp3 not found.")

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
        play_search_beep()
        try:
            async with aiohttp.ClientSession() as session:
                with DDGS() as ddgs:
                    results = ddgs.text(params, max_results=10)
                valid_urls = [res.get("href") for res in results if res.get("href")]
                if not valid_urls:
                    logger.warning("No results found.")
                    return "Nie znaleziono żadnych wyników."
                async def fetch_page(url: str) -> str:
                    try:
                        async with session.get(url, timeout=5) as response:
                            if response.status == 200:
                                return await response.text()
                            else:
                                logger.warning("Error fetching %s, status: %s", url, response.status)
                                return ""
                    except Exception as e:
                        logger.error("Exception fetching %s: %s", url, e)
                        return ""
                tasks = [fetch_page(url) for url in valid_urls[:5]]
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
        "command": "!search",
        "aliases": ["search", "wyszukaj"],
        "description": "Wyszukuje informacje w internecie i podsumowuje wyniki.",
        "handler": search_handler
    }

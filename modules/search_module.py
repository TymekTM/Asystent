import asyncio
import logging
import os
import re
import subprocess
import aiohttp
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import ollama
from config import MAIN_MODEL
import time
from prompts import SEARCH_SUMMARY_PROMPT

logger = logging.getLogger(__name__)
beep_process = None
search_cache = {}

def play_search_beep():
    global beep_process
    beep_file = "search_beep.mp3"
    if os.path.exists(beep_file):
        try:
            logger.info("Odtwarzanie dźwięku wyszukiwania.")
            beep_process = subprocess.Popen(["ffplay", "-nodisp", "-loglevel", "quiet", "-loop", "0", beep_file])
        except Exception as e:
            logger.error("Błąd odtwarzania dźwięku wyszukiwania: %s", e)
            beep_process = None
    else:
        logger.warning("Plik dźwięku search_beep.mp3 nie został znaleziony.")

def normalize_query(query: str) -> str:
    query = query.lower().strip()
    query = re.sub(r'[^\w\s]', '', query)  # usuń znaki interpunkcyjne
    return query

def is_similar(q1: str, q2: str, threshold=0.8) -> bool:
    # Proste porównanie zbiorów słów – jeśli wspólnych słów jest dużo, uznajemy za podobne
    set1 = set(q1.split())
    set2 = set(q2.split())
    if not set1 or not set2:
        return False
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    ratio = len(intersection) / len(union)
    return ratio >= threshold

def stop_search_beep():
    global beep_process
    if beep_process is not None:
        try:
            logger.info("Zatrzymywanie dźwięku wyszukiwania.")
            beep_process.terminate()
        except Exception as e:
            logger.error("Błąd zatrzymywania dźwięku wyszukiwania: %s", e)
        beep_process = None

def search_handler(params: str = "") -> str:
    if not params:
        return "Podaj zapytanie wyszukiwania po komendzie !search"

    async def async_search():
        now = time.time()
        normalized = normalize_query(params)
        # Szukamy podobnego zapytania w cache
        for cached_query, (cached_timestamp, original_query, cached_result) in search_cache.items():
            if is_similar(normalized, cached_query) and now - cached_timestamp < 3600:
                logger.info("Zwracam wynik z cache dla podobnego zapytania: %s", original_query)
                return cached_result

        logger.info("Rozpoczynam wyszukiwanie dla zapytania: %s", params)
        play_search_beep()
        try:
            async with aiohttp.ClientSession() as session:
                with DDGS() as ddgs:
                    results = ddgs.text(params, max_results=10)
                valid_urls = [res.get("href") for res in results if res.get("href")]
                if len(valid_urls) < 1:
                    logger.warning("Nie znaleziono wyników.")
                    return "Nie znaleziono żadnych wyników."

                async def fetch_page(url: str) -> str:
                    try:
                        async with session.get(url, timeout=5) as response:
                            if response.status == 200:
                                text = await response.text()
                                logger.info("Pobrano stronę: %s", url)
                                return text
                            else:
                                logger.warning("Błąd pobierania strony %s, status: %s", url, response.status)
                                return ""
                    except Exception as e:
                        logger.error("Wyjątek podczas pobierania strony %s: %s", url, e)
                        return ""

                tasks = [fetch_page(url) for url in valid_urls[:5]]
                pages = await asyncio.gather(*tasks)
                texts = []
                for page in pages:
                    if page:
                        soup = BeautifulSoup(page, "html.parser")
                        paragraphs = soup.find_all("p")
                        text_content = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
                        text_content = " ".join(text_content.split())
                        texts.append(text_content)
                if texts:
                    combined_text = "\n\n".join(texts)
                    logger.info("Podsumowywanie wyników wyszukiwania.")
                    # Dołączamy oryginalne zapytanie użytkownika do promptu
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
                    # Zapisz wynik w cache, używając znormalizowanego zapytania jako klucza
                    search_cache[normalized] = (time.time(), params, final_result)
                    return final_result
                else:
                    logger.warning("Nie udało się pobrać treści stron.")
                    return "Nie udało się pobrać wyników."
        except Exception as e:
            logger.error("Błąd podczas wyszukiwania: %s", e)
            return "Błąd podczas wyszukiwania."
        finally:
            stop_search_beep()

    return asyncio.run(async_search())

def register():
    return {
        "command": "!search",
        "aliases": ["search", "wyszukaj"],
        "description": "Pozwala wyszukać informacje w internecie i podsumować wyniki.",
        "handler": search_handler
    }

import asyncio
import logging
import os
import subprocess
import aiohttp
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import ollama

import assistant
# Import promptu do podsumowania wyników wyszukiwania
from prompts import SEARCH_SUMMARY_PROMPT

logger = logging.getLogger(__name__)
beep_process = None

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
        logger.info("Rozpoczynam wyszukiwanie dla zapytania: %s", params)
        play_search_beep()
        try:
            async with aiohttp.ClientSession() as session:
                with DDGS() as ddgs:
                    results = ddgs.text(params, max_results=10)
                valid_urls = [res.get("href") for res in results if res.get("href")]
                if len(valid_urls) < 1:
                    logger.warning("Nie znaleziono wystarczającej liczby wyników.")
                    return "Nie znaleziono minimum 3 wyników."

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
                    response = ollama.chat(
                        model="gemma3",
                        messages=[
                            {"role": "system", "content": SEARCH_SUMMARY_PROMPT},
                            {"role": "user", "content": combined_text}
                        ]
                    )
                    summary = response["message"]["content"].strip()
                    logger.info("Podsumowanie: %s", summary)
                    return summary if summary else "Nie udało się wygenerować podsumowania."
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

import asyncio
import logging
import os
import subprocess
import sys

try:
    from duckduckgo_search import DDGS
except ImportError:
    logging.info("duckduckgo_search nie jest zainstalowany, próbuję zainstalować...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "duckduckgo_search"])
        from duckduckgo_search import DDGS
        logging.info("duckduckgo_search zainstalowany pomyślnie.")
    except Exception as e:
        logging.error("Nie udało się zainstalować duckduckgo_search: %s", e)
        DDGS = None

try:
    import aiohttp
except ImportError:
    aiohttp = None
    logging.warning("aiohttp nie jest zainstalowany, pobieranie stron będzie synchroniczne.")

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None
    logging.error("requests lub BeautifulSoup nie są zainstalowane!")

logger = logging.getLogger(__name__)

class SearchModule:
    def __init__(self):
        self.beep_process = None

    def play_search_beep(self):
        beep_file = "search_beep.mp3"  # Upewnij się, że ten plik istnieje
        if os.path.exists(beep_file):
            try:
                # Usuwamy -autoexit i dodajemy -loop 0, aby beep trwał do momentu zatrzymania
                self.beep_process = subprocess.Popen(
                    ["ffplay", "-nodisp", "-loglevel", "quiet", "-loop", "0", beep_file]
                )
            except Exception as e:
                logger.error("Error playing search beep: %s", e)
                self.beep_process = None
        else:
            logger.warning("search_beep.mp3 nie został znaleziony.")
            self.beep_process = None

    def stop_search_beep(self):
        if self.beep_process is not None:
            try:
                self.beep_process.terminate()
                self.beep_process = None
            except Exception as e:
                logger.error("Error stopping search beep: %s", e)

    async def fetch_page(self, url: str) -> str:
        if aiohttp:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            return await response.text()
            except Exception as e:
                logger.error("Error fetching %s: %s", url, e)
        elif requests:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    return resp.text
            except Exception as e:
                logger.error("Error fetching %s: %s", url, e)
        return ""

    async def search_and_summarize(self, query: str) -> str:
        logger.info("Search query: %s", query)
        # Rozpoczynamy odtwarzanie beep podczas wyszukiwania
        self.play_search_beep()
        try:
            if DDGS is None:
                return "Funkcja wyszukiwania niedostępna. Zainstaluj duckduckgo_search."
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=10)
            valid_urls = [res.get("href") for res in results if res.get("href")]
            if len(valid_urls) < 3:
                return "Nie znaleziono minimum 3 wyników."
            tasks = [self.fetch_page(url) for url in valid_urls[:3]]
            pages = await asyncio.gather(*tasks)
            texts = []
            for page in pages:
                if page and BeautifulSoup:
                    soup = BeautifulSoup(page, "html.parser")
                    paragraphs = soup.find_all("p")
                    text_content = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
                    text_content = " ".join(text_content.split())
                    texts.append(text_content)
            if texts:
                combined_text = "\n\n".join(texts)
                import ollama
                try:
                    response = ollama.chat(
                        model="gemma3",
                        messages=[
                            {"role": "system", "content": "Podsumuj poniższe wyniki wyszukiwania w jednym krótkim streszczeniu, podaj tylko esencję informacji."},
                            {"role": "user", "content": combined_text}
                        ]
                    )
                    summary = response["message"]["content"].strip()
                    return summary if summary else "Nie udało się wygenerować podsumowania."
                except Exception as e:
                    logger.error("Summarization error: %s", e)
                    return "Błąd przy podsumowywaniu wyników."
            else:
                return "Nie udało się pobrać wyników."
        except Exception as e:
            logger.error("Search error: %s", e)
            return "Błąd podczas wyszukiwania."
        finally:
            # Zatrzymujemy beep, gdy wyszukiwanie i podsumowywanie się zakończy
            self.stop_search_beep()

import subprocess
import os
import logging

logger = logging.getLogger(__name__)

# Słownik mapujący typ dźwięku do ścieżki do pliku
BEEP_SOUNDS = {
    "keyword": "resources/sounds/beep.mp3",
    "search": "resources/sounds/search_beep.mp3",
    "screenshot": "resources/sounds/screenshot_beep.mp3",
    "deep": "resources/sounds/deepthink_beep.mp3"
}


def play_beep(sound_type: str = "keyword"):
    """
    Odtwarza dźwięk z odpowiedniego pliku na podstawie podanego typu.

    :param sound_type: Typ dźwięku do odtworzenia ("keyword", "search", "screenshot", "deep").
                       Domyślnie "keyword".
    """
    beep_file = BEEP_SOUNDS.get(sound_type)
    if not beep_file:
        logger.warning(f"Nieznany typ dźwięku: {sound_type}")
        return

    if os.path.exists(beep_file):
        try:
            logger.info(f"Odtwarzam dźwięk '{sound_type}' z pliku: {beep_file}")
            subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", beep_file])
        except Exception as e:
            logger.error(f"Błąd przy odtwarzaniu dźwięku '{sound_type}': {e}")
    else:
        logger.warning(f"Plik dźwiękowy nie został znaleziony: {beep_file}")

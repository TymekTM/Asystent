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

def play_beep(sound_type: str = "keyword", loop: bool = True) -> subprocess.Popen | None:
    """
    Odtwarza dźwięk z odpowiedniego pliku na podstawie podanego typu.
    Zwraca obiekt Popen procesu odtwarzania lub None w przypadku błędu.

    :param sound_type: Typ dźwięku do odtworzenia ("keyword", "search", "screenshot", "deep", "api").
                       Domyślnie "keyword".
    :param loop: Czy dźwięk ma być odtwarzany w pętli (True) czy tylko raz (False).
                 Domyślnie True (dla dźwięków narzędzi).
    :return: Obiekt subprocess.Popen lub None.
    """
    # Fallback for unknown tool types to a default sound or silence?
    # For now, just use the specific sound if available.
    beep_file = BEEP_SOUNDS.get(sound_type)

    # If a specific sound for the command doesn't exist, don't play anything
    # or optionally play a generic 'processing' sound.
    # Let's choose not to play if specific sound is missing, except for 'keyword'.
    if not beep_file and sound_type != "keyword":
        logger.debug(f"No specific beep sound found for type: {sound_type}. Skipping beep.")
        return None
    elif not beep_file and sound_type == "keyword":
        # Fallback for keyword if its specific file is missing for some reason
        beep_file = BEEP_SOUNDS.get("keyword", "resources/sounds/beep.mp3")


    if os.path.exists(beep_file):
        try:
            logger.info(f"Odtwarzam dźwięk '{sound_type}' z pliku: {beep_file} (Loop: {loop})")
            # Use -loop 0 for infinite loop, remove it for single play
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
            if loop:
                cmd.extend(["-loop", "0"])
            cmd.append(beep_file)

            process = subprocess.Popen(cmd,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) # Suppress ffplay output
            return process
        except FileNotFoundError:
             logger.error(f"Błąd przy odtwarzaniu dźwięku '{sound_type}': Polecenie 'ffplay' nie znalezione. Upewnij się, że FFmpeg jest zainstalowany i w PATH.")
             return None
        except Exception as e:
            logger.error(f"Błąd przy odtwarzaniu dźwięku '{sound_type}': {e}")
            return None
    else:
        logger.warning(f"Plik dźwiękowy nie został znaleziony: {beep_file}")
        return None

def stop_beep(process: subprocess.Popen):
    """Terminuje proces odtwarzania dźwięku."""
    if process and process.poll() is None: # Check if process is still running
        try:
            logger.info(f"Zatrzymuję dźwięk (PID: {process.pid})")
            process.terminate()
            process.wait(timeout=1) # Give it a moment to terminate gracefully
        except subprocess.TimeoutExpired:
            logger.warning(f"Proces dźwięku (PID: {process.pid}) nie zakończył się na czas, wymuszam zamknięcie.")
            process.kill()
            process.wait(timeout=1) # Wait after kill
        except Exception as e:
            # Catch potential errors if the process already terminated between poll() and terminate()
            logger.error(f"Błąd podczas zatrzymywania dźwięku (PID: {process.pid}): {e}")
    elif process:
        logger.debug(f"Proces dźwięku (PID: {process.pid}) już zakończony.")

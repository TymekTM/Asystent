import subprocess
import os
import logging
import sys  # Added sys import
from config import BASE_DIR
from .ffmpeg_installer import ensure_ffmpeg_installed

# Try to import sounddevice with dependency manager integration
try:
    from .sounddevice_loader import get_sounddevice, is_sounddevice_available
    sd = get_sounddevice()
    SOUNDDEVICE_AVAILABLE = is_sounddevice_available()
    if SOUNDDEVICE_AVAILABLE:
        logging.getLogger(__name__).info("sounddevice loaded successfully via loader")
    else:
        logging.getLogger(__name__).warning("sounddevice not available - will be installed on demand")
except ImportError as e:
    sd = None
    SOUNDDEVICE_AVAILABLE = False
    logging.getLogger(__name__).warning(f"Sounddevice loader not available: {e}")

# Set logger to DEBUG globally
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Helper function to determine the base path for resources (same as in wakeword_detector.py)
# Determine the base directory for resources: use executable dir when frozen, otherwise project root
def get_base_path():
    """Returns the base path for resources, whether running normally or bundled."""
    if getattr(sys, 'frozen', False):  # PyInstaller bundle
        return BASE_DIR
    # Development: 2 levels up from this file
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Global mute flag to disable beeps (e.g., in chat/text mode)
MUTE = False

# Słownik mapujący typ dźwięku do ścieżki do pliku
BEEP_SOUNDS = {
    # General-purpose beep (alias of keyword)
    "beep": "resources/sounds/beep.mp3",
    "keyword": "resources/sounds/beep.mp3",
    "search": "resources/sounds/search_beep.mp3",
    "screenshot": "resources/sounds/screenshot_beep.mp3",
    "deep": "resources/sounds/deepthink_beep.mp3",
    "alarm": "resources/sounds/alarm.wav",
    # Added extra beep sounds for wake word detection and VAD events
    "listening_start": "resources/sounds/beep.mp3",
    "listening_done": "resources/sounds/beep.mp3",
    "error": "resources/sounds/beep.mp3",
    "timeout": "resources/sounds/beep.mp3",
}

def play_beep(sound_type: str = "keyword", loop: bool = False) -> subprocess.Popen | None:
    """
    Odtwarza dźwięk z odpowiedniego pliku na podstawie podanego typu.
    Zwraca obiekt Popen procesu odtwarzania lub None w przypadku błędu.

    :param sound_type: Typ dźwięku do odtworzenia ("keyword", "search", "screenshot", "deep", "api").
                       Domyślnie "keyword".
    :param loop: Czy dźwięk ma być odtwarzany w pętli (True) czy tylko raz (False).
                 Domyślnie False (dla pojedynczego odtwarzania).
    :return: Obiekt subprocess.Popen lub None.
    """
    # Ensure ffmpeg/ffplay is installed before playback
    ensure_ffmpeg_installed()
    # If muted, skip playing sounds
    if MUTE:
        return None
    
    base_dir = get_base_path()  # Use the helper function
    logger.info(f"[Debug] base_dir for beeps: {base_dir}")
    rel_path = BEEP_SOUNDS.get(sound_type)
    
    if not rel_path:  # If sound_type is not in BEEP_SOUNDS
        logger.debug(f"No specific beep sound found for type: {sound_type}. Attempting default.")
        rel_path = BEEP_SOUNDS.get("keyword")  # Fallback to default keyword beep

    if not rel_path:  # If still no rel_path (e.g. "keyword" also missing)
        logger.error(f"Default beep sound ('keyword') not found in BEEP_SOUNDS. Cannot play sound for type: {sound_type}")
        return None

    # Build list of roots to search for the sound file
    # Determine absolute path to the sound file under resources
    beep_file = os.path.join(get_base_path(), rel_path)
    logger.info(f"[Debug] Using beep_file: {beep_file}")
    if not os.path.isfile(beep_file):
        logger.warning(f"Beep file not found: {beep_file}")
        return None
    
    if os.path.exists(beep_file):
        try:
            logger.info(f"Odtwarzam dźwięk '{sound_type}' z pliku: {beep_file} (Loop: {loop})")
            # Use -loop 0 for infinite loop, remove it for single play
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
            if loop:
                cmd.extend(["-loop", "0"])
            cmd.append(beep_file)

            process = subprocess.Popen(cmd,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # Suppress ffplay output
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
    if process and process.poll() is None:  # Check if process is still running
        try:
            logger.info(f"Zatrzymuję dźwięk (PID: {process.pid})")
            process.terminate()
            process.wait(timeout=1)  # Give it a moment to terminate gracefully
        except subprocess.TimeoutExpired:
            logger.warning(f"Proces dźwięku (PID: {process.pid}) nie zakończył się na czas, wymuszam zamknięcie.")
            process.kill()
            process.wait(timeout=1)  # Wait after kill
        except Exception as e:
            # Catch potential errors if the process already terminated between poll() and terminate()
            logger.error(f"Błąd podczas zatrzymywania dźwięku (PID: {process.pid}): {e}")
    elif process:
        logger.debug(f"Proces dźwięku (PID: {process.pid}) już zakończony.")

def play_sound(data, samplerate, blocking=True):
    logger.debug(f"play_sound called. MUTE={MUTE}. Blocking={blocking}")
    
    if MUTE:
        logger.debug("MUTE is active, skipping sound playback.")
        return
        
    if not SOUNDDEVICE_AVAILABLE:
        logger.warning("Sounddevice not available, cannot play sound directly")
        return
    
    logger.debug(f"Default devices: In='{sd.default.device[0]}', Out='{sd.default.device[1]}'")
    # ...existing playback code...

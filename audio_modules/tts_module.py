import asyncio, logging, os, subprocess, uuid, threading
from edge_tts import Communicate
from performance_monitor import measure_performance

logger = logging.getLogger(__name__)


import glob
import time

class TTSModule:
    CLEANUP_INTERVAL = 10  # seconds
    INACTIVITY_THRESHOLD = 30  # seconds

    def __init__(self):
        self.current_process = None
        self._last_activity = time.time()
        self._cleanup_task_started = False
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        if not self._cleanup_task_started:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._cleanup_temp_files_loop())
                else:
                    # For non-async context, start in a background thread
                    threading.Thread(target=lambda: asyncio.run(self._cleanup_temp_files_loop()), daemon=True).start()
                self._cleanup_task_started = True
            except Exception as e:
                logger.error(f"Failed to start TTS cleanup task: {e}")

    async def _cleanup_temp_files_loop(self):
        while True:
            try:
                now = time.time()
                # Only clean up if no TTS activity for INACTIVITY_THRESHOLD
                if now - self._last_activity > self.INACTIVITY_THRESHOLD:
                    pattern = os.path.join("resources", "sounds", "temp_tts_*.mp3")
                    for path in glob.glob(pattern):
                        try:
                            mtime = os.path.getmtime(path)
                            if now - mtime > self.INACTIVITY_THRESHOLD:
                                os.remove(path)
                                logger.info(f"[TTS Cleanup] Deleted old temp file: {path}")
                        except Exception as e:
                            logger.warning(f"[TTS Cleanup] Failed to delete {path}: {e}")
            except Exception as e:
                logger.error(f"[TTS Cleanup] Error in cleanup loop: {e}")
            await asyncio.sleep(self.CLEANUP_INTERVAL)

    def cancel(self):
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception as e:
                logger.error("Error stopping TTS: %s", e)
            self.current_process = None

    @measure_performance
    async def speak(self, text: str):
        logger.info("TTS: %s", text)
        tts = Communicate(text, "pl-PL-MarekNeural")
        temp_filename = f"temp_tts_{uuid.uuid4().hex}.mp3"
        temp_path = os.path.join("resources", "sounds", temp_filename)
        self._last_activity = time.time()
        try:
            await tts.save(temp_path)
            self.cancel()
            self.current_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_path]
            )
            await asyncio.to_thread(self.current_process.wait)
        except Exception as e:
            logger.error("TTS error: %s", e)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except PermissionError:
                    logger.warning(f"Nie można usunąć pliku {temp_path}, jest używany przez inny proces.")
                except Exception as e:
                    logger.error(f"Błąd przy usuwaniu pliku {temp_path}: {e}")
            self.current_process = None

# Create a global instance of TTSModule
_tts_module_instance = TTSModule()

# Define a module-level async speak function
async def speak(text: str):
    """Module-level function to handle text-to-speech."""
    await _tts_module_instance.speak(text)

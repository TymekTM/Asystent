import asyncio, logging, os, subprocess, uuid
from edge_tts import Communicate

logger = logging.getLogger(__name__)

class TTSModule:
    def __init__(self):
        self.current_process = None

    def cancel(self):
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception as e:
                logger.error("Error stopping TTS: %s", e)
            self.current_process = None

    async def speak(self, text: str):
        logger.info("TTS: %s", text)
        tts = Communicate(text, "pl-PL-MarekNeural")
        temp_filename = f"temp_tts_{uuid.uuid4().hex}.mp3"
        temp_path = os.path.join("resources", "sounds", temp_filename)
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

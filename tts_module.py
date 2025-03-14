# tts_module.py

import asyncio
import logging
import os
import subprocess
from edge_tts import Communicate

logger = logging.getLogger(__name__)

class TTSModule:
    def __init__(self):
        self.current_process = None

    def cancel(self):
        if self.current_process is not None:
            try:
                self.current_process.terminate()
            except Exception as e:
                logger.error("Błąd zatrzymywania TTS: %s", e)
            self.current_process = None

    async def speak(self, text: str):
        logger.info("TTS: %s", text)
        tts = Communicate(text, "pl-PL-MarekNeural")
        output_file = "temp_tts.mp3"
        try:
            await tts.save(output_file)
            # Upewnij się, że poprzedni TTS został zatrzymany
            self.cancel()
            self.current_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", output_file]
            )
            await asyncio.to_thread(self.current_process.wait)
        except Exception as e:
            logger.error("TTS error: %s", e)
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)
            self.current_process = None

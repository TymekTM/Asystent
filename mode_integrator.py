import json
import logging
from pathlib import Path

from client.audio_modules.tts_module import TTSModule as OpenAITTS
from client.audio_modules.bing_tts_module import TTSModule as BingTTS
from client.audio_modules.whisper_asr import create_whisper_asr
from client.audio_modules.openai_asr import create_openai_asr

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CONFIG_PATH = Path(__file__).parent / "client" / "configs" / "user_modes.json"


def _load_mode() -> str:
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("current_level", "free")
    except Exception as e:
        logger.error(f"Failed to load user mode: {e}")
    return "free"


class UserModeIntegrator:
    def __init__(self):
        self.mode = _load_mode()
        logger.info(f"Loaded user mode: {self.mode}")
        if self.mode == "free":
            self.tts_module = BingTTS()
            self.asr_module = create_whisper_asr({})
        else:
            self.tts_module = OpenAITTS()
            self.asr_module = create_openai_asr({})


user_integrator = UserModeIntegrator()


import torch
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)


class WhisperASR:
    def __init__(self, model_name="openai/whisper-small"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Ładowanie modelu Whisper ({model_name}) na urządzeniu {device}...")
        self.asr = pipeline("automatic-speech-recognition", model=model_name, device=0 if device == "cuda" else -1)

    def transcribe(self, audio, sample_rate=16000):
        logger.info("Transkrypcja audio przez Whisper...")
        result = self.asr(audio)
        return result.get("text", "")

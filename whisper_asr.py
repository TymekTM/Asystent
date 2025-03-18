import torch, logging
from transformers import pipeline

logger = logging.getLogger(__name__)

class WhisperASR:
    def __init__(self, model_name="openai/whisper-small"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading Whisper model ({model_name}) on {device}...")
        self.asr = pipeline("automatic-speech-recognition", model=model_name, device=0 if device=="cuda" else -1)

    def transcribe(self, audio, sample_rate=16000):
        logger.info("Transcribing audio with Whisper...")
        result = self.asr(audio)
        return result.get("text", "")

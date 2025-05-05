import torch, logging
from transformers import pipeline
from performance_monitor import measure_performance

logger = logging.getLogger(__name__)


class WhisperASR:
    def __init__(self, model_name="openai/whisper-small"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading Whisper model ({model_name}) on {device}...")
        self.asr = pipeline("automatic-speech-recognition", model=model_name, device=0 if device=="cuda" else -1)
        
    @measure_performance
    def transcribe(self, audio, sample_rate=16000):
        logger.info("Transcribing audio with Whisper...")
        result = self.asr(audio)
        return result.get("text", "")

    def unload(self):
        """Unloads the Whisper model and clears CUDA cache if applicable."""
        if self.asr:
            logger.info(f"Unloading Whisper model ({self.asr.model.name_or_path})...")
            # Remove references to allow GC
            del self.asr
            self.asr = None
            if torch.cuda.is_available():
                logger.info("Clearing CUDA cache...")
                torch.cuda.empty_cache()
            logger.info("Whisper model unloaded.")
        else:
            logger.info("Whisper model already unloaded or not loaded.")

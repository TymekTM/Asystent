import sounddevice as sd
import numpy as np
import logging
from transformers import pipeline
import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def record_audio(duration=5, sample_rate=16000, device=5):
    logger.info(f"Recording for {duration} seconds using device id {device}...")
    audio = sd.rec(int(duration * sample_rate),
                   samplerate=sample_rate,
                   channels=1,
                   dtype='float32',
                   device=device)
    sd.wait()
    return audio.flatten()

def main():
    sample_rate = 16000
    duration = 5  # czas nagrania w sekundach
    mic_device_id = 5  # id mikrofonu

    audio = record_audio(duration, sample_rate, device=mic_device_id)
    logger.info("Audio recorded. Loading Whisper model on GPU...")

    # Sprawdzamy, czy GPU jest dostępne
    if torch.cuda.is_available():
        logger.info("GPU is available. Using GPU.")
        device_id = 0  # id GPU
    else:
        logger.info("GPU not available. Falling back to CPU.")
        device_id = -1

    # Tworzymy pipeline ASR. Używamy domyślnego zadania, które wykonuje transkrypcję (bez tłumaczenia)
    asr = pipeline("automatic-speech-recognition",
                   model="openai/whisper-small",
                   device="cuda")

    logger.info("Transcribing audio...")
    result = asr(audio)
    transcription = result.get("text", "")

    logger.info("Transcription: %s", transcription)
    print("Transcription:", transcription)

if __name__ == "__main__":
    main()

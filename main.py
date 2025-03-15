# main.py
import asyncio
import logging
from assistant import Assistant
from config import VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD

logging.basicConfig(
    level=logging.INFO,
    filename="assistant.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    assistant = Assistant(
        vosk_model_path=VOSK_MODEL_PATH,
        mic_device_id=MIC_DEVICE_ID,
        wake_word=WAKE_WORD,
        stt_silence_threshold=STT_SILENCE_THRESHOLD
    )
    try:
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant terminated by user.")
    except Exception as e:
        logger.error("Error: %s", e)

if __name__ == "__main__":
    main()

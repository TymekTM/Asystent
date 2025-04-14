# main.py
import asyncio, logging
from assistant import Assistant
# Config is loaded when assistant is imported, no need for direct config imports here
# from config import VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD

logging.basicConfig(
    level=logging.INFO,
    filename="assistant.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    # Assistant now initializes with defaults from the loaded config
    assistant = Assistant()
    try:
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant terminated by user.")
    except Exception as e:
        logger.error("Error: %s", e)

if __name__ == "__main__":
    main()

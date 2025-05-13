import multiprocessing
import asyncio
import logging
import logging.handlers 
import sys
import os
import time 
from threading import Thread

sys.path.append(os.path.join(os.path.dirname(__file__), 'web_ui'))

from assistant import Assistant
from web_ui.app import create_app 
from config import load_config 

# --- Logging Configuration ---
log_filename = os.path.join("user_data", "assistant.log")
log_level = logging.DEBUG 
log_format = "%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s"

# Use RotatingFileHandler for log rotation
if not os.path.exists("user_data"):
    os.makedirs("user_data", exist_ok=True)
rotating_handler = logging.handlers.RotatingFileHandler(
    log_filename, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8', mode='a'
)
stream_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[rotating_handler, stream_handler]
)
logging.getLogger().setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Process Target Functions ---

def run_assistant_process(queue: multiprocessing.Queue):
    """Target function to run the Assistant in its own process."""
    logger.info("Starting Assistant process...")
    try:
        assistant = Assistant(command_queue=queue)
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant process received KeyboardInterrupt. Exiting.")
    except Exception as e:
        logger.error(f"Critical error in Assistant process: {e}", exc_info=True)
    finally:
        logger.info("Assistant process finished.")
        if 'assistant' in locals() and hasattr(assistant, 'stop_active_window_tracker'):
            assistant.stop_active_window_tracker() # Ensure tracker is stopped on exit

def run_flask_process(queue: multiprocessing.Queue):
    """Target function to run the Flask Web UI in its own process."""
    logger.info("Starting Flask Web UI process...")
    try:
        flask_app = create_app(queue)
        flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Flask process received KeyboardInterrupt. Exiting.")
    except Exception as e:
        logger.error(f"Critical error in Flask process: {e}", exc_info=True)
    finally:
        logger.info("Flask process finished.")

# --- Main Execution ---

def main():
    logger.info("Initializing application...")
    # Ensure database schema is initialized (creates chat_history, memories, etc.)
    try:
        from database_models import init_schema
        init_schema()
        logger.info("Database schema initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}", exc_info=True)

    # Create a multiprocessing queue for IPC
    command_queue = multiprocessing.Queue()

    config = load_config()
    exit_with_console = config.get('EXIT_WITH_CONSOLE', True)
    
    # Usuń stare pliki lock przy starcie, jeśli istnieją
    stop_lock_path = os.path.join(os.path.dirname(__file__), 'assistant_stop.lock')
    restart_lock_path = os.path.join(os.path.dirname(__file__), 'assistant_restarting.lock')
    if os.path.exists(stop_lock_path):
        os.remove(stop_lock_path)
    if os.path.exists(restart_lock_path):
        os.remove(restart_lock_path)
        
    logger.info("Starting Flask process...")

    # --- Assistant Process ---
    assistant_process = multiprocessing.Process(target=run_assistant_process, args=(command_queue,))
    assistant_process.start()

    # --- Flask Process ---
    flask_process = multiprocessing.Process(target=run_flask_process, args=(command_queue,))
    flask_process.start()

    try:
        while True:
            # Check for stop signal (e.g., from web UI or other mechanism)
            if os.path.exists(stop_lock_path):
                logger.info("Stop signal detected. Terminating processes.")
                break 
            
            if not assistant_process.is_alive():
                logger.warning("Assistant process died. Attempting to restart...")
                # The 'assistant' instance from the dead process is out of scope here.
                # Cleanup for that instance is handled in its own 'run_assistant_process' finally block.
                assistant_process = multiprocessing.Process(target=run_assistant_process, args=(command_queue,))
                assistant_process.start()
                logger.info("Assistant process restarted.")

            if not flask_process.is_alive():
                logger.warning("Flask process died. Attempting to restart...")
                flask_process = multiprocessing.Process(target=run_flask_process, args=(command_queue,))
                flask_process.start()
                logger.info("Flask process restarted.")
            
            time.sleep(5)  # Check every 5 seconds

    except KeyboardInterrupt:
        logger.info("Main process received KeyboardInterrupt. Terminating child processes.")
    finally:
        logger.info("Terminating child processes...")
        if assistant_process.is_alive():
            assistant_process.terminate()
            assistant_process.join(timeout=5)
            if assistant_process.is_alive(): # Force kill if terminate failed
                logger.warning("Assistant process did not terminate gracefully, killing.")
                assistant_process.kill()
                assistant_process.join()


        if flask_process.is_alive():
            flask_process.terminate()
            flask_process.join(timeout=5)
            if flask_process.is_alive(): # Force kill if terminate failed
                logger.warning("Flask process did not terminate gracefully, killing.")
                flask_process.kill()
                flask_process.join()
        
        # Clean up lock files on exit
        if os.path.exists(stop_lock_path):
            os.remove(stop_lock_path)
        if os.path.exists(restart_lock_path):
            os.remove(restart_lock_path)

        logger.info("Application shut down.")

if __name__ == "__main__":
    multiprocessing.freeze_support() # Important for Windows
    main()

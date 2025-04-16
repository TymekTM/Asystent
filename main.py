import multiprocessing
import asyncio
import logging
import logging.handlers  # Add this import
import sys
import os
import time # Import the time module
from threading import Thread

# Ensure the web_ui directory is in the Python path if running main.py from the root
# This might not be necessary depending on how the project is structured/run,
# but it's safer for direct execution of main.py.
sys.path.append(os.path.join(os.path.dirname(__file__), 'web_ui'))

# Import necessary components
from assistant import Assistant
from web_ui.app import create_app # Import the factory function
from config import load_config # Import load_config from config.py

# --- Logging Configuration ---
# Configure root logger - both processes will inherit this
log_filename = "assistant.log"
log_level = logging.INFO # Zmieniono z INFO na WARNING
log_format = "%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s"

# Use RotatingFileHandler for log rotation
rotating_handler = logging.handlers.RotatingFileHandler(
    log_filename, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8', mode='a'
)
stream_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[rotating_handler, stream_handler]
)
logger = logging.getLogger(__name__)

# --- Process Target Functions ---

def run_assistant_process(queue: multiprocessing.Queue):
    """Target function to run the Assistant in its own process."""
    logger.info("Starting Assistant process...")
    try:
        assistant = Assistant(command_queue=queue)
        # Ustaw callback do obsługi zapytań (AI/STT)
        async def process_query_callback(text):
            await assistant.process_query(text)
        assistant.process_query_callback = process_query_callback
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant process received KeyboardInterrupt. Exiting.")
    except Exception as e:
        logger.error(f"Critical error in Assistant process: {e}", exc_info=True)
    finally:
        logger.info("Assistant process finished.")

def run_flask_process(queue: multiprocessing.Queue):
    """Target function to run the Flask Web UI in its own process."""
    logger.info("Starting Flask Web UI process...")
    try:
        # Create the Flask app using the factory, passing the queue
        flask_app = create_app(queue)
        # Run the Flask app
        # Use '0.0.0.0' to make it accessible on the network
        # Turn off debug mode and reloader for production/multiprocessing stability
        # Port can be loaded from config if needed
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
            # Sprawdź, czy istnieje plik stop_lock
            if os.path.exists(stop_lock_path):
                logger.warning("Detected stop signal via lock file. Shutting down.")
                os.remove(stop_lock_path)  # Usuń plik lock
                break
                
            if exit_with_console:
                # Wait for both processes, exit if parent dies
                assistant_process.join(0.5)
                flask_process.join(0.5)
                if not assistant_process.is_alive() or not flask_process.is_alive():
                    logger.warning("Detected process exit, shutting down main.")
                    break
            else:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Main process received KeyboardInterrupt. Exiting.")
    finally:
        logger.info("Terminating child processes...")
        # Usuń pliki lock przy zamykaniu, jeśli istnieją
        if os.path.exists(stop_lock_path):
            os.remove(stop_lock_path)
        if os.path.exists(restart_lock_path):
            os.remove(restart_lock_path)
        # Zamknij procesy
        assistant_process.terminate()
        flask_process.terminate()
        assistant_process.join()
        flask_process.join()
        logger.info("All processes terminated.")

if __name__ == "__main__":
    # Required for multiprocessing to work correctly on Windows when freezing apps
    # Also good practice on other platforms.
    multiprocessing.freeze_support()
    main()

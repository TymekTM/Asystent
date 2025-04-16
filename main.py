import multiprocessing
import asyncio
import logging
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

# Use basicConfig for simplicity, or add handlers as needed
logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.FileHandler(log_filename, mode='a', encoding='utf-8'), # Log to file
        logging.StreamHandler(sys.stdout) # Also log to console
    ]
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

    # --- Flask Process (runs once) ---
    flask_proc = multiprocessing.Process(
        target=run_flask_process,
        args=(command_queue,),
        name="FlaskProcess"
    )
    logger.info("Starting Flask process...")
    flask_proc.start()

    # --- Assistant Process (runs in a loop for restarts) ---
    assistant_proc = None
    restart_assistant = True

    try:
        while restart_assistant:
            logger.info("Starting Assistant process...")
            assistant_proc = multiprocessing.Process(
                target=run_assistant_process,
                args=(command_queue,),
                name="AssistantProcess"
            )
            assistant_proc.start()

            # Wait for the assistant process to finish
            assistant_proc.join()

            # Check if the process exited normally (exitcode 0)
            # We assume a normal exit (like after config update) means restart
            if assistant_proc.exitcode == 0:
                logger.info("Assistant process finished cleanly (exit code 0). Restarting...")
                restart_assistant = True
                time.sleep(2) # Short delay before restarting
            else:
                logger.warning(f"Assistant process terminated unexpectedly with exit code {assistant_proc.exitcode}. Not restarting automatically.")
                restart_assistant = False # Stop looping if it crashed

        # If the loop finishes (e.g., assistant crashed), wait for Flask to finish (or be interrupted)
        logger.info("Assistant restart loop finished. Waiting for Flask process...")
        if flask_proc.is_alive():
            flask_proc.join()

    except KeyboardInterrupt:
        logger.warning("Main process received KeyboardInterrupt. Terminating child processes...")
        # Terminate processes gracefully if possible, forcefully if needed
        if flask_proc and flask_proc.is_alive():
            flask_proc.terminate()
            flask_proc.join(timeout=5)
            if flask_proc.is_alive():
                 logger.warning("Flask process did not terminate gracefully, killing.")
                 flask_proc.kill()

        if assistant_proc and assistant_proc.is_alive():
            assistant_proc.terminate()
            assistant_proc.join(timeout=5)
            if assistant_proc.is_alive():
                 logger.warning("Assistant process did not terminate gracefully, killing.")
                 assistant_proc.kill()

    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}", exc_info=True)
        # Attempt to terminate child processes on main process error
        if flask_proc.is_alive(): flask_proc.kill()
        if assistant_proc.is_alive(): assistant_proc.kill()

    finally:
        logger.info("Application shutting down.")
        # Clean up queue if necessary (usually handled by process exit)
        command_queue.close()
        command_queue.join_thread()


if __name__ == "__main__":
    # Required for multiprocessing to work correctly on Windows when freezing apps
    # Also good practice on other platforms.
    multiprocessing.freeze_support()
    main()

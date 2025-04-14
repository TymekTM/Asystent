import multiprocessing
import asyncio
import logging
import sys
import os
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
log_level = logging.INFO # Or load from config if needed
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
        # Pass the queue to the Assistant
        assistant = Assistant(command_queue=queue)
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

    # Create processes
    assistant_proc = multiprocessing.Process(
        target=run_assistant_process,
        args=(command_queue,),
        name="AssistantProcess" # Assign a name for easier logging
    )
    flask_proc = multiprocessing.Process(
        target=run_flask_process,
        args=(command_queue,),
        name="FlaskProcess" # Assign a name for easier logging
    )

    try:
        # Start processes
        logger.info("Starting child processes...")
        assistant_proc.start()
        flask_proc.start()

        # Wait for processes to finish (e.g., on KeyboardInterrupt)
        # You might want more sophisticated monitoring/restart logic here
        assistant_proc.join()
        flask_proc.join()

    except KeyboardInterrupt:
        logger.warning("Main process received KeyboardInterrupt. Terminating child processes...")
        # Terminate processes gracefully if possible, forcefully if needed
        if flask_proc.is_alive():
            flask_proc.terminate() # Send SIGTERM
            flask_proc.join(timeout=5) # Wait a bit
            if flask_proc.is_alive():
                 logger.warning("Flask process did not terminate gracefully, killing.")
                 flask_proc.kill() # Send SIGKILL

        if assistant_proc.is_alive():
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

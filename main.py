import multiprocessing
import asyncio
import logging
import logging.handlers 
import sys
import os
import time 
import threading
from threading import Thread

# Add current directory to Python path for PyInstaller
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    application_path = os.path.dirname(sys.executable)
    script_dir = sys._MEIPASS
else:
    # Running in normal Python environment
    application_path = os.path.dirname(os.path.abspath(__file__))
    script_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.join(script_dir, 'web_ui'))

# Early path setup for dependencies when running from PyInstaller
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle - set up dependencies path early
    deps_path = os.path.join(application_path, "dependencies", "packages")
    if os.path.exists(deps_path) and deps_path not in sys.path:
        sys.path.append(deps_path)

# Dependency management for PyInstaller builds - moved to main() to avoid multiprocessing issues

# Import main modules
from assistant import Assistant
from config import load_config

# Import Flask app creation function at module level for multiprocessing
try:
    from web_ui.app import create_app 
except ImportError as e:
    print(f"Warning: Failed to import Flask app: {e}")
    create_app = None

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

def run_flask_thread(queue: multiprocessing.Queue):
    """Target function to run the Flask Web UI in its own thread."""
    try:
        logger.info("Starting Flask Web UI thread...")
        
        # Check if create_app was imported successfully
        if create_app is None:
            logger.error("Flask app creation function not available")
            return
            
        logger.info("Creating Flask app...")
        flask_app = create_app(queue)
        logger.info("Flask app created successfully")
        
        port = 5000 if getattr(sys, 'frozen', False) else 5001
        logger.info(f"Starting Flask server on port {port}...")
        
        # Run the Flask app
        flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
        
    except KeyboardInterrupt:
        logger.info("Flask thread received KeyboardInterrupt. Exiting.")
    except Exception as e:
        logger.error(f"Critical error in Flask thread: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Flask thread finished.")

# --- Main Execution ---

def main():
    # Set multiprocessing start method for Windows compatibility
    if sys.platform == "win32":
        multiprocessing.set_start_method('spawn', force=True)
    
    # Dependency management for PyInstaller builds - only run in main process
    if getattr(sys, 'frozen', False):
        try:
            from dependency_manager import ensure_dependencies
            print("🔄 Sprawdzanie zależności...")
            if not ensure_dependencies():
                print("❌ Nie udało się zainicjalizować zależności!")
                print("🔍 Sprawdź połączenie internetowe i spróbuj ponownie")
                input("Naciśnij Enter aby zamknąć...")
                sys.exit(1)
            print("✅ Zależności gotowe")
        except Exception as e:
            print(f"⚠️  Ostrzeżenie menedżera zależności: {e}")
            print("🔄 Kontynuuję bez automatycznego pobierania zależności...")
            # Kontynuuj bez menedżera zależności - może działać z systemowym Python
    
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
        
    logger.info("Starting Flask thread...")

    # --- Assistant Process ---
    assistant_process = multiprocessing.Process(target=run_assistant_process, args=(command_queue,))
    assistant_process.start()    # --- Flask Thread ---
    flask_thread = Thread(target=run_flask_thread, args=(command_queue,), daemon=True)
    flask_thread.start()
    
    # Check if this is the first run and open onboarding if needed
    if config.get('FIRST_RUN', True):
        logger.info("First run detected, preparing to launch onboarding...")
        import webbrowser
        import requests
        from requests.exceptions import RequestException

        def open_onboarding_with_retry(max_retries: int = 30, retry_delay: float = 1.0) -> bool:
            """Open onboarding page with retry mechanism to ensure Flask is ready"""
            # Use correct port based on whether running from exe or development
            port = 5000 if getattr(sys, 'frozen', False) else 5001
            for attempt in range(max_retries):
                try:
                    # Test if Flask server is ready by checking the onboarding endpoint
                    response = requests.get(f"http://localhost:{port}/onboarding", timeout=2)
                    if response.status_code == 200:
                        # Server is ready, open the onboarding page
                        webbrowser.open(f"http://localhost:{port}/onboarding")
                        logger.info(f"Opened onboarding page in browser after {attempt+1} attempts")
                        return True
                    else:
                        logger.warning(f"Onboarding endpoint returned status code {response.status_code}")
                except RequestException:
                    logger.debug(f"Server not ready yet (attempt {attempt+1})")

                logger.info(f"Flask server not ready yet, retrying in {retry_delay}s (attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)

            logger.error(f"Failed to open onboarding page after {max_retries} attempts")
            return False        # Start a separate thread to handle the retries without blocking main execution
        Thread(target=open_onboarding_with_retry, daemon=True).start()

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
            
            if not flask_thread.is_alive():
                logger.warning("Flask thread died. Attempting to restart...")
                flask_thread = Thread(target=run_flask_thread, args=(command_queue,), daemon=True)
                flask_thread.start()
                logger.info("Flask thread restarted.")
            
            # Check for restart signal
            if os.path.exists(restart_lock_path):
                logger.info("Restart signal detected. Restarting processes...")
                # Terminate existing processes
                if assistant_process.is_alive():
                    assistant_process.terminate()
                    assistant_process.join(timeout=5)
                # Note: Flask thread will be terminated when main process ends
                
                # Remove restart lock
                os.remove(restart_lock_path)
                
                # Start new processes
                assistant_process = multiprocessing.Process(target=run_assistant_process, args=(command_queue,))
                assistant_process.start()
                flask_thread = Thread(target=run_flask_thread, args=(command_queue,), daemon=True)
                flask_thread.start()
                logger.info("Processes restarted successfully.")
                
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

        # Flask thread will terminate when main process ends (daemon=True)
        
        # Clean up lock files on exit
        if os.path.exists(stop_lock_path):
            os.remove(stop_lock_path)
        if os.path.exists(restart_lock_path):
            os.remove(restart_lock_path)

        logger.info("Application shut down.")

if __name__ == "__main__":
    multiprocessing.freeze_support() # Important for Windows
    main()

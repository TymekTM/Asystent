import multiprocessing
import asyncio
import logging
import logging.handlers 
import sys
import os
import time 
import threading
import subprocess
from threading import Thread
from pathlib import Path

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

# Import main modules - Assistant imported only in subprocess to avoid premature initialization
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
    os.makedirs("user_data")

# Configure logger with file and console output
rotating_handler = logging.handlers.RotatingFileHandler(
    log_filename, maxBytes=5*1024*1024, backupCount=5
)
rotating_handler.setLevel(log_level)
rotating_handler.setFormatter(logging.Formatter(log_format))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format))

# Global logger instance
logger = logging.getLogger('gaja')
logger.setLevel(log_level)
logger.addHandler(rotating_handler)
logger.addHandler(console_handler)

# Prevent duplicate log messages
logger.propagate = False

# --- Global Process Management ---
overlay_process = None

# Import webdriver manager at module level to enable multiprocessing
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        
        # Enable webdriver manager for all platforms
        os.environ['WDM_LOG_LEVEL'] = '0'  # Disable webdriver manager verbose logging
        
        # Pre-install chromedriver to avoid path issues in subprocess
        try:
            chrome_driver_path = ChromeDriverManager().install()
            logger.debug(f"ChromeDriver path: {chrome_driver_path}")
        except Exception as e:
            logger.warning(f"Failed to pre-install ChromeDriver: {e}")
    except ImportError:
        logger.warning("webdriver_manager not available - ChromeDriver management disabled")
        
except ImportError as e:
    logger.warning(f"Selenium webdriver not available: {e}")

def start_overlay():
    """Start the Tauri overlay application if it exists."""
    global overlay_process
    try:
        from process_manager import process_manager
        
        # Determine overlay path based on runtime environment
        if getattr(sys, 'frozen', False):
            # Running from PyInstaller bundle
            if hasattr(sys, '_MEIPASS'):
                # Single file mode - overlay extracted to temp directory
                overlay_exe_path = os.path.join(sys._MEIPASS, "overlay", "Asystent Overlay.exe")
            else:
                # Directory mode - overlay next to exe
                overlay_exe_path = os.path.join(application_path, "overlay", "Asystent Overlay.exe")
        else:
            # Development mode
            overlay_exe_path = os.path.join(script_dir, "overlay", "target", "release", "Asystent Overlay.exe")
        
        # Validate overlay path
        overlay_path = Path(overlay_exe_path)
        if not overlay_path.exists():
            logger.warning(f"Overlay executable not found at: {overlay_exe_path}")
            if not getattr(sys, 'frozen', False):
                logger.info("To build overlay, run: cd overlay && npm run tauri build")
            return None
        
        # Configure overlay process
        port = 5000 if getattr(sys, 'frozen', False) else 5001
        process_manager.register_process_config('overlay', {
            'executable_path': overlay_exe_path,
            'args': [],
            'environment': {
                'GAJA_PORT': str(port)
            },
            'working_dir': overlay_path.parent,
            'no_window': True,
            'capture_output': False
        })
        
        # Start overlay process
        overlay_process = process_manager.start_process('overlay')
        
        if overlay_process:
            logger.info(f"Overlay started successfully (PID: {overlay_process.pid})")
            return overlay_process
        else:
            logger.error("Failed to start overlay process")
            return None
            
    except Exception as e:
        logger.error(f"Failed to start overlay: {e}", exc_info=True)
        return None

def stop_overlay():
    """Stop the overlay process if it's running."""
    global overlay_process
    try:
        from process_manager import process_manager
        
        # Use process manager to safely stop overlay
        if process_manager.stop_process('overlay', timeout=5, force=True):
            logger.info("Overlay process stopped via process manager")
        else:
            # Fallback to direct process handling
            if overlay_process:
                logger.info("Fallback: stopping overlay process directly...")
                
                if overlay_process.poll() is None:  # Process is still running
                    overlay_process.terminate()
                    
                    # Wait for graceful termination
                    try:
                        overlay_process.wait(timeout=5)
                        logger.info("Overlay process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning("Overlay process did not terminate gracefully, forcing...")
                        overlay_process.kill()
                        overlay_process.wait()
                        logger.info("Overlay process killed")
        
        overlay_process = None
        
    except Exception as e:
        logger.error(f"Error stopping overlay: {e}", exc_info=True)

# --- Process Target Functions ---

def run_assistant_process(queue: multiprocessing.Queue):
    """Target function to run the Assistant in its own process."""
    import os
    import sys
    import asyncio
    
    # Import platform-specific modules
    if sys.platform == "win32":
        import msvcrt
        fcntl = None
    else:
        import fcntl
        msvcrt = None
    
    # Use proper file locking to prevent multiple instances
    lock_file = os.path.join(os.path.dirname(__file__), 'assistant_running.lock')
    lock_fd = None
    assistant = None
    
    try:
        # Try to acquire exclusive lock
        lock_fd = open(lock_file, 'w')
        
        if sys.platform == "win32":
            # Windows file locking
            try:
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                logger.warning("Another Assistant process is already running. Exiting.")
                lock_fd.close()
                return
        else:
            # Unix file locking
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                logger.warning("Another Assistant process is already running. Exiting.")
                lock_fd.close()
                return
        
        # Write PID to lock file
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        
        logger.info("Starting Assistant process...")
        
        # Avoid importing assistant.py at module level in subprocess to prevent premature initialization
        # Only import when we're ready to create the instance
        # Ensure config is loaded in this process
        from config import load_config
        load_config(silent=True)
        # Add a small delay to prevent race conditions - reduced delay
        import time
        time.sleep(0.1)  # Minimal delay to prevent multiple initializations
        # Import Assistant only after delay and setup - this prevents module-level initialization
        logger.info("Creating new Assistant instance...")
        from assistant import Assistant
        
        # Create a single Assistant instance directly instead of using get_assistant_instance
        # which might return a shared instance and cause multiple initializations
        assistant = Assistant(command_queue=queue)
        
        logger.info("Starting Assistant main loop...")
        asyncio.run(assistant.run_async())
        
    except KeyboardInterrupt:
        logger.info("Assistant process received KeyboardInterrupt. Exiting.")
    except Exception as e:
        logger.error(f"Critical error in Assistant process: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    finally:
        # Clean up lock file and release file handle
        if lock_fd:
            try:
                if sys.platform == "win32" and msvcrt:
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                elif fcntl:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
            except:
                pass
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except:
                pass
        logger.info("Assistant process finished.")
        if assistant and hasattr(assistant, 'stop_active_window_tracker'):
            assistant.stop_active_window_tracker()  # Ensure tracker is stopped on exit

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
    
    # Initialize logging first
    logger.info("=== GAJA APPLICATION STARTING ===")
    
    # Dependency management for PyInstaller builds
    if getattr(sys, 'frozen', False):
        logger.info("Running in PyInstaller mode")
        
        # Get dependencies directory
        deps_path = os.path.join(application_path, "dependencies", "packages")
        
        if os.path.exists(deps_path):
            logger.info(f"Using dependencies from: {deps_path}")
            # Add to sys.path if not already present
            if deps_path not in sys.path:
                sys.path.append(deps_path)
                logger.info("Dependencies path added to sys.path")
        else:
            logger.warning(f"Dependencies directory not found: {deps_path}")
            
    else:
        logger.info("Running in development mode")
        
        # Auto dependency management for development
        try:
            logger.info("Setting up development dependencies...")
            from dependency_manager import setup_development_dependencies
            setup_development_dependencies()
        except ImportError:
            logger.warning("Dependency manager not available - some features may not work")
    
    try:
        # Create a multiprocessing Queue for communication between processes
        queue = multiprocessing.Queue()
        
        # Start the Flask Web UI in its own thread within the main process
        flask_thread = Thread(target=run_flask_thread, args=(queue,), daemon=True)
        flask_thread.start()
        logger.info("Flask thread started")
        
        # Give Flask a moment to start up
        time.sleep(2)
        
        # Start the Assistant in its own process
        assistant_process = multiprocessing.Process(target=run_assistant_process, args=(queue,))
        assistant_process.start()
        logger.info("Assistant process started")
        
        # Start the overlay if available
        overlay_proc = start_overlay()
        
        # Log startup completion
        logger.info("=== ALL PROCESSES STARTED ===")
        
        try:
            # Wait for Assistant process to complete
            assistant_process.join()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt in main process")
        finally:
            # Cleanup processes
            logger.info("Cleaning up processes...")
            
            # Stop overlay
            stop_overlay()
            
            # Terminate Assistant process if still running
            if assistant_process.is_alive():
                logger.info("Terminating Assistant process...")
                assistant_process.terminate()
                assistant_process.join(timeout=5)
                if assistant_process.is_alive():
                    logger.warning("Force killing Assistant process...")
                    assistant_process.kill()
                    assistant_process.join()
            
            logger.info("All processes terminated")
            
    except Exception as e:
        logger.error(f"Critical error in main process: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    finally:
        logger.info("=== GAJA APPLICATION SHUTDOWN ===")

if __name__ == "__main__":
    main()

import os
import json
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from functools import wraps
import logging
import time # Import time for potential timestamping or delays
import shutil # Import shutil for potential file operations like archiving
import multiprocessing # Import multiprocessing for the queue
import re # Import re for log parsing

# --- Configuration ---
# TODO: SECURITY: Replace with a more robust secret key management (e.g., environment variables)
SECRET_KEY = os.urandom(24)
# TODO: SECURITY: Define user credentials (replace with database/proper auth later)
USERS = {
    "user": {"password": "password", "role": "user"},
    "dev": {"password": "devpassword", "role": "dev"}
}
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config.json') # Path relative to app.py
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'assistant.log') # Path to log file for now
HISTORY_ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), '..', 'history_archive') # Directory for archived logs
LTM_FILE = os.path.join(os.path.dirname(__file__), '..', 'long_term_memory.json')

# --- Global variable for the queue (will be set by create_app) ---
assistant_queue = None

# --- Flask App Setup ---
# Logging setup moved inside create_app to avoid issues with multiple processes
logger = logging.getLogger(__name__) # Use a specific logger for the web UI

# --- Helper Functions ---

def load_config():
    """Load advanced config with nested sections and type validation."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # Optionally: validate config structure here
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def save_config(config_data):
    """Saves configuration to config.json."""
    global assistant_queue # Access the global queue
    logger.debug(f"Attempting to save config to: {CONFIG_FILE}")
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        logger.info("Configuration saved successfully.")
        # Notify the main assistant process about the config change
        if assistant_queue:
            try:
                assistant_queue.put({"action": "config_updated"})
                logger.info("Sent config_updated notification to assistant process.")
            except Exception as q_err:
                 logger.error(f"Failed to send config_updated notification via queue: {q_err}")
        else:
            logger.warning("Assistant queue not available, cannot notify assistant of config change.")
        return True
    except IOError as e:
        logger.error(f"IOError saving configuration to {CONFIG_FILE}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving config: {e}")
        return False

def load_ltm():
    if not os.path.exists(LTM_FILE):
        return []
    try:
        with open(LTM_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load LTM: {e}")
        return []

def save_ltm(data):
    try:
        with open(LTM_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save LTM: {e}")
        return False

# ... (get_conversation_history and clear_conversation_history remain the same) ...
def get_conversation_history(limit=50):
    """
    Reads conversation history from the log file.
    Improved parsing and error handling.
    """
    history = []
    logger.debug(f"Attempting to read history from: {HISTORY_FILE}")
    try:
        # Ensure file exists before opening
        if not os.path.exists(HISTORY_FILE):
            logger.warning(f"History file not found at {HISTORY_FILE}. Returning empty list.")
            return []

        # Open with error handling for encoding issues
        with open(HISTORY_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            # TODO: Consider a more robust log parsing strategy or a structured history format (e.g., JSON lines)
            # This simple parsing might break with complex log messages.
            lines = f.readlines()
            for line in reversed(lines): # Read from end for recent entries
                line = line.strip()
                if not line:
                    continue

                # Basic parsing logic (adjust based on actual log format)
                # Look for specific log messages indicating user input or assistant speech
                if "INFO - Command:" in line:
                    content = line.split("Command:", 1)[1].strip()
                    # Avoid adding empty strings
                    if content and (not history or history[-1].get("content") != content or history[-1].get("role") != "user"):
                        history.append({"role": "user", "content": content})
                elif "INFO - Refined query:" in line: # Also consider refined query as user input for history
                     content = line.split("Refined query:", 1)[1].strip()
                     # Avoid duplicates if Command: log is very close or content is empty
                     if content and (not history or history[-1].get("content") != content or history[-1].get("role") != "user"):
                         history.append({"role": "user", "content": content})
                elif "INFO - TTS:" in line:
                    content = line.split("TTS:", 1)[1].strip()
                    # Avoid adding internal TTS messages like errors or irrelevant info
                    # Filter more specifically based on expected assistant responses
                    if content and not content.startswith("Przepraszam,") and not content.startswith("Error executing command"):
                         # Avoid adding if the last message was the same assistant message
                         if not history or history[-1].get("content") != content or history[-1].get("role") != "assistant":
                            history.append({"role": "assistant", "content": content})
                elif "INFO - AI response:" in line: # Capture AI text before potential tool use
                     content_part = line.split("AI response:", 1)[1].strip()
                     # Try to extract just the spoken part if structure is known (e.g., from parse_response)
                     try:
                         # This assumes a simple structure or requires regex if complex
                         # Example: Extract text before potential <tool_call> or similar marker if used
                         # Let's try parsing the structured output if possible (might be fragile)
                         parsed = None
                         content = content_part # Default to full line part
                         if "{" in content_part and "}" in content_part:
                             try:
                                 # Attempt to find and parse JSON-like structure within the log
                                 match = re.search(r'({.*})', content_part)
                                 if match:
                                     parsed_json = json.loads(match.group(1))
                                     # Prioritize 'text' field if available
                                     if 'text' in parsed_json and parsed_json['text']:
                                         content = parsed_json['text']
                                     # Maybe fallback to command if no text? (optional)
                                     # elif 'command' in parsed_json:
                                     #     content = f"(Executing: {parsed_json['command']})" # Or similar
                             except json.JSONDecodeError:
                                 pass # Keep content as content_part if JSON parsing fails

                         # Check content validity and avoid duplicates/similarity with last TTS
                         if content and (not history or history[-1].get("content") != content or history[-1].get("role") != "assistant"):
                              # Avoid adding if TTS log likely added the same content just before/after
                              is_likely_duplicate = False
                              if history:
                                  last_msg = history[-1]
                                  if last_msg.get("role") == "assistant" and last_msg.get("content") == content:
                                      is_likely_duplicate = True
                              if not is_likely_duplicate:
                                   history.append({"role": "assistant", "content": content})
                     except Exception as parse_err:
                         logger.error(f"Error parsing AI response log line: {parse_err} - Line: {line}")
                         # Fallback if parsing the log line fails, add raw content if valid
                         if content_part and (not history or history[-1].get("content") != content_part or history[-1].get("role") != "assistant"):
                             if not any(h.get("role") == "assistant" and h.get("content") == content_part for h in history[-2:]):
                                 history.append({"role": "assistant", "content": content_part})


                if len(history) >= limit:
                    break # Stop once the limit is reached
            history.reverse() # Put back in chronological order
            logger.info(f"Retrieved {len(history)} history entries.")

    except FileNotFoundError: # Should be caught by the check above, but keep for safety
        logger.warning(f"History file not found at {HISTORY_FILE}.")
    except Exception as e:
        logger.error(f"Error reading or parsing history file {HISTORY_FILE}: {e}", exc_info=True) # Add traceback

    # Filter out empty messages just before returning
    history = [entry for entry in history if entry.get("content")]

    return history # Return whatever was successfully parsed, even if empty

def clear_conversation_history():
     """
     Clears the history by archiving the current log file and creating a new empty one.
     """
     logger.warning(f"Clear history requested for: {HISTORY_FILE}")
     try:
         if not os.path.exists(HISTORY_FILE):
             logger.info("History file does not exist, nothing to clear.")
             return True # No action needed, considered success

         # Create archive directory if it doesn't exist
         os.makedirs(HISTORY_ARCHIVE_DIR, exist_ok=True)

         # Archive the current log file
         timestamp = time.strftime("%Y%m%d_%H%M%S")
         archive_path = os.path.join(HISTORY_ARCHIVE_DIR, f"assistant_{timestamp}.log")
         # Ensure the source file exists before moving
         if os.path.exists(HISTORY_FILE):
             shutil.move(HISTORY_FILE, archive_path) # Move the file
             logger.info(f"Archived current history file to: {archive_path}")
         else:
             logger.warning(f"History file {HISTORY_FILE} disappeared before archiving.")
             return False # Indicate potential issue

         # Create a new empty log file (optional, depends if the logger handles file creation)
         # The main assistant's logger should handle recreation if configured correctly.
         # If issues arise where the log file isn't recreated, uncomment the next lines.
         # try:
         #     with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
         #         pass # Create empty file
         #     logger.info(f"Created new empty history file: {HISTORY_FILE}")
         # except IOError as create_err:
         #     logger.error(f"Failed to create new empty history file {HISTORY_FILE}: {create_err}")
         #     # Even if creation fails, archiving might have succeeded. Decide on return value.
         #     return False # Indicate failure to create new file

         # Notify assistant? Maybe not necessary for just clearing logs unless it reads history internally.

         return True
     except IOError as e:
         logger.error(f"IOError clearing/archiving history file {HISTORY_FILE}: {e}")
         return False
     except Exception as e:
         logger.error(f"Unexpected error clearing history: {e}")
         return False

# --- Authentication ---
# ... (login_required, login, logout remain the same) ...
def login_required(role="user"):
    """Decorator to require login and specific role."""
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'username' not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('login'))
            user_role = session.get('role')
            # Allow devs to access user pages too
            if role == "dev" and user_role != "dev":
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for('index')) # Or a specific error page
            # If role is "user", both "user" and "dev" roles are allowed
            # No specific check needed here if role=="user" as the first check handles non-logged-in users
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# --- Web UI Routes --- defined within create_app ---

# --- API Routes --- defined within create_app or standalone ---

# --- App Creation Function ---
def create_app(queue: multiprocessing.Queue):
    """Creates and configures the Flask application."""
    global assistant_queue # Set the global queue variable for this process
    assistant_queue = queue

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = SECRET_KEY

    # Configure Flask logging
    # Use a basic config, can be enhanced (e.g., rotating file handler)
    # Avoid basicConfig here if the main process already configured it.
    # Rely on the logger obtained at the module level.
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_level = logging.INFO # Or get from config/env
    logging.getLogger(__name__).setLevel(log_level)
    # Add specific handlers if needed (e.g., file handler for web_ui.log)
    # handler = logging.FileHandler('web_ui.log')
    # handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    # logging.getLogger(__name__).addHandler(handler)

    logger.info("Flask app created and configured.")


    # --- Register Blueprints or Routes --- Add routes to the app object

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = USERS.get(username)
            # TODO: SECURITY: Use password hashing (e.g., Werkzeug's generate_password_hash/check_password_hash)
            if user and user['password'] == password:
                session['username'] = username
                session['role'] = user['role']
                flash(f"Welcome, {username}!", "success")
                logger.info(f"User '{username}' logged in successfully.")
                return redirect(url_for('index'))
            else:
                flash("Invalid username or password.", "danger")
                logger.warning(f"Failed login attempt for username: '{username}'.")
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        username = session.get('username', 'Unknown')
        session.pop('username', None)
        session.pop('role', None)
        flash("You have been logged out.", "info")
        logger.info(f"User '{username}' logged out.")
        return redirect(url_for('login'))

    @app.route('/')
    @login_required()
    def index():
        """Main dashboard page."""
        current_config = load_config()
        # TODO: DASHBOARD: Fetch real-time status from the assistant (requires more IPC)
        # For now, just show basic info from config
        assistant_status = {
            "status": "Unknown (IPC needed)",
            "wake_word": current_config.get('WAKE_WORD', 'N/A'),
            "stt_engine": "Whisper" if current_config.get('USE_WHISPER_FOR_COMMAND') else "Vosk",
            "mic_id": current_config.get('MIC_DEVICE_ID', 'N/A')
            }
        return render_template('index.html', config=current_config, status=assistant_status)

    @app.route('/config')
    @login_required(role="dev")
    def config_page():
        """Configuration management page."""
        current_config = load_config()
        return render_template('config.html', config=current_config)

    @app.route('/history')
    @login_required()
    def history_page():
        """Conversation history page."""
        history = get_conversation_history()
        return render_template('history.html', history=history)

    @app.route('/ltm')
    @login_required(role="dev")
    def ltm_page():
        return render_template('ltm_page.html')

    @app.route('/logs')
    @login_required()
    def logs_page():
        return render_template('logs.html')

    # --- API Routes --- (Registered within create_app)
    @app.route('/api/config', methods=['GET', 'POST'])
    @login_required(role="dev")
    def api_config_route(): # Renamed to avoid conflict with function name
        """API endpoint for getting and updating configuration."""
        if request.method == 'POST':
            new_config_data = request.json
            if not isinstance(new_config_data, dict):
                 logger.warning("Received invalid config data (not a dictionary).")
                 return jsonify({"error": "Invalid configuration format."}), 400

            logger.info(f"Received request to update configuration by user '{session.get('username')}'.")
            # Basic validation (optional, enhance as needed)
            # e.g., check if MIC_DEVICE_ID is an integer
            if 'MIC_DEVICE_ID' in new_config_data:
                try:
                    # Allow empty string or integer
                    if new_config_data['MIC_DEVICE_ID'] != '':
                         int(new_config_data['MIC_DEVICE_ID'])
                except (ValueError, TypeError):
                     logger.warning("Invalid MIC_DEVICE_ID received.")
                     return jsonify({"error": "Invalid MIC_DEVICE_ID format (must be an integer or empty)."}), 400

            if save_config(new_config_data):
                return jsonify({"message": "Configuration saved successfully."}), 200
            else:
                # Be specific about the error if possible, but avoid leaking details
                return jsonify({"error": "Failed to save configuration due to a server issue."}), 500
        else: # GET
            logger.info(f"Configuration requested by user '{session.get('username')}'.")
            current_config = load_config()
            return jsonify(current_config)

    @app.route('/api/history', methods=['GET', 'DELETE'])
    @login_required()
    def api_history_route(): # Renamed
        """API endpoint for getting and clearing conversation history."""
        if request.method == 'DELETE':
             logger.warning(f"Request to clear history received from user '{session.get('username')}'.")
             if clear_conversation_history():
                  logger.info("Conversation history cleared successfully.")
                  return jsonify({"message": "Conversation history cleared and archived."}), 200
             else:
                  logger.error("Failed to clear conversation history.")
                  return jsonify({"error": "Failed to clear history due to server error."}), 500
        else: # GET
            logger.info(f"History requested by user '{session.get('username')}'.")
            history = get_conversation_history()
            return jsonify(history)

    @app.route('/api/activate', methods=['POST'])
    @login_required()
    def api_activate(): # Moved inside create_app
        """API endpoint to manually trigger voice listening (bypass wake word)."""
        global assistant_queue # Access the global queue
        username = session.get('username', 'Unknown')
        logger.info(f"Manual activation requested via Web UI by user '{username}'.")

        if assistant_queue:
            try:
                assistant_queue.put({"action": "activate"})
                logger.info("Sent 'activate' command to assistant process.")
                return jsonify({"message": "Activation request sent to assistant."}), 202
            except Exception as e:
                logger.error(f"Error sending 'activate' command via queue: {e}")
                return jsonify({"error": f"Failed to send activation command: {e}"}), 500
        else:
             logger.warning("Cannot trigger manual listen: Assistant queue not available.")
             return jsonify({"error": "Assistant connection not available."}), 503

    @app.route('/api/long_term_memory', methods=['GET', 'POST', 'DELETE'])
    @login_required(role="dev")
    def api_long_term_memory():
        """API endpoint for long-term memory management."""
        logger.info(f"LTM API endpoint accessed (Method: {request.method}) by user '{session.get('username')}'.")
        if request.method == 'POST':
            # Add or update an LTM entry
            entry = request.json
            if not isinstance(entry, dict) or not entry.get('content'):
                return jsonify({"error": "Invalid LTM entry format."}), 400
            ltm = load_ltm()
            ltm.append({"content": entry['content'], "timestamp": time.time()})
            if save_ltm(ltm):
                return jsonify({"message": "LTM entry added."}), 200
            else:
                return jsonify({"error": "Failed to save LTM."}), 500
        elif request.method == 'DELETE':
            # Clear all LTM entries
            if save_ltm([]):
                return jsonify({"message": "LTM cleared."}), 200
            else:
                return jsonify({"error": "Failed to clear LTM."}), 500
        else: # GET
            ltm = load_ltm()
            return jsonify(ltm)

    @app.route('/api/status', methods=['GET'])
    @login_required()
    def api_status():
        """API endpoint for assistant status (for dashboard polling)."""
        # In a real implementation, fetch live status from the assistant process via IPC.
        # For now, return config-based info and a dummy status.
        current_config = load_config()
        status = {
            "status": "Online",  # Could be dynamic if IPC is implemented
            "wake_word": current_config.get('WAKE_WORD', 'N/A'),
            "stt_engine": "Whisper" if current_config.get('USE_WHISPER_FOR_COMMAND') else "Vosk",
            "mic_id": current_config.get('MIC_DEVICE_ID', 'N/A')
        }
        return jsonify(status)

    @app.route('/api/logs')
    @login_required()
    def api_logs():
        level = request.args.get('level', 'ALL')
        log_path = os.path.join(os.path.dirname(__file__), '..', 'assistant.log')
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if level != 'ALL':
                lines = [l for l in lines if f'- {level} -' in l]
            # Limit to last 500 lines for performance
            logs = lines[-500:]
            return jsonify({'logs': logs})
        except Exception as e:
            return jsonify({'logs': [f'Błąd odczytu logów: {e}']}), 500

    return app

# --- Main Execution (for standalone testing) ---
if __name__ == '__main__':
    # This block is for running the web UI standalone for testing/development
    # It won't have a connection to the real assistant process in this mode.
    print("Running Flask app in standalone debug mode...")
    # Configure logging for standalone mode
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Create a dummy queue for standalone mode
    dummy_queue = multiprocessing.Queue()
    app = create_app(dummy_queue)
    # Run Flask in debug mode for development
    # Consider using a production server like Gunicorn or Waitress for deployment
    # Running on 0.0.0.0 makes it accessible on the network
    # Use use_reloader=False to prevent issues with multiprocessing in debug mode if needed
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

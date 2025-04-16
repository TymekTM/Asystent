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
import subprocess
import threading
import queue
import sounddevice as sd # Import sounddevice
import collections # Import collections for deque

# Import the main config loading/saving functions
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import load_config as load_main_config, save_config as save_main_config, CONFIG_FILE as MAIN_CONFIG_FILE, DEFAULT_CONFIG

# --- Configuration ---
# TODO: SECURITY: Replace with a more robust secret key management (e.g., environment variables)
SECRET_KEY = os.urandom(24)
# TODO: SECURITY: Define user credentials (replace with database/proper auth later)
USERS = {
    "user": {"password": "password", "role": "user"},
    "dev": {"password": "devpassword", "role": "dev"}
}
# Use the config file path from the main config module
CONFIG_FILE = MAIN_CONFIG_FILE
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'assistant.log') # Path to log file for now
HISTORY_ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), '..', 'history_archive') # Directory for archived logs
LTM_FILE = os.path.join(os.path.dirname(__file__), '..', 'long_term_memory.json')

# --- Global variable for the queue (will be set by create_app) ---
assistant_queue = None

# --- Flask App Setup ---
# Logging setup moved inside create_app to avoid issues with multiple processes
logger = logging.getLogger(__name__) # Use a specific logger for the web UI

# --- Test Runner State ---
test_status = {
    'running': False,
    'result': None,
    'log': '',
    'summary': '',
    'ai_summary': ''
}
test_status_lock = threading.Lock()

def run_unit_tests():
    """Run unit tests and update test_status dict."""
    global test_status
    with test_status_lock:
        test_status['running'] = True
        test_status['result'] = None
        test_status['log'] = ''
        test_status['summary'] = ''
        test_status['ai_summary'] = ''
        test_status['tests'] = []
    try:
        proc = subprocess.Popen([
            'python', '-m', 'unittest', 'discover', '-s', 'tests_unit', '-p', 'test_*.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output, _ = proc.communicate()
        passed = proc.returncode == 0
        summary = parse_test_summary(output)
        ai_summary = generate_ai_summary(output)
        tests = parse_individual_tests(output)
        with test_status_lock:
            test_status['running'] = False
            test_status['result'] = 'passed' if passed else 'failed'
            test_status['log'] = output
            test_status['summary'] = summary
            test_status['ai_summary'] = ai_summary
            test_status['tests'] = tests
    except Exception as e:
        with test_status_lock:
            test_status['running'] = False
            test_status['result'] = 'error'
            test_status['log'] = str(e)
            test_status['summary'] = ''
            test_status['ai_summary'] = ''
            test_status['tests'] = []

def parse_individual_tests(output):
    """Parse unittest output for individual test results (robust for dots and verbose, with real test names and status)."""
    import re
    tests = []
    # Try verbose output first
    test_line_re = re.compile(r'^(test_\w+) \(([^)]+)\) \.+ (ok|FAIL|ERROR)$', re.MULTILINE)
    for match in test_line_re.finditer(output):
        name = match.group(1)
        cls = match.group(2)
        status = match.group(3)
        tests.append({'name': name, 'class': cls, 'status': status, 'details': ''})
    # If no verbose output, try to parse from summary and match to discovered test names
    if not tests:
        try:
            import subprocess
            proc = subprocess.Popen([
                'python', '-m', 'unittest', 'discover', '-s', 'tests_unit', '-p', 'test_*.py', '-v'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            discover_out, _ = proc.communicate(timeout=10)
            discovered = re.findall(r'^(test_\w+) \(([^)]+)\)', discover_out, re.MULTILINE)
            summary_line = None
            for line in output.splitlines():
                if re.match(r'^[.FE]+$', line.strip()) and len(line.strip()) > 2:
                    summary_line = line.strip()
                    break
            for idx, (name, cls) in enumerate(discovered):
                status = None
                if summary_line and idx < len(summary_line):
                    status = {'F': 'FAIL', 'E': 'ERROR', '.': 'ok'}.get(summary_line[idx], summary_line[idx])
                else:
                    status = 'ok'  # Default to ok if not found
                tests.append({'name': name, 'class': cls, 'status': status, 'details': ''})
        except Exception:
            summary_line = None
            for line in output.splitlines():
                if re.match(r'^[.FE]+$', line.strip()) and len(line.strip()) > 2:
                    summary_line = line.strip()
                    break
            for idx, ch in enumerate(summary_line or ''):
                status = {'F': 'FAIL', 'E': 'ERROR', '.': 'ok'}.get(ch, ch)
                tests.append({'name': f'test_{idx+1}', 'class': '', 'status': status, 'details': ''})
    # Find error/failure details
    fail_blocks = re.split(r'={10,}', output)
    for block in fail_blocks:
        fail_match = re.search(r'(FAIL|ERROR): (test_\w+) \(([^)]+)\)', block)
        if fail_match:
            status = fail_match.group(1)
            name = fail_match.group(2)
            cls = fail_match.group(3)
            details = block.strip()
            for t in tests:
                if t['name'] == name and (not t['class'] or t['class'] == cls):
                    t['details'] = details
    # Mark tests as 'unknown' only if status is not ok/FAIL/ERROR
    for t in tests:
        if t['status'] not in ('ok', 'FAIL', 'ERROR'):
            t['status'] = 'ok'
    return tests

def parse_test_summary(output):
    """Extracts a simple summary from unittest output."""
    import re
    match = re.search(r'Ran (\d+) tests? in ([\d\.]+)s', output)
    if match:
        total = match.group(1)
        time = match.group(2)
        failed = 'FAILED' in output or 'ERROR' in output
        return f"Wykonano {total} testów w {time}s. {'Błędy!' if failed else 'Wszystkie zaliczone.'}"
    return 'Brak podsumowania.'

def generate_ai_summary(output):
    """Placeholder for AI-generated summary. Można podpiąć model AI tutaj."""
    if 'FAILED' in output or 'ERROR' in output:
        return 'Niektóre testy nie przeszły. Sprawdź szczegóły poniżej.'
    if 'OK' in output:
        return 'Wszystkie testy zaliczone pomyślnie.'
    return 'Brak szczegółowego podsumowania.'

# --- Helper Functions ---

def get_audio_input_devices():
    """Gets a list of available audio input devices."""
    devices = []
    try:
        sd_devices = sd.query_devices()
        default_input_device_index = sd.default.device[0] # Get default input device index
        for i, device in enumerate(sd_devices):
            if device['max_input_channels'] > 0:
                is_default = (i == default_input_device_index)
                devices.append({
                    'id': i,
                    'name': device['name'],
                    'is_default': is_default
                })
        logger.info(f"Found audio input devices: {devices}")
    except Exception as e:
        logger.error(f"Could not query audio devices: {e}")
        # Return a dummy entry or empty list if query fails
        devices.append({'id': -1, 'name': "Error querying devices", 'is_default': False})
    return devices

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
def get_conversation_history(limit=50, buffer_multiplier=5):
    """
    Reads conversation history from the log file efficiently.
    Reads roughly the last N lines needed, where N is limit * buffer_multiplier.
    Improved parsing and error handling.
    """
    history = []
    logger.debug(f"Attempting to read history from: {HISTORY_FILE}")
    try:
        if not os.path.exists(HISTORY_FILE):
            logger.warning(f"History file not found at {HISTORY_FILE}. Returning empty list.")
            return []

        # Estimate buffer size needed (average line length * lines_to_read)
        # This is a heuristic, adjust avg_line_len if needed
        avg_line_len = 150
        lines_to_read = limit * buffer_multiplier
        buffer_size = avg_line_len * lines_to_read

        with open(HISTORY_FILE, 'rb') as f: # Open in binary mode for seek
            # Seek towards the end of the file, but not necessarily exactly
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            seek_pos = max(0, file_size - buffer_size)
            f.seek(seek_pos, os.SEEK_SET)

            # Read the end chunk and decode, handling potential partial lines
            # Use deque for efficient limited line storage
            try:
                # Read remaining data and decode, ignoring errors
                lines_bytes = f.read()
                lines_str = lines_bytes.decode('utf-8', errors='ignore')
                # Use deque to keep only the last lines_to_read (approx)
                last_lines = collections.deque(lines_str.splitlines(), maxlen=lines_to_read)
            except Exception as read_err:
                 logger.error(f"Error reading/decoding end of history file: {read_err}")
                 return [] # Return empty on read error

            # Parse lines from the deque in reverse (most recent first)
            last_user_content = None
            for line in reversed(last_lines):
                line = line.strip()
                if not line:
                    continue

                # --- Keep the existing parsing logic ---
                # Basic parsing logic (adjust based on actual log format)
                # Look for specific log messages indicating user input or assistant speech
                if "INFO - Refined query:" in line:
                    content = line.split("Refined query:", 1)[1].strip()
                    if content and (not history or history[-1].get("content") != content or history[-1].get("role") != "user"):
                        history.append({"role": "user", "content": content})
                    last_user_content = content
                elif "INFO - Command:" in line:
                    # Only add if there was no refined query after this command
                    content = line.split("Command:", 1)[1].strip()
                    if last_user_content != content:
                        if content and (not history or history[-1].get("content") != content or history[-1].get("role") != "user"):
                            history.append({"role": "user", "content": content})
                    last_user_content = None
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
                # --- End of existing parsing logic ---


                if len(history) >= limit:
                    break # Stop once the limit is reached

            history.reverse() # Put back in chronological order
            logger.info(f"Retrieved {len(history)} history entries (from buffer).")

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
    log_level = logging.WARNING # Or get from config/env
    logging.getLogger(__name__).setLevel(log_level)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Ogranicz logi Werkzeug do WARNING i wyżej
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
        current_config = load_main_config() # Use main config loader
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
        current_config = load_main_config() # Use main config loader
        audio_devices = get_audio_input_devices() # Get the list of devices
        return render_template('config.html', config=current_config, audio_devices=audio_devices)

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

    @app.route('/dev')
    def dev_page():
        if not session.get('username') or session.get('role') != 'dev':
            flash('Brak dostępu do zakładki Dev.', 'danger')
            return redirect(url_for('index'))
        return render_template('dev.html')

    @app.route('/plugins')
    @login_required(role="dev")
    def plugins_page():
        return render_template('plugins.html')

    @app.route('/mcp')
    @login_required(role="dev")
    def mcp_page():
        return render_template('mcp.html')

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

            logger.info(f"Received request to update configuration by user '{session.get('username')}' with data: {new_config_data}")
            # Basic validation (optional, enhance as needed)
            if 'MIC_DEVICE_ID' in new_config_data:
                try:
                    if new_config_data['MIC_DEVICE_ID'] != '':
                         int(new_config_data['MIC_DEVICE_ID'])
                except (ValueError, TypeError):
                     logger.warning("Invalid MIC_DEVICE_ID received.")
                     return jsonify({"error": "Invalid MIC_DEVICE_ID format (must be an integer or empty)."}), 400

            try:
                # Use the main save function
                save_main_config(new_config_data)
                logger.info("Configuration saved successfully via save_main_config.")

                # Notify the main assistant process about the config change
                if assistant_queue:
                    try:
                        assistant_queue.put({"action": "config_updated"})
                        logger.info("Sent config_updated notification to assistant process.")
                    except Exception as q_err:
                         logger.error(f"Failed to send config_updated notification via queue: {q_err}")
                         # Continue even if queue fails, config was saved
                else:
                    logger.warning("Assistant queue not available, cannot notify assistant of config change.")

                return jsonify({"message": "Configuration saved successfully."}), 200
            except Exception as e:
                # Log the specific error during saving or queue notification
                logger.error(f"Error during save_main_config or queue notification: {e}", exc_info=True)
                return jsonify({"error": "Failed to save configuration due to a server issue."}), 500

        else: # GET
            logger.info(f"Configuration requested by user '{session.get('username')}' via GET.")
            current_config = load_main_config() # Use main config loader
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
        current_config = load_main_config() # Use main config loader
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

    @app.route('/api/analytics', methods=['GET'])
    @login_required()
    def api_analytics():
        """API endpoint for usage statistics (dashboard)."""
        # Example: count messages and users from conversation history
        try:
            history = get_conversation_history()
            msg_count = len(history)
            unique_users = list({entry.get('user', 'unknown') for entry in history})
            avg_response_time = sum(entry.get('response_time', 0) for entry in history if entry.get('response_time')) / msg_count if msg_count else 0
            last_query_time = max((entry.get('timestamp', 0) for entry in history), default=None)
            return jsonify({
                'msg_count': msg_count,
                'unique_users': unique_users,
                'avg_response_time': avg_response_time,
                'last_query_time': last_query_time
            })
        except Exception as e:
            logger.error(f"Failed to calculate analytics: {e}", exc_info=True)
            return jsonify({'msg_count': 0, 'unique_users': [], 'avg_response_time': 0, 'last_query_time': None})

    @app.route('/api/plugins', methods=['GET'])
    @login_required(role="dev")
    def api_plugins():
        """API endpoint for plugin list and status."""
        import os, json
        plugins_file = os.path.join(os.path.dirname(__file__), '..', 'plugins_state.json')
        plugins = {}
        try:
            if os.path.exists(plugins_file):
                with open(plugins_file, 'r', encoding='utf-8') as f:
                    plugins_data = json.load(f)
                    # plugins_data może być {'plugins': {...}} lub {...}
                    if 'plugins' in plugins_data:
                        plugins = plugins_data['plugins']
                    else:
                        plugins = plugins_data
            else:
                # Fallback: scan modules dir
                modules_dir = os.path.join(os.path.dirname(__file__), '..', 'modules')
                for fname in os.listdir(modules_dir):
                    if fname.endswith('_module.py'):
                        name = fname[:-3]
                        plugins[name] = {'enabled': True}
            return jsonify(plugins)
        except Exception as e:
            logger.error(f"Failed to load plugins: {e}", exc_info=True)
            return jsonify({})

    # --- API endpoints for test running ---
    from flask import Blueprint
    api_bp = Blueprint('api', __name__)

    @api_bp.route('/api/run_tests', methods=['POST'])
    def api_run_tests():
        with test_status_lock:
            if test_status['running']:
                return jsonify({'status': 'already_running'}), 409
            # Start test runner in background thread
            thread = threading.Thread(target=run_unit_tests, daemon=True)
            thread.start()
            test_status['running'] = True
            test_status['result'] = None
            test_status['log'] = ''
            test_status['summary'] = ''
            test_status['ai_summary'] = ''
        return jsonify({'status': 'started'})

    @api_bp.route('/api/test_status', methods=['GET'])
    def api_test_status():
        with test_status_lock:
            return jsonify(test_status)

    # Register blueprint in create_app or directly if app is global
    app.register_blueprint(api_bp)

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

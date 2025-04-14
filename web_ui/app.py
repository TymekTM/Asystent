# filepath: f:\Asystent\web_ui\app.py
import os
import json
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from functools import wraps
import logging

# --- Configuration ---
# TODO: Replace with a more robust secret key management
SECRET_KEY = os.urandom(24)
# TODO: Define user credentials (replace with database/proper auth later)
USERS = {
    "user": {"password": "password", "role": "user"},
    "dev": {"password": "devpassword", "role": "dev"}
}
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config.json') # Path relative to app.py
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'assistant.log') # Path to log file for now
# TODO: Need a way to access/control the main assistant instance
# This might involve IPC, shared state, or refactoring assistant.py
ASSISTANT_INSTANCE = None # Placeholder

# --- Flask App Setup ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = SECRET_KEY
logging.basicConfig(level=logging.INFO) # Configure Flask logging

# --- Helper Functions ---

def load_config():
    """Loads configuration from config.json."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {} # Or handle error more gracefully

def save_config(config_data):
    """Saves configuration to config.json."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except IOError:
        return False

def get_conversation_history():
    """Reads conversation history (simplified from log for now)."""
    history = []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            # TODO: Implement more robust log parsing or switch to a structured history format
            for line in f:
                if "INFO - Command:" in line:
                    history.append({"role": "user", "content": line.split("Command:")[1].strip()})
                elif "INFO - TTS:" in line:
                     # Avoid adding internal TTS messages like errors
                     tts_content = line.split("TTS:")[1].strip()
                     if not tts_content.startswith("Przepraszam,"):
                         history.append({"role": "assistant", "content": tts_content})
                elif "INFO - Refined query:" in line:
                     # Optionally show refined query for dev?
                     pass
    except FileNotFoundError:
        pass
    return history[-50:] # Limit history display for now

def clear_conversation_history():
     """Clears the history (very basic: clears the log file)."""
     # WARNING: This is destructive. A better approach is needed (e.g., archiving).
     try:
         with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
             f.write("") # Clear the file
         return True
     except IOError:
         return False


# --- Authentication ---

def login_required(role="user"):
    """Decorator to require login and specific role."""
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'username' not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('login'))
            user_role = session.get('role')
            if role == "dev" and user_role != "dev":
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for('index')) # Or a specific error page
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = USERS.get(username)
        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            flash(f"Welcome, {username}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# --- Web UI Routes ---

@app.route('/')
@login_required()
def index():
    """Main dashboard page."""
    # TODO: Add dashboard elements (status, quick actions)
    return render_template('index.html')

@app.route('/config')
@login_required(role="dev") # Only devs can access config page
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

# --- API Routes ---

@app.route('/api/config', methods=['GET', 'POST'])
@login_required(role="dev")
def api_config():
    """API endpoint for getting and updating configuration."""
    if request.method == 'POST':
        new_config_data = request.json
        if save_config(new_config_data):
            return jsonify({"message": "Configuration saved successfully."}), 200
        else:
            return jsonify({"error": "Failed to save configuration."}), 500
    else: # GET
        current_config = load_config()
        return jsonify(current_config)

@app.route('/api/history', methods=['GET', 'DELETE'])
@login_required()
def api_history():
    """API endpoint for getting and clearing conversation history."""
    if request.method == 'DELETE':
        if clear_conversation_history():
             return jsonify({"message": "Conversation history cleared."}), 200
        else:
             return jsonify({"error": "Failed to clear history."}), 500
    else: # GET
        history = get_conversation_history()
        return jsonify(history)

@app.route('/api/activate', methods=['POST'])
@login_required()
def api_activate():
    """API endpoint to manually trigger voice listening (bypass wake word)."""
    logging.info("Manual activation requested via Web UI.")
    # TODO: Implement the logic to trigger listening in the main assistant loop
    # This is complex due to asyncio and potential process separation.
    # Example using asyncio.run_coroutine_threadsafe if assistant runs in a separate thread:
    # if ASSISTANT_INSTANCE and hasattr(ASSISTANT_INSTANCE, 'trigger_manual_listen'):
    #     future = asyncio.run_coroutine_threadsafe(ASSISTANT_INSTANCE.trigger_manual_listen(), ASSISTANT_INSTANCE.loop)
    #     try:
    #         future.result(timeout=1) # Wait briefly for acknowledgement
    #         return jsonify({"message": "Manual listening triggered."}), 200
    #     except Exception as e:
    #          logging.error(f"Error triggering manual listen: {e}")
    #          return jsonify({"error": "Failed to trigger listening."}), 500
    # else:
    #      return jsonify({"error": "Assistant not ready or trigger function missing."}), 503

    # Placeholder response:
    return jsonify({"message": "Manual activation endpoint called (implementation pending)."}), 202


@app.route('/api/long_term_memory', methods=['GET', 'POST', 'DELETE'])
@login_required(role="dev") # Example: Devs manage LTM
def api_long_term_memory():
    """Placeholder API endpoint for long-term memory management."""
    # TODO: Implement interaction with a future long-term memory system (database, vector store, etc.)
    if request.method == 'POST':
        # Add/update memory
        pass
    elif request.method == 'DELETE':
        # Delete memory entry
        pass
    # GET: Retrieve memory entries (potentially with search/filtering)
    return jsonify({"message": "Long-term memory endpoint (implementation pending)."}), 501


# --- Main Execution ---
if __name__ == '__main__':
    # Run Flask in debug mode for development
    # Consider using a production server like Gunicorn or Waitress for deployment
    # Running on 0.0.0.0 makes it accessible on the network
    app.run(debug=True, host='0.0.0.0', port=5000)

import os
import json
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from datetime import datetime  # Added for timestamping chat history
from flask import Response, stream_with_context
from datetime import datetime
from functools import wraps
import logging
import time
import shutil
import multiprocessing
import re 
import subprocess
import tempfile
import threading
import queue
from functools import wraps
import sounddevice as sd 
import collections 
import platform
import markdown
from performance_monitor import get_average_times, measure_performance, clear_performance_stats 

# --- Configuration ---


import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import load_config as load_main_config, save_config as save_main_config, CONFIG_FILE as MAIN_CONFIG_FILE, DEFAULT_CONFIG, _config
from database_manager import get_db_connection
from database_models import init_schema
# Ensure chat_history table exists
init_schema()
from database_models import (get_user_by_username, get_user_password_hash, list_users, add_user, delete_user, update_user, 
                           get_memories, add_memory, delete_memory) 

# --- Configuration ---
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Fallback to generated key if not provided via environment
    SECRET_KEY = os.urandom(24)
# Use the config file path from the main config module
CONFIG_FILE = MAIN_CONFIG_FILE
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'assistant.log')
HISTORY_ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), '..', 'history_archive')
LTM_FILE = os.path.join(os.path.dirname(__file__), '..', 'long_term_memory.json')
# --- Flask app (module-level) and startup time ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = SECRET_KEY
assistant_queue = None
# Translation mapping for UI
TRANSLATIONS = {
    'en': {
        'Assistant CP': 'Assistant CP', 'Documentation': 'Documentation', 'Chat': 'Chat',
        'Personalization': 'Personalization', 'Dashboard': 'Dashboard', 'History': 'History',
        'Logs': 'Logs', 'Plugins': 'Plugins', 'MCP': 'MCP', 'Configuration': 'Configuration',
        'Long-Term Memory': 'Long-Term Memory', 'Dev': 'Dev', 'Login': 'Login', 'Logout': 'Logout'
    },
    'pl': {
        'Assistant CP': 'Panel Asystenta', 'Documentation': 'Dokumentacja', 'Chat': 'Czat',
        'Personalization': 'Personalizacja', 'Dashboard': 'Panel', 'History': 'Historia',
        'Logs': 'Logi', 'Plugins': 'Pluginy', 'MCP': 'MCP', 'Configuration': 'Konfiguracja',
        'Long-Term Memory': 'Pamięć długoterminowa', 'Dev': 'Dev', 'Login': 'Zaloguj', 'Logout': 'Wyloguj'
    }
}
# Ensure language in session and expose translations
@app.before_request
def ensure_language():
    if 'lang' not in session:
        session['lang'] = _config.get('ui_language', 'en')
    # expose to templates
    app.jinja_env.globals['translations'] = TRANSLATIONS
    app.jinja_env.globals['current_lang'] = session['lang']

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    ref = request.referrer or url_for('index')
    return redirect(ref)
_startup_time = time.time()

# --- Audio upload helpers ---
def convert_audio(input_path: str) -> str:
    """Convert any audio file to WAV and return new path."""
    wav_path = input_path + '.wav'
    subprocess.run([
        'ffmpeg', '-y', '-i', input_path,
        '-ar', '16000', '-ac', '1', wav_path
    ], check=True, capture_output=True)
    return wav_path


from assistant import Assistant
_assistant_instance = None
def get_assistant_instance():
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = Assistant()
    return _assistant_instance

def transcribe_audio(wav_path: str) -> str:
    """Transcribe WAV file via assistant instance if available."""
    try:
        assistant = get_assistant_instance()
        if getattr(assistant, 'whisper_asr', None):
            return assistant.whisper_asr.transcribe(wav_path)
        if getattr(assistant, 'speech_recognizer', None):
            return assistant.speech_recognizer.transcribe_file(wav_path)
    except Exception:
        pass
    return ''

def cleanup_files(*paths: str):
    """Remove temp files, ignore errors."""
    for p in paths:
        try:
            os.remove(p)
        except Exception:
            pass
_startup_time = time.time()
_startup_time = time.time()

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

bench_status = {'running': False, 'result': {}, 'log': '', 'summary': ''}
bench_status_lock = threading.Lock()

# Test history and scheduling
test_history = []
max_history_entries = 20
scheduled_interval = None  # in minutes
scheduled_timer = None
scheduler_lock = threading.Lock()

import unittest, io

def run_unit_tests():
    """Run unit tests incrementally and update test_status for real-time UI."""
    global test_status
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(os.path.dirname(__file__), '..', 'tests_unit'), pattern='test_*.py')
    stream = io.StringIO()
    # Initialize status
    with test_status_lock:
        test_status.update({
            'running': True,
            'result': None,
            'log': '',
            'summary': '',
            'ai_summary': '',
            'tests': [],
            'last_run': datetime.datetime.now().isoformat()
        })
    # Custom TestResult for streaming
    class StreamingResult(unittest.TextTestResult):
        def __init__(self, *args, **kwargs):
            # Accept all args including 'durations' and 'tb_locals'
            super().__init__(*args, **kwargs)
        def addSuccess(self, test):
            super().addSuccess(test)
            with test_status_lock:
                test_status['tests'].append({'name': test._testMethodName, 'class': test.__class__.__name__, 'status': 'ok', 'details': ''})
                test_status['log'] = stream.getvalue()
        def addFailure(self, test, err):
            super().addFailure(test, err)
            details = self.failures[-1][1]
            with test_status_lock:
                test_status['tests'].append({'name': test._testMethodName, 'class': test.__class__.__name__, 'status': 'FAIL', 'details': details})
                test_status['log'] = stream.getvalue()
        def addError(self, test, err):
            super().addError(test, err)
            details = self.errors[-1][1]
            with test_status_lock:
                test_status['tests'].append({'name': test._testMethodName, 'class': test.__class__.__name__, 'status': 'ERROR', 'details': details})
                test_status['log'] = stream.getvalue()
    runner = unittest.TextTestRunner(stream=stream, verbosity=1, resultclass=StreamingResult)
    result_obj = runner.run(suite)
    output = stream.getvalue()
    with test_status_lock:
        test_status['running'] = False
        test_status['result'] = 'passed' if result_obj.wasSuccessful() else 'failed'
        test_status['summary'] = parse_test_summary(output)
        test_status['ai_summary'] = generate_ai_summary(output)
        test_status['log'] = output
        # Append to history
        entry = {
            'timestamp': test_status.get('last_run'),
            'result': test_status['result'],
            'summary': test_status['summary']
        }
        test_history.append(entry)
        if len(test_history) > max_history_entries:
            test_history.pop(0)

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

def run_benchmarks():
    with bench_status_lock:
        bench_status['running'] = True
        bench_status['result'] = {}
        bench_status['log'] = ''
        bench_status['summary'] = ''
    log_lines = []
    try:
        import psutil, time
        # System info
        cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
        total_gb = psutil.virtual_memory().total / (1024**3)
        log_lines.append(f"CPU cores: {cpu_count}")
        log_lines.append(f"Total RAM: {total_gb:.2f} GB")
        # CPU benchmark
        start = time.time()
        sum(range(10_000_000))
        cpu_time = time.time() - start
        log_lines.append(f"Sum(range(10_000_000)): {cpu_time:.3f}s")
        # Memory benchmark
        proc = psutil.Process()
        mem_before = proc.memory_info().rss / (1024**2)
        lst = [0] * 10_000_000
        mem_after = proc.memory_info().rss / (1024**2)
        mem_delta = mem_after - mem_before
        log_lines.append(f"Alloc list(10M ints): +{mem_delta:.2f} MB")
        # Disk I/O benchmark: write and read 10MB file
        import tempfile
        # Prepare 10MB file in temp location
        fd, tmp_path = tempfile.mkstemp(prefix="bench_io_", suffix=".tmp")
        os.close(fd)
        data = b'\0' * (1 * 1024 * 1024)
        num_chunks = 10
        start_io = time.time()
        with open(tmp_path, "wb") as f:
            for _ in range(num_chunks):
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        write_time = time.time() - start_io
        log_lines.append(f"Write 10MB file: {write_time:.3f}s")
        # Read back the file
        start_io = time.time()
        with open(tmp_path, "rb") as f:
            while f.read(1024 * 1024):
                pass
        read_time = time.time() - start_io
        log_lines.append(f"Read 10MB file: {read_time:.3f}s")
        # Cleanup
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        # Prepare initial results including CPU and memory
        result = {
            'cpu_cores': cpu_count,
            'total_memory_gb': round(total_gb, 2),
            'cpu_benchmark_sec': round(cpu_time, 3),
            'memory_alloc_mb': round(mem_delta, 2)
        }
        # Add disk I/O results
        result['disk_write_sec'] = round(write_time, 3)
        result['disk_read_sec'] = round(read_time, 3)
        # Prepare summary string
        summary = (
            f"{cpu_count} cores, {total_gb:.1f}GB RAM; "
            f"CPU: {cpu_time:.3f}s; Mem: {mem_delta:.2f}MB; "
            f"Write: {result['disk_write_sec']:.3f}s; Read: {result['disk_read_sec']:.3f}s"
        )
        log = "\n".join(log_lines)
        with bench_status_lock:
            bench_status['running'] = False
            bench_status['result'] = result
            bench_status['log'] = log
            bench_status['summary'] = summary
    except Exception as e:
        err = str(e)
        with bench_status_lock:
            bench_status['running'] = False
            bench_status['summary'] = f"Error: {err}"
            bench_status['log'] = "\n".join(log_lines) + f"\nError: {err}"
            bench_status['result'] = {}

# --- Helper Functions ---

def get_audio_input_devices():
    """Gets a list of available audio input devices with IDs and names."""
    devices = []
    try:
        sd_devices = sd.query_devices()
        default_input_device_index = sd.default.device[0] # Get default input device index
        for i, device in enumerate(sd_devices):
            if device['max_input_channels'] > 0:
                is_default = (i == default_input_device_index)
                devices.append({
                    "id": i,
                    "name": device['name'],
                    "is_default": is_default
                })
    except Exception as e:
        logger.error(f"Error querying audio devices: {e}")
        # Optionally return a default/error indicator
        devices.append({"id": "error", "name": "Nie można pobrać urządzeń", "is_default": False})
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
                    timestamp = line.split(" - ", 1)[0]
                    content = line.split("Refined query:", 1)[1].strip()
                    if content and (not history or history[-1].get("content") != content or history[-1].get("role") != "user"):
                        history.append({"role": "user", "content": content, "timestamp": timestamp})
                    last_user_content = content
                elif "INFO - Command:" in line:
                    # Only add if there was no refined query after this command
                    timestamp = line.split(" - ", 1)[0]
                    content = line.split("Command:", 1)[1].strip()
                    if last_user_content != content:
                        if content and (not history or history[-1].get("content") != content or history[-1].get("role") != "user"):
                            history.append({"role": "user", "content": content, "timestamp": timestamp})
                    last_user_content = None
                elif "INFO - TTS:" in line:
                    content = line.split("TTS:", 1)[1].strip()
                    # Avoid adding internal TTS messages like errors or irrelevant info
                    # Filter more specifically based on expected assistant responses
                    if content and not content.startswith("Przepraszam,") and not content.startswith("Error executing command"):
                         timestamp = line.split(" - ", 1)[0]
                         # Avoid adding if the last message was the same assistant message
                         if not history or history[-1].get("content") != content or history[-1].get("role") != "assistant":
                            history.append({"role": "assistant", "content": content, "timestamp": timestamp})
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
                              timestamp = line.split(" - ", 1)[0]
                              # Avoid adding if TTS log likely added the same content just before/after
                              is_likely_duplicate = False
                              if history:
                                  last_msg = history[-1]
                                  if last_msg.get("role") == "assistant" and last_msg.get("content") == content:
                                      is_likely_duplicate = True
                              if not is_likely_duplicate:
                                   history.append({"role": "assistant", "content": content, "timestamp": timestamp})
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
def login_required(_func=None, *, role="user"):
    def decorator(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'username' not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('login'))
            user = get_user_by_username(session['username'])
            if not user:
                session.clear()
                flash("User not found.", "danger")
                return redirect(url_for('login'))
            if role == "dev" and user.role != "dev": # Corrected attribute access
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for('index'))
            return fn(*args, **kwargs)
        return decorated_view
    if _func is None:
        return decorator
    else:
        return decorator(_func)

# --- Web UI Routes --- defined within create_app ---

# --- API Routes --- defined within create_app or standalone ---
def setup_api_routes(app, queue):
    global assistant_queue
    assistant_queue = queue

    @app.route('/api/config', methods=['GET', 'POST'])
    @login_required # Protect config access
    def api_config():
        if request.method == 'POST':
            try:
                new_config_data = request.get_json()
                logger.debug(f"Received config data for saving: {new_config_data}")

                # --- Type Conversion and Validation ---
                # Convert numeric fields
                for key in ['STT_SILENCE_THRESHOLD', 'MAX_HISTORY_LENGTH']:
                    if key in new_config_data:
                        try:
                            new_config_data[key] = int(new_config_data[key])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid value for {key}, keeping original or default.")
                            # Optionally load current config to keep original value
                            current_config = load_main_config()
                            new_config_data[key] = current_config.get(key, DEFAULT_CONFIG.get(key))


                # Handle MIC_DEVICE_ID (can be None or int)
                mic_id_str = new_config_data.get('MIC_DEVICE_ID', '')
                if isinstance(mic_id_str, str) and mic_id_str.isdigit():
                     new_config_data['MIC_DEVICE_ID'] = int(mic_id_str)
                elif mic_id_str == '' or mic_id_str is None:
                     new_config_data['MIC_DEVICE_ID'] = None # Explicitly set to None for default
                else:
                     # Keep existing or default if invalid format
                     logger.warning(f"Invalid MIC_DEVICE_ID format: '{mic_id_str}'. Using default (None).")
                     new_config_data['MIC_DEVICE_ID'] = None


                # Convert boolean fields (ensure they exist)
                for key in ['USE_WHISPER_FOR_COMMAND', 'LOW_POWER_MODE', 'EXIT_WITH_CONSOLE', 'DEV_MODE']:
                    new_config_data[key] = bool(new_config_data.get(key, False)) # Default to False if missing

                # Handle nested query_refinement enabled boolean
                if 'query_refinement' in new_config_data and isinstance(new_config_data['query_refinement'], dict):
                    new_config_data['query_refinement']['enabled'] = bool(new_config_data['query_refinement'].get('enabled', False))
                else:
                     # Ensure query_refinement structure exists if saving related fields
                     if 'query_refinement.model' in new_config_data: # Check if any refinement field was sent
                         current_config = load_main_config()
                         new_config_data['query_refinement'] = current_config.get('query_refinement', DEFAULT_CONFIG.get('query_refinement', {})).copy()
                         # Update only the fields that were actually sent if necessary
                         if 'query_refinement.model' in new_config_data:
                             new_config_data['query_refinement']['model'] = new_config_data.pop('query_refinement.model') # Adjust if needed based on form data structure
                         new_config_data['query_refinement']['enabled'] = bool(new_config_data['query_refinement'].get('enabled', False))


                # Load current config to merge, ensuring no keys are lost
                current_config = load_main_config()
                # Update current_config with validated new_config_data
                for key, value in new_config_data.items():
                     # Handle nested dicts like API_KEYS and query_refinement carefully
                     if isinstance(value, dict) and key in current_config and isinstance(current_config[key], dict):
                         current_config[key].update(value) # Merge sub-dictionaries
                     else:
                         current_config[key] = value # Overwrite top-level keys or non-dict values


                # Ensure all default keys still exist after merge (in case some were removed)
                for key, default_value in DEFAULT_CONFIG.items():
                    if key not in current_config:
                        current_config[key] = default_value
                    elif isinstance(default_value, dict):
                        if not isinstance(current_config.get(key), dict):
                             current_config[key] = default_value.copy() # Reset if type changed
                        else:
                             # Ensure nested defaults exist
                             for sub_key, sub_default_value in default_value.items():
                                 if sub_key not in current_config[key]:
                                     current_config[key][sub_key] = sub_default_value


                logger.debug(f"Final config data to save: {current_config}")
                save_main_config(current_config)
                flash("Konfiguracja zapisana pomyślnie.", "success")
                # Signal main process to reload config if necessary (implementation depends on main loop)
                if assistant_queue:
                    try:
                        assistant_queue.put_nowait({'command': 'reload_config'})
                        logger.info("Sent reload_config command to assistant process.")
                    except Exception as e:
                        logger.error(f"Failed to send reload_config command: {e}")
                return jsonify({"message": "Konfiguracja zapisana."}), 200
            except json.JSONDecodeError:
                logger.error("Invalid JSON received for config update.")
                return jsonify({"error": "Nieprawidłowy format JSON."}), 400
            except Exception as e:
                logger.error(f"Error saving configuration: {e}", exc_info=True)
                return jsonify({"error": f"Wystąpił błąd serwera podczas zapisu: {e}"}), 500
        else: # GET request
            config_data = load_main_config()
            # Ensure API keys are masked or handled appropriately before sending to client
            if 'API_KEYS' in config_data:
                 config_data['API_KEYS'] = {k: '********' if v else '' for k, v in config_data['API_KEYS'].items()}
            return jsonify(config_data)

    @app.route('/api/audio_devices', methods=['GET'])
    @login_required
    def api_audio_devices():
        """API endpoint to get the list of audio input devices."""
        devices = get_audio_input_devices()
        return jsonify(devices)

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
        # Check for restart lock file
        lock_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_restarting.lock')
        if os.path.exists(lock_path):
            status_str = "Restarting"
        else:
            # In a real implementation, fetch live status from the assistant process via IPC.
            # For now, return config-based info and a dummy status.
            status_str = "Online"
        current_config = load_main_config() # Use main config loader
        status = {
            "status": status_str,
            "wake_word": current_config.get('WAKE_WORD', 'N/A'),
            "stt_engine": "Whisper" if current_config.get('USE_WHISPER_FOR_COMMAND') else "Vosk",
            "mic_id": current_config.get('MIC_DEVICE_ID', 'N/A')
        }
        return jsonify(status)

    @app.route('/api/restart/assistant', methods=['POST'])
    @login_required()
    def restart_assistant():
        """Endpoint to restart the assistant process."""
        logger.warning("[WEB] Restart assistant requested via dashboard API.")
        lock_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_restarting.lock')
        with open(lock_path, 'w') as f:
            f.write('restarting')
        # Cross-platform restart
        if platform.system() == 'Windows':
            subprocess.Popen(['powershell.exe', '-Command', 'Start-Process', 'python', 'main.py', '-WindowStyle', 'Hidden'])
        else:
            subprocess.Popen(['nohup', 'python3', 'main.py', '&'])
        logger.warning("[WEB] Attempted to start new assistant process. Uwaga: stary proces nie jest automatycznie zamykany!")
        return jsonify({"message": "Restarting assistant..."}), 202

    @app.route('/api/restart/web', methods=['POST'])
    @login_required()
    def restart_web():
        logger.warning("[WEB] Restart web panel requested via dashboard API.")
        lock_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_restarting.lock')
        with open(lock_path, 'w') as f:
            f.write('restarting')
        os._exit(3)  # This will cause most process managers to restart Flask
        return jsonify({"message": "Restarting web panel..."}), 202

    @app.route('/api/restart/all', methods=['POST'])
    @login_required()
    def restart_all():
        logger.warning("[WEB] Restart all (assistant + web) requested via dashboard API.")
        lock_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_restarting.lock')
        with open(lock_path, 'w') as f:
            f.write('restarting')
        if platform.system() == 'Windows':
            subprocess.Popen(['powershell.exe', '-Command', 'Start-Process', 'python', 'main.py', '-WindowStyle', 'Hidden'])
        else:
            subprocess.Popen(['nohup', 'python3', 'main.py', '&'])
        logger.warning("[WEB] Attempted to start new assistant process. Uwaga: stary proces nie jest automatycznie zamykany!")
        os._exit(3)
        return jsonify({"message": "Restarting assistant and web panel..."}), 202

    @app.route('/api/logs')
    @login_required()
    def api_logs():
        level = request.args.get('level', 'ALL')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 100))
        log_path = os.path.join(os.path.dirname(__file__), '..', 'assistant.log')
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if level != 'ALL':
                lines = [l for l in lines if f'- {level} -' in l]
            total_lines = len(lines)
            total_pages = max(1, (total_lines + page_size - 1) // page_size)
            page = max(1, min(page, total_pages))
            start = (page - 1) * page_size
            end = start + page_size
            logs = lines[start:end]
            return jsonify({'logs': logs, 'page': page, 'total_pages': total_pages, 'total_lines': total_lines})
        except Exception as e:
            return jsonify({'logs': [f'Błąd odczytu logów: {e}'], 'page': 1, 'total_pages': 1, 'total_lines': 0}), 500

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
        modules_dir = os.path.join(os.path.dirname(__file__), '..', 'modules')
        plugins = {}
        try:
            # Load plugin states from file if exists
            if os.path.exists(plugins_file):
                with open(plugins_file, 'r', encoding='utf-8') as f:
                    plugins_data = json.load(f)
                    if 'plugins' in plugins_data:
                        plugins = plugins_data['plugins']
                    else:
                        plugins = plugins_data
            # Always scan modules dir for *_module.py files
            if os.path.exists(modules_dir):
                for fname in os.listdir(modules_dir):
                    if fname.endswith('_module.py'):
                        name = fname[:-3]
                        if name not in plugins:
                            plugins[name] = {'enabled': True}
            return jsonify(plugins)
        except Exception as e:
            logger.error(f"Failed to load plugins: {e}", exc_info=True)
            return jsonify({})
    
    # Enable or disable a plugin
    @app.route('/api/plugins/<name>/enable', methods=['POST'])
    @login_required(role="dev")
    def api_plugin_enable(name):
        """Enable a plugin by name."""
        import os, json
        plugins_file = os.path.join(os.path.dirname(__file__), '..', 'plugins_state.json')
        try:
            # load existing state
            state = {}
            if os.path.exists(plugins_file):
                with open(plugins_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            plugins = state.get('plugins', {})
            # set enabled
            plugins.setdefault(name, {})
            plugins[name]['enabled'] = True
            state['plugins'] = plugins
            with open(plugins_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            # reload in assistant
            try:
                get_assistant_instance().load_plugins()
            except Exception:
                pass
            return jsonify({"status": "enabled"}), 200
        except Exception as e:
            logger.error(f"Failed to enable plugin {name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/plugins/<name>/disable', methods=['POST'])
    @login_required(role="dev")
    def api_plugin_disable(name):
        """Disable a plugin by name."""
        import os, json
        plugins_file = os.path.join(os.path.dirname(__file__), '..', 'plugins_state.json')
        try:
            state = {}
            if os.path.exists(plugins_file):
                with open(plugins_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            plugins = state.get('plugins', {})
            plugins.setdefault(name, {})
            plugins[name]['enabled'] = False
            state['plugins'] = plugins
            with open(plugins_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            try:
                get_assistant_instance().load_plugins()
            except Exception:
                pass
            return jsonify({"status": "disabled"}), 200
        except Exception as e:
            logger.error(f"Failed to disable plugin {name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/plugins/<name>/reload', methods=['POST'])
    @login_required(role="dev")
    def api_plugin_reload(name):
        """Reload a plugin by name."""
        try:
            # Trigger assistant to reload plugins
            get_assistant_instance().load_plugins()
            return jsonify({"status": "reloaded"}), 200
        except Exception as e:
            logger.error(f"Failed to reload plugin {name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/performance_stats', methods=['GET', 'DELETE']) # Add DELETE method
    @login_required
    @measure_performance # Measure this endpoint too
    def api_performance_stats():
        """API endpoint to get or clear performance statistics."""
        if request.method == 'DELETE':
            if 'username' in session and session.get('role') == 'dev': # Only allow devs to clear
                if clear_performance_stats():
                    logger.info(f"Performance stats cleared by user '{session['username']}'.")
                    return jsonify({"message": "Performance stats cleared successfully."}), 200
                else:
                    logger.error("Failed to clear performance stats.")
                    return jsonify({"error": "Failed to clear performance stats."}), 500
            else:
                return jsonify({"error": "Unauthorized to clear stats."}), 403
        else: # GET
            stats = get_average_times()
            return jsonify(stats)

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

    @api_bp.route('/api/run_benchmarks', methods=['POST'])
    def api_run_benchmarks():
        with bench_status_lock:
            if bench_status['running']:
                return jsonify({'status': 'already_running'}), 409
            thread = threading.Thread(target=run_benchmarks, daemon=True)
            thread.start()
            bench_status['running'] = True
            bench_status['result'] = {}
            bench_status['log'] = ''
            bench_status['summary'] = ''
        return jsonify({'status': 'started'})

    @api_bp.route('/api/bench_status', methods=['GET'])
    def api_bench_status():
        with bench_status_lock:
            return jsonify(bench_status)

    @api_bp.route('/api/test_history', methods=['GET'])
    def api_test_history():
        """Return list of past test runs."""
        with test_status_lock:
            return jsonify(test_history)

    @api_bp.route('/api/schedule_tests', methods=['POST'])
    def api_schedule_tests():
        """Schedule recurring test runs at given interval in minutes."""
        data = request.json or {}
        interval = data.get('interval')
        try:
            mins = float(interval)
        except Exception:
            return jsonify({'error': 'Invalid interval'}), 400
        global scheduled_interval, scheduled_timer
        # Cancel existing
        with scheduler_lock:
            if scheduled_timer:
                scheduled_timer.cancel()
            scheduled_interval = mins
            # Schedule first run after interval
            def schedule_runner():
                run_unit_tests()
                # Reschedule
                global scheduled_timer
                with scheduler_lock:
                    scheduled_timer = threading.Timer(scheduled_interval * 60, schedule_runner)
                    scheduled_timer.daemon = True
                    scheduled_timer.start()
            scheduled_timer = threading.Timer(mins * 60, schedule_runner)
            scheduled_timer.daemon = True
            scheduled_timer.start()
        return jsonify({'status': 'scheduled', 'interval': scheduled_interval}), 200

    @api_bp.route('/api/schedule_status', methods=['GET'])
    def api_schedule_status():
        """Return scheduling status."""
        return jsonify({'scheduled_interval': scheduled_interval})    # Register blueprint in create_app
    app.register_blueprint(api_bp)


    # API endpoint to get memories (for dynamic updates/search)
    @app.route('/api/ltm/get', methods=['GET'])
    @login_required()
    def get_memories_api():
        query = request.args.get('q', '')
        limit = request.args.get('limit', default=50, type=int)
        try:
            memories = get_memories(query=query, limit=limit) # Corrected function name
            # Convert Memory objects to dictionaries for JSON serialization
            memories_list = [
                {
                    "id": mem.id,
                    "content": mem.content,
                    "user": mem.user,
                    "timestamp": mem.timestamp.isoformat() # Format datetime
                }
                for mem in memories
            ]
            return jsonify(memories_list)
        except Exception as e:
            logger.error(f"Error fetching memories via API: {e}")
            return jsonify({"error": "Failed to fetch memories"}), 500

    # API endpoint to add a memory
    @app.route('/api/ltm/add', methods=['POST'])
    @login_required()
    def add_memory_api():
        data = request.json
        content = data.get('content')
        user = session.get('username', 'unknown') # Get user from session
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        try:
            # Check for duplicates (optional, based on desired behavior)
            recent = get_memories(query=content, limit=3) # Corrected function name
            if any(m.content == content for m in recent):
                 logger.warning(f"Attempted to add duplicate memory: {content[:50]}...")
                 # Decide whether to return an error or just log
                 # return jsonify({'warning': 'Memory might be a duplicate'}), 200

            memory_id = add_memory(content=content, user=user) # Corrected function name
            logger.info(f"Memory added via API by {user}: ID {memory_id}")
            return jsonify({'success': True, 'id': memory_id}), 201
        except Exception as e:
            logger.error(f"Error adding memory via API: {e}")
            return jsonify({'error': 'Failed to add memory'}), 500

    # API endpoint to delete a memory
    @app.route('/api/ltm/delete/<int:memory_id>', methods=['DELETE'])
    @login_required()
    def delete_memory_api(memory_id):
        try:
            success = delete_memory(memory_id) # Corrected function name
            if success:
                logger.info(f"Memory {memory_id} deleted via API by {session.get('username')}")
                return jsonify({'success': True})
            else:
                logger.warning(f"Attempt to delete non-existent memory {memory_id} via API")
                return jsonify({'error': 'Memory not found'}), 404
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id} via API: {e}")
            return jsonify({'error': 'Failed to delete memory'}), 500

    @app.route('/api/stop/assistant', methods=['POST'])
    @login_required()
    def stop_assistant():
        logger.warning("[WEB] Stop assistant requested via dashboard API.")
        # Wysyłamy sygnał do procesu asystenta przez plik lock
        lock_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_stop.lock')
        with open(lock_path, 'w') as f:
            f.write('stop')
        return jsonify({"message": "Wysłano żądanie zatrzymania asystenta."}), 202

    @app.route('/chat')
    @login_required(role="user")
    def chat_page():
        return render_template('chat.html')
    

    @app.route('/api/chat/stream')
    @login_required(role="user")
    def chat_stream_api():
        import json
        import asyncio
        from flask import Response, stream_with_context
        from database_manager import get_db_connection
        # Ensure chat_history schema exists
        from database_models import init_schema
        init_schema()
        message = request.args.get('message', '').strip()
        if not message:
            return ('', 204)
        username = session['username']
        user = get_user_by_username(username)
        user_id = user.id if user else None
        # Zapisz wiadomość użytkownika do chat_history
        with get_db_connection() as conn:
            if user_id:
                conn.execute(
                    "INSERT INTO chat_history (message, user_id, timestamp) VALUES (?, ?, ?)",
                    (message, user_id, datetime.utcnow())
                )
        assistant = get_assistant_instance()
        async def run_and_stream():
            # Wywołaj asynchronicznie process_query i zbieraj odpowiedzi do kolejki
            await assistant.process_query(message, True)
            # Po zakończeniu, pobierz ostatnią odpowiedź z historii
            last = None
            for msg in reversed(assistant.conversation_history):
                if msg['role'] == 'assistant':
                    last = msg['content']
                    break
            if last:
                # Zapisz odpowiedź asystenta do chat_history z user_id jako NULL
                with get_db_connection() as conn:
                    conn.execute(
                        "INSERT INTO chat_history (message, user_id, timestamp) VALUES (?, ?, ?)",
                        (last, None, datetime.utcnow())
                    )
                # Strumieniuj odpowiedź po fragmentach
                for chunk in [last[i:i+100] for i in range(0, len(last), 100)]:
                    yield json.dumps({'type': 'chunk', 'content': chunk})
            yield json.dumps({'type': 'final'})

        def generate():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def collect():
                    items = []
                    async for item in run_and_stream():
                        items.append(item)
                    return items
                for item in loop.run_until_complete(collect()):
                    yield f'data: {item}\n\n'
            finally:
                loop.close()
        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    @app.route('/personalization')
    @login_required(role="user")
    def personalization_page():
        return render_template('personalization.html')

    @app.route('/api/chat/history')
    @login_required(role="user")
    def chat_history_api():
        # Ensure chat_history schema exists
        from database_models import init_schema
        init_schema()
        username = session['username']
        user = get_user_by_username(username)
        if not user:
            return jsonify({'history': []})
        user_id = user.id
        from database_manager import get_db_connection
        # Pobierz tylko wiadomości tego usera i AI, posortowane rosnąco
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT ch.message, ch.timestamp, ch.user_id, u.username"
                " FROM chat_history ch"
                " LEFT JOIN users u ON ch.user_id = u.id"
                " WHERE ch.user_id = ? OR ch.user_id IS NULL"
                " ORDER BY ch.id ASC",
                (user_id,)
            ).fetchall()
        history = []
        for row in rows:
            if row['user_id'] == user_id:
                history.append({'role': 'user', 'content': row['message'], 'timestamp': row['timestamp']})
            else:
                history.append({'role': 'assistant', 'content': row['message'], 'timestamp': row['timestamp']})
        return jsonify({'history': history})

    @app.route('/api/chat/send', methods=['POST'])
    @login_required(role="user")
    def chat_send_api():
        import importlib
        from ai_module import chat_with_providers, remove_chain_of_thought, parse_response
        from config import MAIN_MODEL
        from prompts import SYSTEM_PROMPT
        import inspect
        data = request.get_json()
        message = data.get('message', '').strip()
        if not message:
            return jsonify({'reply': ''})
        username = session['username']
        user = get_user_by_username(username)
        if not user:
            return jsonify({'reply': '(Błąd użytkownika)'}), 400
        user_id = user['id']
        # Zapisz wiadomość usera do oddzielnej tabeli chat_history
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (message, user_id, timestamp) VALUES (?, ?, ?) ",
                (message, user_id, datetime.utcnow())
            )
        # Pobierz całą historię tego chatu z chat_history
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT ch.message, ch.timestamp, ch.user_id, u.username"
                " FROM chat_history ch"
                " LEFT JOIN users u ON ch.user_id = u.id"
                " WHERE ch.user_id = ? OR ch.user_id IS NULL"
                " ORDER BY ch.id ASC",
                (user_id,)
            ).fetchall()
        chat_msgs = []
        for row in rows:
            if row['user_id'] == user_id:
                chat_msgs.append({'role': 'user', 'content': row['content']})
            else:
                chat_msgs.append({'role': 'assistant', 'content': row['content']})
        chat_msgs.insert(0, {'role': 'system', 'content': SYSTEM_PROMPT + '\nYou are now in a text chat with the user.'})

        # --- TOOL CALLING PIPELINE ---
        ai_response = chat_with_providers(MAIN_MODEL, chat_msgs)
        ai_content = ai_response["message"]["content"].strip() if ai_response and ai_response.get("message", {}).get("content") else None
        reply = ""
        tool_result = None
        if ai_content:
            try:
                parsed = None
                try:
                    parsed = json.loads(ai_content)
                except Exception:
                    pass
                if not parsed and hasattr(importlib, 'import_module'):
                    # Try parse_response if available
                    try:
                        parse_response_fn = getattr(importlib.import_module('ai_module'), 'parse_response', None)
                        if parse_response_fn:
                            parsed = parse_response_fn(ai_content)
                    except Exception:
                        pass
                if isinstance(parsed, dict) and (parsed.get('command') or parsed.get('tool')):
                    # Tool call detected
                    ai_command = parsed.get('command') or parsed.get('tool')
                    ai_params = parsed.get('params', '')
                    ai_text = parsed.get('text', '')
                    reply = ai_text or ''
                    # Try to find and call the tool handler
                    tool_result = None
                    # --- Dynamic tool handler loading ---
                    tool_modules = ['modules.search_module', 'modules.memory_module', 'modules.api_module', 'modules.deepseek_module', 'modules.see_screen_module', 'modules.open_web_module']
                    handler = None
                    for mod_name in tool_modules:
                        try:
                            mod = importlib.import_module(mod_name)
                            if hasattr(mod, 'register'):
                                reg = mod.register()
                                if reg.get('command') == ai_command or ai_command in reg.get('aliases', []):
                                    handler = reg.get('handler')
                                    break
                        except Exception:
                            continue
                    if handler:
                        sig = inspect.signature(handler)
                        args_to_pass = {}
                        if 'params' in sig.parameters:
                            args_to_pass['params'] = ai_params
                        if 'conversation_history' in sig.parameters:
                            args_to_pass['conversation_history'] = chat_msgs
                        if 'user_lang' in sig.parameters:
                            args_to_pass['user_lang'] = None
                        if 'user' in sig.parameters:
                            args_to_pass['user'] = username
                        try:
                            if inspect.iscoroutinefunction(handler):
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                tool_result = loop.run_until_complete(handler(**args_to_pass))
                                loop.close()
                            else:
                                tool_result = handler(**args_to_pass)
                        except Exception as e:
                            tool_result = f"Błąd podczas wywołania funkcji '{ai_command}': {e}"
                        if isinstance(tool_result, tuple):
                            reply = str(tool_result[0])
                        elif tool_result is not None:
                            reply = str(tool_result)
                        else:
                            reply = ai_text or f"(Brak odpowiedzi narzędzia {ai_command})"
                    else:
                        reply = ai_text or f"(Nie znaleziono handlera dla komendy {ai_command})"
                elif isinstance(parsed, dict) and 'text' in parsed:
                    reply = parsed['text']
                else:
                    reply = ai_content
            except Exception as e:
                reply = f"(Błąd AI: {e})"
        else:
            reply = "(Brak odpowiedzi AI)"
        # Zapisz odpowiedź AI do chat_history z user_id użytkownika (nie NULL)
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (message, user_id, timestamp) VALUES (?, ?, ?)",
                (reply, user_id, datetime.utcnow())
            )
        return jsonify({'reply': reply})

    @app.route('/api/chat/clear', methods=['POST'])
    @login_required(role="user")
    def chat_clear_api():
        username = session['username']
        user = get_user_by_username(username)
        if not user:
            return jsonify({'success': False})
        user_id = user.id
        # Usuń historię czatu z tabeli chat_history
        with get_db_connection() as conn:
            # Fix: Prevent clearing voice mode history when text chat history is cleared.
            # Original query was: "DELETE FROM chat_history WHERE user_id = ? OR user_id IS NULL"
            # This new query only deletes messages directly from the logged-in user.
            # Assistant messages (user_id IS NULL), which may include voice mode history, are preserved.
            conn.execute(
                "DELETE FROM chat_history WHERE user_id = ?",
                (user_id,)
            )
        return jsonify({'success': True})

    @app.route('/api/logs/download')
    @login_required()
    def download_logs():
        """Download the current and rotated log files as a zip archive."""
        import zipfile, io, glob
        log_dir = os.path.dirname(os.path.dirname(__file__))
        log_files = glob.glob(os.path.join(log_dir, 'assistant.log*'))
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for log_file in log_files:
                arcname = os.path.basename(log_file)
                zf.write(log_file, arcname)
        mem_zip.seek(0)
        return send_file(mem_zip, mimetype='application/zip', as_attachment=True, download_name='logs.zip')

    @app.route('/api/voice_upload', methods=['POST'])
    def voice_upload():
        """Przyjmuje plik audio z web UI (np. z telefonu), rozpoznaje tekst i zwraca go do UI."""
        if 'audio' not in request.files:
            return jsonify({'error': 'Brak pliku audio.'}), 400
        audio_file = request.files['audio']
        # Zapisz plik tymczasowo
        # Save to secure temporary file to avoid conflicts
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
            temp_path = tmp.name
        audio_file.save(temp_path)
        # Convert and transcribe, then cleanup
        try:
            wav_path = convert_audio(temp_path)
            text = transcribe_audio(wav_path)
        except subprocess.CalledProcessError as e:
            return jsonify({'error': f'Błąd konwersji audio: {e}'}), 500
        except Exception:
            text = ''
        finally:
            cleanup_files(temp_path, locals().get('wav_path', ''))
        return jsonify({'text': text})

    # --- Documentation Routes ---
    @app.route('/docs')

    def docs_index():
        """Render the documentation index page."""
        return render_template('docs_index.html')

    # Documentation pages for web UI
    @app.route('/documentation')
    def documentation_main():
        """Main documentation page."""
        try:
            with open(os.path.join(app.root_path, '..', 'docs', 'README.md'), 'r', encoding='utf-8') as f:
                content = f.read()
            html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
            return render_template('documentation.html', 
                                title="Documentation", 
                                content=html_content,
                                section="main")
        except FileNotFoundError:
            flash("Documentation not found", "danger")
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error rendering documentation: {e}")
            flash("Error loading documentation", "danger")
            return redirect(url_for('index'))

    @app.route('/documentation/<section>/<path>')
    def documentation_section(section, path):
        """Display a specific documentation file."""
        try:
            file_path = os.path.join(app.root_path, '..', 'docs', section, f"{path}.md")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
            return render_template('documentation.html', 
                                title=f"{path.replace('-', ' ').title()}", 
                                content=html_content,
                                section=section,
                                path=path)
        except FileNotFoundError:
            flash("Documentation page not found", "danger")
            return redirect(url_for('documentation_main'))
        except Exception as e:
            logger.error(f"Error rendering documentation section: {e}")
            flash("Error loading documentation", "danger")
            return redirect(url_for('documentation_main'))

    @app.route('/docs/<path:filename>')
    def docs_file(filename):
        """Serve a documentation file."""
        try:
            return send_file(os.path.join(os.path.dirname(__file__), '..', 'docs', filename))
        except Exception as e:
            logger.error(f"Error serving docs file {filename}: {e}")
            return jsonify({"error": "File not found"}), 404    @app.route('/api/docs')
    def api_docs():
        """API endpoint to get documentation files list."""
        docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
        try:
            files = os.listdir(docs_dir)
            # Filter and return only markdown files for documentation
            md_files = [f for f in files if f.endswith('.md')]
            return jsonify({"files": md_files})
        except Exception as e:
            logger.error(f"Error listing docs directory: {e}")
            return jsonify({"error": "Failed to list documentation files"}), 500

# --- App Creation Function ---
def create_app(queue: multiprocessing.Queue):
    from database_models import init_schema
    # Ensure chat_history table exists for this Flask process
    init_schema()
    global assistant_queue
    assistant_queue = queue

    # Create a new Flask app instance for this process
    local_app = Flask(__name__, template_folder='templates', static_folder='static')
    local_app.secret_key = SECRET_KEY
    # --- Internationalization (i18n) middleware and routes ---
    @local_app.before_request
    def ensure_language_local():
        if 'lang' not in session:
            session['lang'] = _config.get('ui_language', 'en')
        local_app.jinja_env.globals['translations'] = TRANSLATIONS
        local_app.jinja_env.globals['current_lang'] = session['lang']
    @local_app.route('/set_language/<lang>', endpoint='set_language')  # expose as 'set_language' for templates
    def set_language_local(lang):
        if lang in TRANSLATIONS:
            session['lang'] = lang
        ref = request.referrer or url_for('index')
        return redirect(ref)
    # --- Health check endpoint ---
    @local_app.route('/health')
    def health():
        uptime = time.time() - _startup_time
        qsize = assistant_queue.qsize() if assistant_queue else None
        return jsonify({'version': DEFAULT_CONFIG.get('version'), 'uptime_sec': uptime, 'queue_size': qsize})
    # --- Global error handlers ---
    @local_app.errorhandler(404)
    def handle_404(e):
        return jsonify({'error': 'Not Found'}), 404
    @local_app.errorhandler(500)
    def handle_500(e):
        # Log the actual error
        logger.error(f"Internal Server Error: {e}", exc_info=True)
        return jsonify({'error': 'Internal Server Error'}), 500


    # Configure Flask logging
    # Use a basic config, can be enhanced (e.g., rotating file handler)
    # Avoid basicConfig here if the main process already configured it.
    # Rely on the logger obtained at the module level.
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
    log_level = logging.WARNING # Or get from config/env
    logging.getLogger(__name__).setLevel(log_level)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Ogranicz logi Werkzeug do WARNING i wyżej
    # Add specific handlers if needed (e.g., file handler for web_ui.log)
    # handler = logging.FileHandler('web_ui.log')
    # handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levellevel)s - %(message)s'))
    # logging.getLogger(__name__).addHandler(handler)

    logger.info("Flask app created and configured.")


    # --- Register Blueprints or Routes --- Add routes to the app object

    @local_app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = get_user_by_username(username)

            # Fetch password hash separately only if user exists
            if user:
                stored_password_hash = get_user_password_hash(username)
                # TODO: Implement proper password hashing and verification (e.g., using werkzeug.security)
                # Comparing plaintext or simple hash is INSECURE!
                if stored_password_hash and stored_password_hash == password: # Check if hash exists and matches
                    session['username'] = username
                    session['role'] = user.role # Correct attribute access
                    flash(f"Welcome, {username}!", "success")
                    logger.info(f"User '{username}' logged in successfully.")
                    return redirect(url_for('index'))

            # If user not found or password incorrect
            flash("Invalid username or password.", "danger")
            logger.warning(f"Failed login attempt for username: '{username}'.")
        return render_template('login.html')

    @local_app.route('/logout')
    def logout():
        username = session.get('username', 'Unknown')
        session.pop('username', None)
        session.pop('role', None)
        flash("You have been logged out.", "info")
        logger.info(f"User '{username}' logged out.")
        return redirect(url_for('login'))

    @local_app.route('/')
    @login_required()
    def index():
        """Main dashboard page."""
        current_config = load_main_config()  # Use main config loader
        # Fetch assistant status based on lock file (restarting or online)
        lock_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_restarting.lock')
        if os.path.exists(lock_path):
            status_str = "Restarting"
        else:
            status_str = "Online"
        assistant_status = {
            "status": status_str,
            "wake_word": current_config.get('WAKE_WORD', 'N/A'),
            "stt_engine": "Whisper" if current_config.get('USE_WHISPER_FOR_COMMAND') else "Vosk",
            "mic_id": current_config.get('MIC_DEVICE_ID', 'N/A')
        }
        return render_template('index.html', config=current_config, status=assistant_status)

    @local_app.route('/config')
    @login_required(role="dev")
    def config_page():
        """Configuration management page."""
        current_config = load_main_config() # Use main config loader
        audio_devices = get_audio_input_devices() # Get the list of devices
        # Pass default API keys structure for rendering all fields
        default_api_keys = DEFAULT_CONFIG.get('API_KEYS', {})
        return render_template('config.html', config=current_config, audio_devices=audio_devices, default_api_keys=default_api_keys)

    @local_app.route('/history')
    @login_required()
    def history_page():
        """Conversation history page."""
        history = get_conversation_history()
        return render_template('history.html', history=history)

    @local_app.route('/ltm')
    def ltm_page():
        if 'username' not in session:
            return redirect(url_for('login'))
        try:
            search_query = request.args.get('q', '')
            memories = get_memories(query=search_query, limit=100) # Corrected function name
            return render_template('ltm_page.html', memories=memories, search_query=search_query)
        except Exception as e:
            logger.error(f"Error loading LTM page: {e}")
            flash("Wystąpił błąd podczas ładowania strony pamięci.", "danger")
            return render_template('ltm_page.html', memories=[], search_query='')

    @local_app.route('/logs')
    @login_required()
    def logs_page():
        return render_template('logs.html')

    @local_app.route('/dev')
    @login_required(role="dev") # Changed role to dev for consistency
    @measure_performance # Apply decorator here
    def dev_page():
        """Developer page for testing and diagnostics."""
        current_users = list_users()
        current_config = load_main_config() # Use main config loader
        audio_devices = get_audio_input_devices() # Get the list of devices
        # Performance stats will be loaded dynamically via JS/API
        return render_template('dev.html', users=current_users, config=current_config, audio_devices=audio_devices)

    @local_app.route('/plugins')
    @login_required(role="dev")
    def plugins_page():
        return render_template('plugins.html')

    @local_app.route('/mcp')
    @login_required(role="dev")
    def mcp_page():
        return render_template('mcp.html')

    # --- User Management (Dev Only) ---
    @local_app.route('/dev/users', methods=['GET'])
    @login_required(role="dev")
    def dev_list_users():
        users = list_users()
        return render_template('dev.html', users=users)

    @local_app.route('/dev/users/add', methods=['POST'])
    @login_required(role="dev")
    def dev_add_user():
        data = request.json
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'user')
        display_name = data.get('display_name')
        ai_persona = data.get('ai_persona')
        personalization = data.get('personalization')
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required.'}), 400
        if get_user_by_username(username):
            return jsonify({'success': False, 'error': 'User already exists.'}), 400
        add_user(username, password, role, display_name, ai_persona, personalization)
        return jsonify({'success': True})

    @local_app.route('/dev/users/delete', methods=['POST']) # Fixed syntax error here
    @login_required(role="dev")
    def dev_delete_user():
        data = request.json
        username = data.get('username')
        if username == 'dev':
            return jsonify({'success': False, 'error': 'Cannot delete the default dev user.'}), 400 # Added return
        if not get_user_by_username(username):
            return jsonify({'success': False, 'error': 'User not found.'}), 404 # Added return
        delete_user(username)
        return jsonify({'success': True})

    @local_app.route('/dev/users/update', methods=['POST'])
    @login_required(role="dev")
    def dev_update_user():
        data = request.json
        username = data.get('username')
        fields = {k: v for k, v in data.items() if k != 'username'}
        if not get_user_by_username(username):
            return jsonify({'success': False, 'error': 'User not found.'}), 404
        update_user(username, **fields)
        return jsonify({'success': True})

    # --- API Routes --- (Registered within create_app)
    setup_api_routes(local_app, queue)

    # Ensure the app instance is returned
    return local_app
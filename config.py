# config.py
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

"""
Configuration file path: use executable directory when frozen (PyInstaller), otherwise module directory.
"""
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle: prefer real install dir (where exe resides)
    exe_path = os.path.abspath(sys.argv[0])
    exe_dir = os.path.dirname(exe_path)
    # If a 'resources' folder exists next to the exe, use that as base
    if os.path.isdir(os.path.join(exe_dir, 'resources')):
        BASE_DIR = exe_dir
    else:
        # Fallback to bundled temp dir (_MEIPASS) for onefile builds
        BASE_DIR = getattr(sys, '_MEIPASS', exe_dir)
else:
    # Running in normal Python environment
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE_PATH = os.path.join(BASE_DIR, 'config.json')
CONFIG_FILE = CONFIG_FILE_PATH  # Alias for compatibility in tests

DEFAULT_CONFIG = {
  "ASSISTANT_NAME": "Gaja",
  "WAKE_WORD": "gaja",
  "WAKE_WORD_SENSITIVITY_THRESHOLD": 0.35,
  "LANGUAGE": "pl-PL",
  "API_KEYS": {
    "OPENAI_API_KEY": "YOUR_OPENAI_API_KEY",
    "AZURE_SPEECH_KEY": "YOUR_AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION": "YOUR_AZURE_REGION",
    "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY": "YOUR_DEEPSEEK_API_KEY"
  },
  "STT_MODEL": "whisper-1", # Speech-to-Text model (cloud, e.g. OpenAI)
  "MAIN_MODEL": "gpt-4.1-nano",   # Main interaction LLM
  "PROVIDER": "openai", # Default provider for MAIN_MODEL if not specified in model string
  "DEEP_MODEL": "gpt-4.1-nano", # Model for deeper analysis if needed
  "MIC_DEVICE_ID": None,
  "STT_SILENCE_THRESHOLD": 500, # Milliseconds of silence to end STT
  "WHISPER_MODEL": "openai/whisper-base", # Local whisper model (for wakeword confirmation or primary STT if cloud STT fails/disabled)
  "MAX_HISTORY_LENGTH": 10,
  "PLUGIN_MONITOR_INTERVAL": 30, # Seconds
  "LOW_POWER_MODE": False,
  "EXIT_WITH_CONSOLE": False, # If true, console stays open after assistant exits
  "DEV_MODE": False, # Enables more verbose logging and potentially other dev features
  "FIRST_RUN": True, # Flag to indicate if this is the first run of the application
  "query_refinement": {
    "model": "gpt-4.1-nano", # Model for query refinement
    "enabled": True
  },  "version": "1.1.0", # Current assistant version
  "AUTO_LISTEN_AFTER_TTS": False, # Should assistant listen automatically after speaking?
  "TRACK_ACTIVE_WINDOW": False, # Track active window title for context
  "ACTIVE_WINDOW_POLL_INTERVAL": 5, # Seconds
  "USE_FUNCTION_CALLING": True # Enable OpenAI Function Calling (requires OpenAI provider)
}

# Global dictionary to hold the current configuration
_config = {}

# Global accessor variables, initialized with defaults or None
ASSISTANT_NAME = DEFAULT_CONFIG["ASSISTANT_NAME"]
WAKE_WORD = DEFAULT_CONFIG["WAKE_WORD"]
WAKE_WORD_SENSITIVITY_THRESHOLD = DEFAULT_CONFIG["WAKE_WORD_SENSITIVITY_THRESHOLD"]
LANGUAGE = DEFAULT_CONFIG["LANGUAGE"]
OPENAI_API_KEY = DEFAULT_CONFIG["API_KEYS"]["OPENAI_API_KEY"]
AZURE_SPEECH_KEY = DEFAULT_CONFIG["API_KEYS"]["AZURE_SPEECH_KEY"]
AZURE_SPEECH_REGION = DEFAULT_CONFIG["API_KEYS"]["AZURE_SPEECH_REGION"]
ANTHROPIC_API_KEY = DEFAULT_CONFIG["API_KEYS"]["ANTHROPIC_API_KEY"]
DEEPSEEK_API_KEY = DEFAULT_CONFIG["API_KEYS"]["DEEPSEEK_API_KEY"]
STT_MODEL = DEFAULT_CONFIG["STT_MODEL"]
MAIN_MODEL = DEFAULT_CONFIG["MAIN_MODEL"]
PROVIDER = DEFAULT_CONFIG["PROVIDER"]
DEEP_MODEL = DEFAULT_CONFIG["DEEP_MODEL"]
MIC_DEVICE_ID = DEFAULT_CONFIG["MIC_DEVICE_ID"]
STT_SILENCE_THRESHOLD = DEFAULT_CONFIG["STT_SILENCE_THRESHOLD"]
WHISPER_MODEL = DEFAULT_CONFIG["WHISPER_MODEL"]
MAX_HISTORY_LENGTH = DEFAULT_CONFIG["MAX_HISTORY_LENGTH"]
PLUGIN_MONITOR_INTERVAL = DEFAULT_CONFIG["PLUGIN_MONITOR_INTERVAL"]
LOW_POWER_MODE = DEFAULT_CONFIG["LOW_POWER_MODE"]
EXIT_WITH_CONSOLE = DEFAULT_CONFIG["EXIT_WITH_CONSOLE"]
DEV_MODE = DEFAULT_CONFIG["DEV_MODE"]
FIRST_RUN = DEFAULT_CONFIG["FIRST_RUN"]
query_refinement = DEFAULT_CONFIG["query_refinement"].copy() # Ensure it's a copy
version = DEFAULT_CONFIG["version"]
AUTO_LISTEN_AFTER_TTS = DEFAULT_CONFIG["AUTO_LISTEN_AFTER_TTS"]
TRACK_ACTIVE_WINDOW = DEFAULT_CONFIG["TRACK_ACTIVE_WINDOW"]
ACTIVE_WINDOW_POLL_INTERVAL = DEFAULT_CONFIG["ACTIVE_WINDOW_POLL_INTERVAL"]
USE_FUNCTION_CALLING = DEFAULT_CONFIG["USE_FUNCTION_CALLING"]
API_KEYS = DEFAULT_CONFIG["API_KEYS"].copy()


def load_config(path=CONFIG_FILE_PATH):
    global _config, ASSISTANT_NAME, WAKE_WORD, WAKE_WORD_SENSITIVITY_THRESHOLD, LANGUAGE, \
           OPENAI_API_KEY, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, \
           STT_MODEL, MAIN_MODEL, PROVIDER, DEEP_MODEL, WHISPER_MODEL, \
           MAX_HISTORY_LENGTH, LOW_POWER_MODE, EXIT_WITH_CONSOLE, DEV_MODE, \
           AUTO_LISTEN_AFTER_TTS, TRACK_ACTIVE_WINDOW, ACTIVE_WINDOW_POLL_INTERVAL, \
           USE_FUNCTION_CALLING, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, \
           MIC_DEVICE_ID, STT_SILENCE_THRESHOLD, API_KEYS, query_refinement, version, \
           PLUGIN_MONITOR_INTERVAL, FIRST_RUN

    loaded_file_data = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            loaded_file_data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config file '{path}' not found. Creating default config file with default settings.")
        # Load defaults and create the config file
        loaded_file_data = DEFAULT_CONFIG.copy()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(loaded_file_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Created default config file at '{path}'.")
        except Exception as e_write:
            logger.error(f"Failed to create default config file at '{path}': {e_write}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from '{path}': {e}. Using default config in-memory.")
        loaded_file_data = DEFAULT_CONFIG.copy()
        # Do not overwrite config file on JSON error to avoid unintended overwrites
    
    # Normalize certain fields to proper types
    # MIC_DEVICE_ID and STT_SILENCE_THRESHOLD should be ints
    if 'MIC_DEVICE_ID' in loaded_file_data:
        try:
            loaded_file_data['MIC_DEVICE_ID'] = int(loaded_file_data['MIC_DEVICE_ID'])
        except Exception:
            pass
    if 'STT_SILENCE_THRESHOLD' in loaded_file_data:
        try:
            loaded_file_data['STT_SILENCE_THRESHOLD'] = int(loaded_file_data['STT_SILENCE_THRESHOLD'])
        except Exception:
            pass
    # WAKE_WORD_SENSITIVITY_THRESHOLD should be float
    if 'WAKE_WORD_SENSITIVITY_THRESHOLD' in loaded_file_data:
        try:
            loaded_file_data['WAKE_WORD_SENSITIVITY_THRESHOLD'] = float(loaded_file_data['WAKE_WORD_SENSITIVITY_THRESHOLD'])
        except Exception:
            pass
    # Update in-memory config
    _config.clear()
    _config.update(loaded_file_data)

    ASSISTANT_NAME = _config.get("ASSISTANT_NAME", DEFAULT_CONFIG["ASSISTANT_NAME"])
    WAKE_WORD = _config.get("WAKE_WORD", DEFAULT_CONFIG["WAKE_WORD"])
    WAKE_WORD_SENSITIVITY_THRESHOLD = _config.get("WAKE_WORD_SENSITIVITY_THRESHOLD", DEFAULT_CONFIG["WAKE_WORD_SENSITIVITY_THRESHOLD"])
    LANGUAGE = _config.get("LANGUAGE", DEFAULT_CONFIG["LANGUAGE"])
    
    API_KEYS = _config.get("API_KEYS", DEFAULT_CONFIG["API_KEYS"].copy())
    OPENAI_API_KEY = API_KEYS.get("OPENAI_API_KEY", DEFAULT_CONFIG["API_KEYS"]["OPENAI_API_KEY"])
    AZURE_SPEECH_KEY = API_KEYS.get("AZURE_SPEECH_KEY", DEFAULT_CONFIG["API_KEYS"]["AZURE_SPEECH_KEY"])
    AZURE_SPEECH_REGION = API_KEYS.get("AZURE_SPEECH_REGION", DEFAULT_CONFIG["API_KEYS"]["AZURE_SPEECH_REGION"])
    ANTHROPIC_API_KEY = API_KEYS.get("ANTHROPIC_API_KEY", DEFAULT_CONFIG["API_KEYS"]["ANTHROPIC_API_KEY"])
    DEEPSEEK_API_KEY = API_KEYS.get("DEEPSEEK_API_KEY", DEFAULT_CONFIG["API_KEYS"]["DEEPSEEK_API_KEY"])

    STT_MODEL = _config.get("STT_MODEL", DEFAULT_CONFIG["STT_MODEL"])
    MAIN_MODEL = _config.get("MAIN_MODEL", DEFAULT_CONFIG["MAIN_MODEL"])
    PROVIDER = _config.get("PROVIDER", DEFAULT_CONFIG["PROVIDER"])
    DEEP_MODEL = _config.get("DEEP_MODEL", DEFAULT_CONFIG["DEEP_MODEL"])
    MIC_DEVICE_ID = _config.get("MIC_DEVICE_ID", DEFAULT_CONFIG["MIC_DEVICE_ID"])
    STT_SILENCE_THRESHOLD = _config.get("STT_SILENCE_THRESHOLD", DEFAULT_CONFIG["STT_SILENCE_THRESHOLD"])
    WHISPER_MODEL = _config.get("WHISPER_MODEL", DEFAULT_CONFIG["WHISPER_MODEL"])
    MAX_HISTORY_LENGTH = _config.get("MAX_HISTORY_LENGTH", DEFAULT_CONFIG["MAX_HISTORY_LENGTH"])
    PLUGIN_MONITOR_INTERVAL = _config.get("PLUGIN_MONITOR_INTERVAL", DEFAULT_CONFIG["PLUGIN_MONITOR_INTERVAL"])
    LOW_POWER_MODE = _config.get("LOW_POWER_MODE", DEFAULT_CONFIG["LOW_POWER_MODE"])
    EXIT_WITH_CONSOLE = _config.get("EXIT_WITH_CONSOLE", DEFAULT_CONFIG["EXIT_WITH_CONSOLE"])
    DEV_MODE = _config.get("DEV_MODE", DEFAULT_CONFIG["DEV_MODE"])
    
    query_refinement = _config.get("query_refinement", DEFAULT_CONFIG["query_refinement"].copy())
    
    version = _config.get("version", DEFAULT_CONFIG["version"])
    AUTO_LISTEN_AFTER_TTS = _config.get("AUTO_LISTEN_AFTER_TTS", DEFAULT_CONFIG["AUTO_LISTEN_AFTER_TTS"])
    TRACK_ACTIVE_WINDOW = _config.get("TRACK_ACTIVE_WINDOW", DEFAULT_CONFIG["TRACK_ACTIVE_WINDOW"])
    ACTIVE_WINDOW_POLL_INTERVAL = _config.get("ACTIVE_WINDOW_POLL_INTERVAL", DEFAULT_CONFIG["ACTIVE_WINDOW_POLL_INTERVAL"])
    USE_FUNCTION_CALLING = _config.get("USE_FUNCTION_CALLING", DEFAULT_CONFIG["USE_FUNCTION_CALLING"])
    FIRST_RUN = _config.get("FIRST_RUN", DEFAULT_CONFIG["FIRST_RUN"])

    return _config # Return the global _config dict itself

def save_config(data_to_save=None, path=CONFIG_FILE_PATH):
    """Saves the provided configuration data to the specified path.
    If no data is provided, it saves the current global _config.
    """
    global _config
    if data_to_save is None:
        data_to_save = _config
    
    # Ensure legacy keys are not saved
    data_to_save.pop("SPEECH_RECOGNITION_PROVIDER", None)
            
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuration saved successfully to '{path}'.")
    except Exception as e:
        logger.error(f"Could not save configuration to '{path}': {e}")

# Initial load of configuration when the module is imported.
# Other modules can then import _config or the individual accessor variables.
load_config()
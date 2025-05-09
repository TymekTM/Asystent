# config.py
import json
import os
import logging
import psutil  # for environment detection

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CONFIG_FILE = "config.json"
# Default configuration values
DEFAULT_CONFIG = {
  "VOSK_MODEL_PATH": "vosk_model",
  "WAKE_WORD": "asystencie",
  "MIC_DEVICE_ID": None, # Default to None, let sounddevice choose
  "STT_SILENCE_THRESHOLD": 600,
  "PROVIDER": "openai",
  "STT_MODEL": "gpt-4.1-nano",
  "MAIN_MODEL": "gpt-4.1-nano",
  "DEEP_MODEL": "openthinker",
  "USE_WHISPER_FOR_COMMAND": True,
  "WHISPER_MODEL": "openai/whisper-small",
  "MAX_HISTORY_LENGTH": 20,
  "LOW_POWER_MODE": False, # Default to False
  "EXIT_WITH_CONSOLE": True, # Default to True
  "DEV_MODE": False, # Default to False - prevents model unloading on exit if True
  "AUTO_LISTEN_AFTER_TTS": False, # Default to False
  "TRACK_ACTIVE_WINDOW": True, # Default to True
  "API_KEYS": {
    "OPENAI_API_KEY": "None",
    "DEEPSEEK_API_KEY": "None",
    "ANTHROPIC_API_KEY": "None",
  },
  "query_refinement": {
    "enabled": True,
    "model": "gpt-4.1-nano"
  },
  "version": "1.1.0", # Add version here
  "ACTIVE_WINDOW_POLL_INTERVAL": 5 # Seconds
}

# Extract default values for direct import elsewhere
VOSK_MODEL_PATH = DEFAULT_CONFIG['VOSK_MODEL_PATH']
WHISPER_MODEL = DEFAULT_CONFIG['WHISPER_MODEL']
MAX_HISTORY_LENGTH = DEFAULT_CONFIG['MAX_HISTORY_LENGTH']
LOW_POWER_MODE = DEFAULT_CONFIG['LOW_POWER_MODE']
EXIT_WITH_CONSOLE = DEFAULT_CONFIG['EXIT_WITH_CONSOLE']
DEV_MODE = DEFAULT_CONFIG['DEV_MODE'] # Add DEV_MODE here
TRACK_ACTIVE_WINDOW = DEFAULT_CONFIG['TRACK_ACTIVE_WINDOW']
ACTIVE_WINDOW_POLL_INTERVAL = DEFAULT_CONFIG['ACTIVE_WINDOW_POLL_INTERVAL']

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ensure all default keys exist
                updated = False
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                        updated = True
                        logger.info(f"Added missing default config key: {key}")
                    # Handle nested dicts like API_KEYS and query_refinement
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if key not in config or not isinstance(config[key], dict) or sub_key not in config[key]:
                                 if key not in config or not isinstance(config[key], dict):
                                     config[key] = {} # Ensure the key exists as a dict
                                 config[key][sub_key] = sub_value
                                 updated = True
                                 logger.info(f"Added missing default config sub-key: {key}.{sub_key}")

                # Save back if defaults were added
                if updated:
                    save_config(config)

                return config
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading {CONFIG_FILE}: {e}. Using default config.")
            return DEFAULT_CONFIG
    else:
        logger.warning(f"{CONFIG_FILE} not found. Creating with default values.")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config_data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Error saving {CONFIG_FILE}: {e}")

# Load configuration once at startup
_config = load_config()

# Auto-enable low power mode based on system resources if not explicitly set
try:
    if not _config.get('LOW_POWER_MODE', False):
        total_gb = psutil.virtual_memory().total / (1024 ** 3)
        cpus = psutil.cpu_count(logical=False) or psutil.cpu_count()
        thresholds = _config.get('LOW_POWER_THRESHOLDS', {})
        if total_gb < thresholds.get('memory_gb', 1) or cpus < thresholds.get('cpu_count', 2):
            _config['LOW_POWER_MODE'] = True
            logger.info("Low power environment detected (mem: %.1fGB, cpus: %d). Enabling LOW_POWER_MODE.", total_gb, cpus)
except Exception as e:
    logger.warning("Failed to auto-detect low power mode: %s", e)

# --- Accessor variables ---
VOSK_MODEL_PATH = _config.get("VOSK_MODEL_PATH")
MIC_DEVICE_ID = _config.get("MIC_DEVICE_ID")
WAKE_WORD = _config.get("WAKE_WORD")
STT_SILENCE_THRESHOLD = _config.get("STT_SILENCE_THRESHOLD")
STT_MODEL = _config.get("STT_MODEL")
MAIN_MODEL = _config.get("MAIN_MODEL")
DEEP_MODEL = _config.get("DEEP_MODEL")
PROVIDER = _config.get("PROVIDER")
USE_WHISPER_FOR_COMMAND = _config.get("USE_WHISPER_FOR_COMMAND")
WHISPER_MODEL = _config.get("WHISPER_MODEL")
MAX_HISTORY_LENGTH = _config.get("MAX_HISTORY_LENGTH")
PLUGIN_MONITOR_INTERVAL = _config.get("PLUGIN_MONITOR_INTERVAL")
AUTO_LISTEN_AFTER_TTS = _config.get("AUTO_LISTEN_AFTER_TTS") # Add this line

# Load API keys into environment variables if they exist in the config and are not None
# This maintains compatibility with how ai_module checks for keys
API_KEYS = _config.get("API_KEYS", {})
if isinstance(API_KEYS, str):
    try:
        import ast
        API_KEYS = ast.literal_eval(API_KEYS)
    except Exception:
        API_KEYS = {}
for key, value in API_KEYS.items():
    if value and value != f"YOUR_{key}_HERE": # Don't set if it's None or the placeholder
        os.environ[key] = value

# expose low power flag
LOW_POWER_MODE = _config.get('LOW_POWER_MODE', False)
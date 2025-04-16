# config.py
import json
import os
import logging
import psutil  # for environment detection

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
  "VOSK_MODEL_PATH": "vosk_model",
  "MIC_DEVICE_ID": 14,
  "WAKE_WORD": "asystencie",
  "STT_SILENCE_THRESHOLD": 600,
  "STT_MODEL": "gemma3:4b-it-q4_K_M",
  "MAIN_MODEL": "gemma3:4b-it-q4_K_M",
  "DEEP_MODEL": "openthinker",
  "PROVIDER": "lmstudio",
  "USE_WHISPER_FOR_COMMAND": False,
  "WHISPER_MODEL": "openai/whisper-small",
  "MAX_HISTORY_LENGTH": 20,
  "PLUGIN_MONITOR_INTERVAL": 30,
  "EXIT_WITH_CONSOLE": True,  # Jeśli true, bot wyłącza się razem z konsolą/rodzicem
  "API_KEYS": {
    "OPENAI_API_KEY": None,
    "DEEPSEEK_API_KEY": None,
    "ANTHROPIC_API_KEY": None
  },
  "LOW_POWER_MODE": False,
  "LOW_POWER_THRESHOLDS": {"memory_gb": 1, "cpu_count": 2}
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ensure all default keys exist
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict): # Handle nested dicts like API_KEYS
                         for sub_key, sub_value in value.items():
                              if sub_key not in config[key]:
                                   config[key][sub_key] = sub_value
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
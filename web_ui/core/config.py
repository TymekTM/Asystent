import os
import sys
import time
import logging

# Ensure parent directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Define custom exception for file lock errors
class LogFileLockedError(IOError):
    pass

# Configuration
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Fallback to generated key if not provided via environment
    SECRET_KEY = os.urandom(24)

# Import config from main module
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import load_config as load_main_config, save_config as save_main_config, CONFIG_FILE_PATH as MAIN_CONFIG_FILE, DEFAULT_CONFIG, _config

# File paths
CONFIG_FILE = MAIN_CONFIG_FILE
CONFIG_FILE_PATH = MAIN_CONFIG_FILE  # Additional alias for compatibility
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'user_data', 'assistant.log')
HISTORY_ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'history_archive')
LTM_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'long_term_memory.json')

# Startup time
_startup_time = time.time()

# Logger
logger = logging.getLogger(__name__)

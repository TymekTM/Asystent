import webbrowser
import logging
import os
import json
from config import save_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def mark_onboarding_complete():
    """Mark onboarding as complete in configuration."""
    try:
        # Load current config
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Update first run flag
        config['FIRST_RUN'] = False

        # Save updated config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info("Onboarding marked as complete in configuration")
        return True
    except Exception as e:
        logger.error(f"Failed to mark onboarding as complete: {e}", exc_info=True)
        return False

def open_onboarding(port=5000):
    """Open the onboarding page in default browser."""
    try:
        url = f"http://localhost:{port}/onboarding"
        webbrowser.open(url)
        logger.info(f"Opening onboarding page: {url}")
        return True
    except Exception as e:
        logger.error(f"Failed to open onboarding page: {e}", exc_info=True)
        return False

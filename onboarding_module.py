import webbrowser
import logging
import os
import json
from config import save_config, load_config, CONFIG_FILE_PATH

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def mark_onboarding_complete():
    """Mark onboarding as complete in configuration."""
    try:
        # It's better to use the existing config loading and saving mechanism
        # to ensure consistency and handle potential complexities already managed there.
        current_config = load_config(CONFIG_FILE_PATH) # Load the most recent config
        if current_config is None:
            logger.error("Failed to load configuration for marking onboarding complete.")
            return False

        # Update first run flag
        current_config['FIRST_RUN'] = False

        # Save updated config using the global save_config function
        save_config(current_config, CONFIG_FILE_PATH)

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

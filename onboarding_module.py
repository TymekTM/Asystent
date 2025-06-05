import webbrowser
import logging
import os
import json
import requests
from config import save_config, load_config, CONFIG_FILE_PATH

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_location_from_ip():
    """Get user location based on IP address."""
    try:
        response = requests.get('http://ip-api.com/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                city = data.get('city', 'Warsaw')
                country_code = data.get('countryCode', 'PL')
                return f"{city},{country_code}"
    except Exception as e:
        logger.warning(f"Failed to get location from IP: {e}")
    
    return "Warsaw,PL"  # Default fallback

def save_onboarding_data(config_data):
    """Save onboarding configuration data."""
    try:
        current_config = load_config(CONFIG_FILE_PATH)
        if current_config is None:
            logger.error("Failed to load configuration for saving onboarding data.")
            return False

        # Update config with onboarding data
        if 'USER_NAME' in config_data:
            current_config['USER_NAME'] = config_data['USER_NAME']
            
        # Update daily briefing config
        if 'daily_briefing' in config_data:
            if 'daily_briefing' not in current_config:
                current_config['daily_briefing'] = {}
            current_config['daily_briefing'].update(config_data['daily_briefing'])
            
        # Update other config fields
        for key, value in config_data.items():
            if key not in ['daily_briefing']:
                current_config[key] = value

        # Save updated config
        save_config(current_config, CONFIG_FILE_PATH)
        logger.info("Onboarding data saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save onboarding data: {e}", exc_info=True)
        return False

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

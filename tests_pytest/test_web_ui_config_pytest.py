import pytest
from flask import url_for
import json
from config import CONFIG_FILE_PATH # Added import

# Sample configuration data to be used in tests
SAMPLE_CONFIG = {
    "WAKE_WORD": "gaja",
    "MIC_DEVICE_ID": 1,
    "STT_SILENCE_THRESHOLD": 600,
    "PROVIDER": "openai",
    "STT_MODEL": "gpt-4.1-nano",
    "MAIN_MODEL": "gpt-4.1-nano",
    "DEEP_MODEL": "openthinker",
    # "USE_WHISPER_FOR_COMMAND": True, # Removed
    "WHISPER_MODEL": "openai/whisper-small",
    "MAX_HISTORY_LENGTH": 20,
    "PLUGIN_MONITOR_INTERVAL": 30,
    "API_KEYS": {
        "ANTHROPIC_API_KEY": "None"
    },
    "LOW_POWER_MODE": False,
    "EXIT_WITH_CONSOLE": True,
    "DEV_MODE": False,
    "query_refinement": {
        "model": "gpt-4.1-nano"
    },
    "version": "1.1.0",
    "AUTO_LISTEN_AFTER_TTS": False
}

@pytest.fixture
def client(app):
    """A test client for the app."""
    # Ensure that the app uses a temporary config file for tests
    # This can be achieved by setting the app.config['CONFIG_FILE_PATH'] or similar
    # For now, we'll rely on tests explicitly managing the config file they use.
    return app.test_client()

@pytest.fixture
def app_context(app):
    """Creates an application context for the tests."""
    with app.app_context():
        yield

def test_config_page_loads_correctly(client, app_context):
    """Test that the config page loads and displays current config."""
    # Mock the config file reading
    with open(CONFIG_FILE_PATH, 'w') as f: # Use imported CONFIG_FILE_PATH
        json.dump(SAMPLE_CONFIG, f)

    response = client.get(url_for('config'))
    assert response.status_code == 200
    assert b"Konfiguracja Asystenta" in response.data
    # Check if some of the sample config values are present in the form
    assert bytes(SAMPLE_CONFIG["WAKE_WORD"], 'utf-8') in response.data
    assert bytes(str(SAMPLE_CONFIG["MIC_DEVICE_ID"]), 'utf-8') in response.data

def test_config_page_saves_correctly(client, app_context):
    """Test that the config page saves new values."""
    new_wake_word = "nova"
    new_mic_id = 2

    # Prepare a modified config based on SAMPLE_CONFIG
    modified_config_data = SAMPLE_CONFIG.copy()
    modified_config_data["WAKE_WORD"] = new_wake_word
    modified_config_data["MIC_DEVICE_ID"] = new_mic_id
    # Ensure API_KEYS is a dictionary if it's not already or needs specific structure
    if "API_KEYS" not in modified_config_data or not isinstance(modified_config_data.get("API_KEYS"), dict):
        modified_config_data["API_KEYS"] = {} # Initialize if not present or not a dict
    modified_config_data["API_KEYS"]["ANTHROPIC_API_KEY"] = SAMPLE_CONFIG.get("API_KEYS", {}).get("ANTHROPIC_API_KEY", "None")


    # Initial load to ensure config.json exists using CONFIG_FILE_PATH
    with open(CONFIG_FILE_PATH, 'w') as f: # Use imported CONFIG_FILE_PATH
        json.dump(SAMPLE_CONFIG, f)
    
    client.get(url_for('config')) # Load page once if needed by app logic

    # Construct the form data from modified_config_data
    form_data = {
        "WAKE_WORD": modified_config_data["WAKE_WORD"],
        "MIC_DEVICE_ID": str(modified_config_data["MIC_DEVICE_ID"]),
        "STT_SILENCE_THRESHOLD": str(modified_config_data["STT_SILENCE_THRESHOLD"]),
        "PROVIDER": modified_config_data["PROVIDER"],
        "STT_MODEL": modified_config_data["STT_MODEL"],
        "MAIN_MODEL": modified_config_data["MAIN_MODEL"],
        "DEEP_MODEL": modified_config_data["DEEP_MODEL"],
        "WHISPER_MODEL": modified_config_data["WHISPER_MODEL"],
        "MAX_HISTORY_LENGTH": str(modified_config_data["MAX_HISTORY_LENGTH"]),
        "PLUGIN_MONITOR_INTERVAL": str(modified_config_data["PLUGIN_MONITOR_INTERVAL"]),
        "API_KEYS[ANTHROPIC_API_KEY]": modified_config_data["API_KEYS"]["ANTHROPIC_API_KEY"],
        "LOW_POWER_MODE": "True" if modified_config_data["LOW_POWER_MODE"] else "",
        "EXIT_WITH_CONSOLE": "True" if modified_config_data["EXIT_WITH_CONSOLE"] else "",
        "DEV_MODE": "True" if modified_config_data["DEV_MODE"] else "",
        "AUTO_LISTEN_AFTER_TTS": "True" if modified_config_data["AUTO_LISTEN_AFTER_TTS"] else "",
    }
    # Add other necessary fields from SAMPLE_CONFIG that are expected by the form
    # For example, if query_refinement fields are separate form inputs:
    if "query_refinement" in modified_config_data and isinstance(modified_config_data["query_refinement"], dict):
        form_data["query_refinement[model]"] = modified_config_data["query_refinement"].get("model", "")
        # Add other query_refinement fields if they exist as separate form inputs

    response = client.post(url_for('config'), data=form_data)

    assert response.status_code == 200 # Or 302 if redirecting
    assert b"Configuration saved successfully!" in response.data

    # Verify the config.json was updated
    with open(CONFIG_FILE_PATH, 'r') as f: # Use imported CONFIG_FILE_PATH
        updated_config = json.load(f)
    
    assert updated_config["WAKE_WORD"] == new_wake_word
    assert updated_config["MIC_DEVICE_ID"] == new_mic_id

def test_config_page_handles_invalid_mic_id(client, app_context):
    """Test that the config page handles invalid MIC_DEVICE_ID."""
    with open(CONFIG_FILE_PATH, 'w') as f: # Use imported CONFIG_FILE_PATH
        json.dump(SAMPLE_CONFIG, f)

    response = client.post(url_for('config'), data={
        # "VOSK_MODEL_PATH": SAMPLE_CONFIG["VOSK_MODEL_PATH"], # Removed
        "WAKE_WORD": SAMPLE_CONFIG["WAKE_WORD"],
        "MIC_DEVICE_ID": "not_an_integer", # Invalid value
        "STT_SILENCE_THRESHOLD": str(SAMPLE_CONFIG["STT_SILENCE_THRESHOLD"]),
        "PROVIDER": SAMPLE_CONFIG["PROVIDER"],
        "STT_MODEL": SAMPLE_CONFIG["STT_MODEL"],
        "MAIN_MODEL": SAMPLE_CONFIG["MAIN_MODEL"],
        "DEEP_MODEL": SAMPLE_CONFIG["DEEP_MODEL"],
        # "USE_WHISPER_FOR_COMMAND": "True" if SAMPLE_CONFIG["USE_WHISPER_FOR_COMMAND"] else "", # Removed
        "WHISPER_MODEL": SAMPLE_CONFIG["WHISPER_MODEL"],
        "MAX_HISTORY_LENGTH": str(SAMPLE_CONFIG["MAX_HISTORY_LENGTH"]),
        "PLUGIN_MONITOR_INTERVAL": str(SAMPLE_CONFIG["PLUGIN_MONITOR_INTERVAL"]),
        "API_KEYS[ANTHROPIC_API_KEY]": SAMPLE_CONFIG["API_KEYS"]["ANTHROPIC_API_KEY"],
        "LOW_POWER_MODE": "True" if SAMPLE_CONFIG["LOW_POWER_MODE"] else "",
        "EXIT_WITH_CONSOLE": "True" if SAMPLE_CONFIG["EXIT_WITH_CONSOLE"] else "",
        "DEV_MODE": "True" if SAMPLE_CONFIG["DEV_MODE"] else "",
        "AUTO_LISTEN_AFTER_TTS": "True" if SAMPLE_CONFIG["AUTO_LISTEN_AFTER_TTS"] else "",
    })
    assert response.status_code == 200 # Or appropriate error code/page
    assert b"Invalid MIC_DEVICE_ID" in response.data # Or some other error message

    # Ensure config was not saved with invalid data
    with open(CONFIG_FILE_PATH, 'r') as f: # Use imported CONFIG_FILE_PATH
        current_config = json.load(f)
    assert current_config["MIC_DEVICE_ID"] == SAMPLE_CONFIG["MIC_DEVICE_ID"]

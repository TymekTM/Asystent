import pytest
from flask import url_for
import json

# Sample configuration data to be used in tests
SAMPLE_CONFIG = {
    "VOSK_MODEL_PATH": "vosk_model",
    "WAKE_WORD": "gaja",
    "MIC_DEVICE_ID": 1,
    "STT_SILENCE_THRESHOLD": 600,
    "PROVIDER": "openai",
    "STT_MODEL": "gpt-4.1-nano",
    "MAIN_MODEL": "gpt-4.1-nano",
    "DEEP_MODEL": "openthinker",
    "USE_WHISPER_FOR_COMMAND": True,
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
    return app.test_client()

@pytest.fixture
def app_context(app):
    """Creates an application context for the tests."""
    with app.app_context():
        yield

def test_config_page_loads_correctly(client, app_context):
    """Test that the config page loads and displays current config."""
    # Mock the config file reading
    with open('f:\\Asystent\\config.json', 'w') as f:
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

    # Initial load to ensure config.json exists via the other test or a setup step
    with open('f:\\Asystent\\config.json', 'w') as f:
        json.dump(SAMPLE_CONFIG, f)
    
    client.get(url_for('config')) # Load page once if needed by app logic

    response = client.post(url_for('config'), data={
        **SAMPLE_CONFIG, # Spread existing config
        "WAKE_WORD": new_wake_word,
        "MIC_DEVICE_ID": new_mic_id,
        # Ensure all boolean fields that might be missing from form post are included
        "USE_WHISPER_FOR_COMMAND": "True" if SAMPLE_CONFIG["USE_WHISPER_FOR_COMMAND"] else "",
        "LOW_POWER_MODE": "True" if SAMPLE_CONFIG["LOW_POWER_MODE"] else "",
        "EXIT_WITH_CONSOLE": "True" if SAMPLE_CONFIG["EXIT_WITH_CONSOLE"] else "",
        "DEV_MODE": "True" if SAMPLE_CONFIG["DEV_MODE"] else "",
        "AUTO_LISTEN_AFTER_TTS": "True" if SAMPLE_CONFIG["AUTO_LISTEN_AFTER_TTS"] else "",
    })
    assert response.status_code == 200 # Or 302 if redirecting
    assert b"Configuration saved successfully!" in response.data

    # Verify the config.json was updated
    with open('f:\\Asystent\\config.json', 'r') as f:
        updated_config = json.load(f)
    
    assert updated_config["WAKE_WORD"] == new_wake_word
    assert updated_config["MIC_DEVICE_ID"] == new_mic_id

def test_config_page_handles_invalid_mic_id(client, app_context):
    """Test that the config page handles invalid MIC_DEVICE_ID."""
    with open('f:\\Asystent\\config.json', 'w') as f:
        json.dump(SAMPLE_CONFIG, f)

    response = client.post(url_for('config'), data={
        **SAMPLE_CONFIG,
        "MIC_DEVICE_ID": "not_an_integer", # Invalid value
         # Ensure all boolean fields that might be missing from form post are included
        "USE_WHISPER_FOR_COMMAND": "True" if SAMPLE_CONFIG["USE_WHISPER_FOR_COMMAND"] else "",
        "LOW_POWER_MODE": "True" if SAMPLE_CONFIG["LOW_POWER_MODE"] else "",
        "EXIT_WITH_CONSOLE": "True" if SAMPLE_CONFIG["EXIT_WITH_CONSOLE"] else "",
        "DEV_MODE": "True" if SAMPLE_CONFIG["DEV_MODE"] else "",
        "AUTO_LISTEN_AFTER_TTS": "True" if SAMPLE_CONFIG["AUTO_LISTEN_AFTER_TTS"] else "",
    })
    assert response.status_code == 200 # Or appropriate error code/page
    assert b"Invalid MIC_DEVICE_ID" in response.data # Or some other error message

    # Ensure config was not saved with invalid data
    with open('f:\\Asystent\\config.json', 'r') as f:
        current_config = json.load(f)
    assert current_config["MIC_DEVICE_ID"] == SAMPLE_CONFIG["MIC_DEVICE_ID"]

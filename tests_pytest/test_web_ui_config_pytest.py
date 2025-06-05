import pytest
from flask import url_for, session, get_flashed_messages
from unittest.mock import patch, MagicMock
import json
import os
from config import DEFAULT_CONFIG # Add DEFAULT_CONFIG

# Ensure the app and its configurations are loaded correctly for tests
# This might involve setting up a test app context if not already handled by fixtures

# Assuming SAMPLE_CONFIG and CONFIG_FILE_PATH are defined appropriately for testing
# If they are in conftest.py or a shared utility, ensure they are accessible here.
# For now, let's define them if they are simple, or mock their usage.

# If CONFIG_FILE_PATH is determined dynamically, ensure it points to a test-specific file
CONFIG_FILE_PATH = "f:/Asystent/web_ui/test_config.json" # Example path for test config
SAMPLE_CONFIG = {
    "WEB_UI_USERNAME": "testadmin",
    "WEB_UI_PASSWORD": "testpassword",
    "API_KEY_OPENAI": "test_key_openai",
    "ASSISTANT_NAME": "TestBot",
    # Add other necessary minimal config fields
}

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    # This import should be here to avoid circular dependencies or premature app loading
    from web_ui.app import create_app 
    # Create a dummy queue for testing if the real one is not needed or available
    # from multiprocessing import Queue
    # test_queue = Queue()
    # application = create_app(queue=test_queue)
    application = create_app() # Assuming create_app can handle None queue or has a default
    application.config.update({
        "TESTING": True,
        "SECRET_KEY": "test_secret_key", # Consistent secret key for session handling
        "WTF_CSRF_ENABLED": False, # Disable CSRF for easier testing of form posts
        "SERVER_NAME": "localhost.test" # Necessary for url_for to work in some contexts
    })

    # Create a dummy config file for tests
    os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(SAMPLE_CONFIG, f)

    yield application

    # Clean up the dummy config file
    if os.path.exists(CONFIG_FILE_PATH):
        os.remove(CONFIG_FILE_PATH)

@pytest.fixture
def client(app):
    """A test client for the app."""
    with app.app_context(): # Ensure operations are within app context
        yield app.test_client()


# Helper to log in the client
def login(client, username, password):
    return client.post(url_for('login'), data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

# Helper to log out the client
def logout(client):
    return client.get(url_for('logout'), follow_redirects=True)


def test_config_route_unauthenticated(client):
    """Test that accessing /config without being logged in redirects to login."""
    with client.application.app_context():
        response = client.get(url_for('config'))
        assert response.status_code == 302
        # Assuming response.location is relative like '/login'
        assert response.location == url_for('login', _external=False)

def test_config_route_authenticated(client, mock_load_main_config, mock_get_audio_input_devices):
    mock_load_main_config.return_value = DEFAULT_CONFIG
    mock_get_audio_input_devices.return_value = [("Device 1", 0), ("Device 2", 1)]
    login(client, "testuser", "password")
    response = client.get(url_for('config')) # Corrected: remove 'web.' prefix
    assert response.status_code == 200
    assert b"Konfiguracja" in response.data
    logout(client)

def test_update_config_route_unauthenticated(client):
    """Test that updating config without being logged in redirects to login."""
    with client.application.app_context():
        response = client.post(url_for('config'), data={})
        assert response.status_code == 302
        assert response.location == url_for('login', _external=False)

def test_update_config_route_authenticated(client, mock_load_main_config, mock_save_main_config, mock_get_audio_input_devices):
    mock_load_main_config.return_value = DEFAULT_CONFIG
    mock_get_audio_input_devices.return_value = [("Device 1", 0), ("Device 2", 1)]
    login(client, "testuser", "password")
    
    new_config_data = {
        "OPENAI_API_KEY": "new_api_key",
        "ASSISTANT_NAME": "New Assistant",
        "SELECTED_MODEL": "gpt-4",
        "SELECTED_TTS_MODEL": "tts-new",
        "SELECTED_VOICE": "voice-new",
        "SELECTED_STYLE": "style-new",
        "WAKE_WORD": "hey_new",
        "SELECTED_MIC_DEVICE_ID": "1",  # Ensure this is a string as it comes from form
        "SPEECH_SPEED": "1.2",         # Ensure this is a string
        "AUTO_START_LISTENING": "true", # Boolean field, ensure correct value
        "SEARCH_IN_BROWSER": "false",   # Boolean field
        "SCREENSHOTS_ENABLED": "true",  # Boolean field
        "LOGGING_LEVEL": "DEBUG",
        "MAX_HISTORY_LENGTH": "50",     # Ensure this is a string
        "TEMPERATURE": "0.8",           # Ensure this is a string
        "MAX_TOKENS": "200",            # Ensure this is a string
        "PRESENCE_PENALTY": "0.1",      # Ensure this is a string
        "FREQUENCY_PENALTY": "0.1"      # Ensure this is a string
    }

    response = client.post(url_for('config'), data=new_config_data) # Corrected: remove 'web.' prefix
    assert response.status_code == 200 # Or 302 if redirecting after save
    assert b"Konfiguracja zapisana" in response.data # Or check flash message

    # Assert that save_main_config was called with data converted to correct types
    # This requires knowing how your route processes form data
    # For example, if "SELECTED_MIC_DEVICE_ID" becomes an int:
    expected_saved_config = DEFAULT_CONFIG.copy()
    expected_saved_config.update({
        "OPENAI_API_KEY": "new_api_key",
        "ASSISTANT_NAME": "New Assistant",
        "SELECTED_MODEL": "gpt-4",
        "SELECTED_TTS_MODEL": "tts-new",
        "SELECTED_VOICE": "voice-new",
        "SELECTED_STYLE": "style-new",
        "WAKE_WORD": "hey_new",
        "SELECTED_MIC_DEVICE_ID": 1, # Converted to int
        "SPEECH_SPEED": 1.2,        # Converted to float
        "AUTO_START_LISTENING": True,
        "SEARCH_IN_BROWSER": False,
        "SCREENSHOTS_ENABLED": True,
        "LOGGING_LEVEL": "DEBUG",
        "MAX_HISTORY_LENGTH": 50,   # Converted to int
        "TEMPERATURE": 0.8,         # Converted to float
        "MAX_TOKENS": 200,          # Converted to int
        "PRESENCE_PENALTY": 0.1,    # Converted to float
        "FREQUENCY_PENALTY": 0.1    # Converted to float
    })
    # The actual call to save_main_config might have a slightly different structure
    # depending on how the route processes the form. Inspect the route if this fails.
    mock_save_main_config.assert_called_once()
    args, _ = mock_save_main_config.call_args
    assert args[0] == expected_saved_config
    logout(client)

@pytest.fixture
def mock_load_main_config():
    with patch('web_ui.routes.web_routes.load_main_config', new_callable=MagicMock) as mock:
        yield mock

@pytest.fixture
def mock_save_main_config():
    with patch('web_ui.routes.web_routes.save_main_config', new_callable=MagicMock) as mock:
        yield mock

@pytest.fixture
def mock_get_audio_input_devices():
    with patch('web_ui.routes.web_routes.get_audio_input_devices', new_callable=MagicMock) as mock:
        yield mock

# Remove or adapt old tests that are now covered or made redundant by the new structure
# For example, the original test_config_page_loads_correctly, etc. might need to be refactored
# to use the new login helpers and app context. 

# Example of adapting an old test (if still needed):
@patch('web_ui.routes.web_routes.load_main_config')
@patch('web_ui.routes.web_routes.get_audio_input_devices')
@patch('web_ui.routes.web_routes.User.get_by_username') # Mock user lookup
def test_config_page_loads_old_style_adapted(mock_user_get, mock_get_audio, mock_load_config, client):
    """Test that the config page loads correctly (adapted from old test)."""
    # Setup mocks
    mock_load_config.return_value = DEFAULT_CONFIG
    mock_get_audio.return_value = [("Built-in Microphone", 0), ("External USB Mic", 1)]
    
    # Mock user for login
    mock_user = MagicMock()
    mock_user.check_password.return_value = True # Simulate correct password
    mock_user_get.return_value = mock_user

    login_response = login(client, "testuser", "password")
    # Check if login was successful, e.g., by checking session or response after login
    # For example, if login sets a user_id in session:
    with client.session_transaction() as sess:
        assert sess.get('user_id') is not None, "Login failed, user_id not in session."

    response = client.get(url_for('config')) # Corrected: remove 'web.' prefix

    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Login might have failed."
    assert b"Konfiguracja Asystenta" in response.data
    assert b"OpenAI API Key" in response.data
    assert b"Built-in Microphone" in response.data 

    logout(client) # Assuming you have a logout function

import json
from unittest.mock import patch, MagicMock
from web_ui.app import create_app


def test_status_endpoint_structure():
    dummy = MagicMock()
    dummy.is_listening = False
    dummy.is_speaking = True
    dummy.last_tts_text = "Hello"

    with patch('web_ui.routes.api_routes.get_assistant_instance', return_value=dummy), \
         patch('web_ui.routes.api_routes.load_main_config', return_value={'WAKE_WORD': 'gaja', 'MIC_DEVICE_ID': 0}):
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
        resp = client.get('/api/status')
        assert resp.status_code == 200
        data = resp.get_json()
        for key in ['status', 'wake_word', 'stt_engine', 'mic_device_id', 'is_listening', 'is_speaking', 'text']:
            assert key in data

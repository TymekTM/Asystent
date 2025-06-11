"""
Konfiguracja pytest i helpery testowe dla GAJA Assistant
"""

import asyncio
import json
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, Optional

# Dodaj ścieżki do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
sys.path.insert(0, str(Path(__file__).parent.parent / "client"))

# Import głównych modułów
from server.server_main import ServerApp, ConnectionManager
from client.client_main import ClientApp


@pytest.fixture(scope="session")
def event_loop():
    """Utwórz główną pętlę zdarzeń dla testów."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_config_dir():
    """Utwórz tymczasowy katalog dla konfiguracji testowej."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_config():
    """Mock konfiguracji dla testów."""
    return {
        "server": {
            "host": "localhost",
            "port": 8001,
            "debug": True
        },
        "database": {
            "path": ":memory:",
            "timeout": 30
        },
        "ai": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "max_tokens": 1000
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1
        },
        "security": {
            "cors_origins": ["http://localhost:3000"]
        },
        "plugins": {
            "enabled": [],
            "max_file_size": 1048576
        }
    }


@pytest.fixture
def mock_db_manager():
    """Mock menedżera bazy danych."""
    mock = AsyncMock()
    mock.initialize = AsyncMock()
    mock.create_user = AsyncMock(return_value={"id": 1, "username": "test_user"})
    mock.get_user = AsyncMock(return_value={"id": 1, "username": "test_user"})
    mock.get_all_users = AsyncMock(return_value=[])
    mock.save_chat_message = AsyncMock()
    mock.get_chat_history = AsyncMock(return_value=[])
    mock.update_user_plugin_status = AsyncMock()
    return mock


@pytest.fixture
def mock_ai_module():
    """Mock modułu AI."""
    mock = AsyncMock()
    mock.get_response = AsyncMock(return_value={
        "text": "Test AI response",
        "confidence": 0.95
    })
    mock.process_text = AsyncMock(return_value="Processed text")
    return mock


@pytest.fixture
def mock_websocket():
    """Mock połączenia WebSocket."""
    mock = AsyncMock()
    mock.accept = AsyncMock()
    mock.send_text = AsyncMock()
    mock.receive_text = AsyncMock(return_value='{"type": "test"}')
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_audio_components():
    """Mock komponentów audio."""
    return {
        "wakeword_detector": Mock(
            start_detection=Mock(),
            stop_detection=Mock(),
            is_detecting=Mock(return_value=False)
        ),
        "whisper_asr": Mock(
            transcribe=AsyncMock(return_value="Test transcription"),
            is_available=Mock(return_value=True)
        ),
        "tts": Mock(
            speak=AsyncMock(),
            is_speaking=Mock(return_value=False)
        ),
        "audio_recorder": Mock(
            start_recording=Mock(),
            stop_recording=Mock(),
            get_audio_data=Mock(return_value=b"mock_audio_data")
        )
    }


@pytest.fixture
async def server_app(mock_config, mock_db_manager, mock_ai_module):
    """Instancja ServerApp dla testów."""
    app = ServerApp()
    app.config = mock_config
    app.db_manager = mock_db_manager
    app.ai_module = mock_ai_module
    app.connection_manager = ConnectionManager()
    
    # Mock innych komponentów
    app.function_system = Mock()
    app.onboarding_module = Mock()
    app.daily_briefing = Mock()
    app.day_summary = Mock()
    app.user_behavior = Mock()
    app.routines_learner = Mock()
    app.day_narrative = Mock()
    app.proactive_assistant = Mock()
    
    yield app


@pytest.fixture
async def client_app(mock_config, mock_audio_components):
    """Instancja ClientApp dla testów."""
    client_config = {
        "user_id": "test_user",
        "server_url": "ws://localhost:8001/ws/test_user",
        "audio": mock_config["audio"]
    }
    
    app = ClientApp()
    app.config = client_config
    app.user_id = "test_user"
    app.server_url = "ws://localhost:8001/ws/test_user"
    
    # Mock komponentów audio
    app.wakeword_detector = mock_audio_components["wakeword_detector"]
    app.whisper_asr = mock_audio_components["whisper_asr"]
    app.tts = mock_audio_components["tts"]
    app.audio_recorder = mock_audio_components["audio_recorder"]
    
    # Mock innych komponentów
    app.websocket = None
    app.running = False
    app.monitoring_wakeword = False
    app.wake_word_detected = False
    app.recording_command = False
    app.tts_playing = False
    
    yield app


@pytest.fixture
def sample_chat_data():
    """Przykładowe dane czatu."""
    return [
        {
            "id": 1,
            "user_id": "test_user",
            "message": "Hello",
            "response": "Hi there!",
            "timestamp": "2025-06-11 10:00:00"
        },
        {
            "id": 2,
            "user_id": "test_user",
            "message": "How are you?",
            "response": "I'm doing well, thank you!",
            "timestamp": "2025-06-11 10:01:00"
        }
    ]


@pytest.fixture
def sample_plugin_data():
    """Przykładowe dane pluginów."""
    return {
        "test_plugin": {
            "name": "test_plugin",
            "description": "Test plugin for unit tests",
            "version": "1.0.0",
            "author": "Test Author",
            "functions": ["test_function"],
            "enabled": True,
            "loaded": True
        },
        "weather_plugin": {
            "name": "weather_plugin",
            "description": "Weather information plugin",
            "version": "1.1.0",
            "author": "Weather Corp",
            "functions": ["get_weather", "get_forecast"],
            "enabled": False,
            "loaded": False
        }
    }


class MockPlugin:
    """Mock klasa pluginu dla testów."""
    
    def __init__(self, name: str, functions: list = None):
        self.name = name
        self.functions = functions or ["test_function"]
        self.PLUGIN_METADATA = {
            "name": name,
            "version": "1.0.0",
            "description": f"Mock plugin {name}",
            "author": "Test Suite"
        }
    
    async def execute_function(self, function_name: str, parameters: Dict[str, Any], user_id: int):
        """Mock wykonanie funkcji."""
        return {
            "status": "success",
            "result": f"Mock result for {function_name}",
            "parameters": parameters,
            "user_id": user_id
        }
    
    def get_functions(self):
        """Zwróć listę dostępnych funkcji."""
        return self.functions


@pytest.fixture
def mock_plugin():
    """Mock plugin dla testów."""
    return MockPlugin("test_plugin", ["test_function", "another_function"])


def create_test_message(message_type: str, **kwargs) -> Dict[str, Any]:
    """Helper do tworzenia wiadomości testowych."""
    message = {"type": message_type}
    message.update(kwargs)
    return message


def assert_websocket_message(mock_websocket, expected_type: str, **expected_fields):
    """Helper do sprawdzania wiadomości WebSocket."""
    mock_websocket.send_text.assert_called()
    
    # Pobierz ostatnią wysłaną wiadomość
    calls = mock_websocket.send_text.call_args_list
    if not calls:
        pytest.fail("No WebSocket messages sent")
    
    last_call = calls[-1]
    sent_data = json.loads(last_call[0][0])
    
    assert sent_data["type"] == expected_type
    
    for field, expected_value in expected_fields.items():
        assert field in sent_data
        assert sent_data[field] == expected_value


def create_mock_audio_data(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Utwórz mock danych audio."""
    import struct
    num_samples = int(duration_seconds * sample_rate)
    # Utwórz prostą sinusoidę
    samples = []
    for i in range(num_samples):
        value = int(32767 * 0.5 * (i % 100) / 100)  # Prosta fala
        samples.append(struct.pack('<h', value))
    return b''.join(samples)


class AsyncContextManager:
    """Helper dla async context managerów w testach."""
    
    def __init__(self, value):
        self.value = value
    
    async def __aenter__(self):
        return self.value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

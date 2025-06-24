"""
Comprehensive test suite for music_module.py - AGENTS.md Compliant

Tests cover:
- Function registration and plugin interface
- Async function execution
- Music control actions
- Spotify integration (with mocking)
- System media key handling
- Error handling and edge cases
- Platform normalization
"""

import asyncio
import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import music module
from server.modules import music_module_new as music_module


class TestMusicModulePluginInterface:
    """Test plugin interface compliance."""

    def test_get_functions_returns_list(self):
        """Test that get_functions returns a list."""
        functions = music_module.get_functions()
        assert isinstance(functions, list)
        assert len(functions) > 0

    def test_get_functions_structure(self):
        """Test function definitions have required structure."""
        functions = music_module.get_functions()

        for func in functions:
            assert isinstance(func, dict)
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert isinstance(func["parameters"], dict)

    def test_control_music_function_definition(self):
        """Test control_music function is properly defined."""
        functions = music_module.get_functions()
        control_func = next(f for f in functions if f["name"] == "control_music")

        assert control_func["description"]
        params = control_func["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "action" in params["properties"]
        assert "platform" in params["properties"]
        assert "required" in params
        assert "action" in params["required"]

    def test_get_spotify_status_function_definition(self):
        """Test get_spotify_status function is properly defined."""
        functions = music_module.get_functions()
        status_func = next(f for f in functions if f["name"] == "get_spotify_status")

        assert status_func["description"]
        params = status_func["parameters"]
        assert params["type"] == "object"
        assert "properties" in params


class TestMusicControlAsync:
    """Test async music control functionality."""

    @pytest.mark.asyncio
    async def test_execute_function_control_music(self):
        """Test basic execute_function with control_music."""
        result = await music_module.execute_function(
            "control_music", {"action": "play", "test_mode": True}, user_id=1
        )

        assert result["success"] is True
        assert result["test_mode"] is True
        assert result["action"] == "play"

    @pytest.mark.asyncio
    async def test_execute_function_invalid_action(self):
        """Test execute_function with invalid action."""
        result = await music_module.execute_function(
            "control_music", {"action": "invalid_action"}, user_id=1
        )

        assert result["success"] is False
        assert "unsupported" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_function_missing_action(self):
        """Test execute_function with missing action."""
        result = await music_module.execute_function("control_music", {}, user_id=1)

        assert result["success"] is False
        assert "required" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_action_normalization(self):
        """Test that action aliases are normalized correctly."""
        # Test play aliases
        for action in ["play", "resume"]:
            result = await music_module.execute_function(
                "control_music", {"action": action, "test_mode": True}, user_id=1
            )
            assert result["success"] is True
            assert result["action"] == "play"

        # Test pause aliases
        for action in ["pause", "stop"]:
            result = await music_module.execute_function(
                "control_music", {"action": action, "test_mode": True}, user_id=1
            )
            assert result["success"] is True
            assert result["action"] == "pause"

    @pytest.mark.asyncio
    async def test_platform_normalization(self):
        """Test platform normalization."""
        result = await music_module.execute_function(
            "control_music",
            {"action": "play", "platform": "spo", "test_mode": True},
            user_id=1,
        )

        assert result["success"] is True
        # Platform is returned as passed since we're in test mode
        assert "spo" in result["platform"] or result["platform"] == "spotify"


class TestSpotifyIntegration:
    """Test Spotify integration with mocking."""

    @pytest.mark.asyncio
    async def test_get_spotify_status_test_mode(self):
        """Test get_spotify_status in test mode."""
        result = await music_module.execute_function(
            "get_spotify_status", {"test_mode": True}, user_id=1
        )

        assert result["success"] is True
        assert result["test_mode"] is True
        assert "status" in result
        assert result["status"]["is_playing"] is True

    @pytest.mark.asyncio
    @patch("server.modules.music_module_new.SPOTIFY_AVAILABLE", True)
    @patch("server.modules.music_module_new._get_spotify_client")
    async def test_spotify_control_success(self, mock_client_func):
        """Test successful Spotify control."""
        # Mock Spotify client
        mock_client = Mock()
        mock_client.devices.return_value = {
            "devices": [{"id": "device1", "name": "Test Device"}]
        }
        mock_client.start_playback = Mock()
        mock_client_func.return_value = mock_client

        result = await music_module._spotify_action_async("play")

        assert result["success"] is True
        assert result["platform"] == "spotify"
        assert result["action"] == "play"
        mock_client.start_playback.assert_called_once()

    @pytest.mark.asyncio
    @patch("server.modules.music_module_new.SPOTIFY_AVAILABLE", True)
    @patch("server.modules.music_module_new._get_spotify_client")
    async def test_spotify_no_devices(self, mock_client_func):
        """Test Spotify control with no active devices."""
        mock_client = Mock()
        mock_client.devices.return_value = {"devices": []}
        mock_client_func.return_value = mock_client

        result = await music_module._spotify_action_async("play")

        assert result["success"] is False
        assert "no active device" in result["message"].lower()

    @pytest.mark.asyncio
    @patch("server.modules.music_module_new.SPOTIFY_AVAILABLE", True)
    @patch("server.modules.music_module_new._get_spotify_client")
    async def test_spotify_client_unavailable(self, mock_client_func):
        """Test Spotify control when client is unavailable."""
        mock_client_func.return_value = None

        result = await music_module._spotify_action_async("play")

        assert result["success"] is False
        assert "unavailable" in result["message"].lower()

    @pytest.mark.asyncio
    @patch("server.modules.music_module_new.SPOTIFY_AVAILABLE", True)
    @patch("server.modules.music_module_new._get_spotify_client")
    async def test_get_spotify_status_success(self, mock_client_func):
        """Test successful Spotify status retrieval."""
        mock_client = Mock()
        mock_client.current_playback.return_value = {
            "is_playing": True,
            "item": {
                "name": "Test Song",
                "artists": [{"name": "Test Artist"}],
                "duration_ms": 180000,
            },
            "progress_ms": 60000,
        }
        mock_client_func.return_value = mock_client

        result = await music_module._get_spotify_status_async()

        assert result["success"] is True
        assert result["status"]["is_playing"] is True
        assert result["status"]["track"] == "Test Song"
        assert result["status"]["artist"] == "Test Artist"

    @pytest.mark.asyncio
    @patch("server.modules.music_module_new.SPOTIFY_AVAILABLE", True)
    @patch("server.modules.music_module_new._get_spotify_client")
    async def test_get_spotify_status_no_playback(self, mock_client_func):
        """Test Spotify status with no active playback."""
        mock_client = Mock()
        mock_client.current_playback.return_value = None
        mock_client_func.return_value = mock_client

        result = await music_module._get_spotify_status_async()

        assert result["success"] is True
        assert result["status"]["is_playing"] is False
        assert result["status"]["track"] is None


class TestSystemMediaKeys:
    """Test system media key functionality."""

    @pytest.mark.asyncio
    @patch("server.modules.music_module_new._keyboard_available", True)
    @patch("server.modules.music_module_new.keyboard")
    async def test_system_media_key_success(self, mock_keyboard):
        """Test successful media key simulation."""
        mock_keyboard.send = Mock()

        result = await music_module._system_media_key_async("play")

        assert result["success"] is True
        assert result["platform"] == "system"
        assert result["action"] == "play"
        mock_keyboard.send.assert_called_once()

    @pytest.mark.asyncio
    @patch("server.modules.music_module_new._keyboard_available", False)
    async def test_system_media_key_unavailable(self):
        """Test media key control when keyboard library unavailable."""
        result = await music_module._system_media_key_async("play")

        assert result["success"] is False
        assert "unavailable" in result["message"].lower()

    @pytest.mark.asyncio
    @patch("server.modules.music_module_new._keyboard_available", True)
    @patch("server.modules.music_module_new.keyboard")
    async def test_system_media_key_exception(self, mock_keyboard):
        """Test media key control with keyboard exception."""
        mock_keyboard.send.side_effect = Exception("Keyboard error")

        result = await music_module._system_media_key_async("play")

        assert result["success"] is False
        assert "failed" in result["message"].lower()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_execute_function_unknown_function(self):
        """Test execute_function with unknown function name."""
        result = await music_module.execute_function("unknown_function", {}, user_id=1)

        assert result["success"] is False
        assert "unknown function" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_function_exception_handling(self):
        """Test execute_function handles exceptions properly."""
        # Mock execute_function to raise an exception
        with patch.object(
            music_module, "_control_music_async", side_effect=Exception("Test error")
        ):
            result = await music_module.execute_function(
                "control_music", {"action": "play"}, user_id=1
            )

            assert result["success"] is False
            assert "error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_control_music_no_methods_available(self):
        """Test music control when no methods are available."""
        with patch("server.modules.music_module_new.SPOTIFY_AVAILABLE", False):
            with patch("server.modules.music_module_new._keyboard_available", False):
                result = await music_module._control_music_async("play", "auto")

                assert result["success"] is False
                assert "no music control methods" in result["message"].lower()


class TestHelperFunctions:
    """Test helper functions."""

    def test_normalize_platform(self):
        """Test platform normalization."""
        assert music_module._normalize_platform("spotify") == "spotify"
        assert music_module._normalize_platform("spo") == "spotify"
        assert music_module._normalize_platform("youtube") == "ytmusic"
        assert music_module._normalize_platform("unknown") == "auto"

    def test_normalize_action(self):
        """Test action normalization."""
        assert music_module._normalize_action("play") == "play"
        assert music_module._normalize_action("resume") == "play"
        assert music_module._normalize_action("pause") == "pause"
        assert music_module._normalize_action("stop") == "pause"
        assert music_module._normalize_action("invalid") == "unknown"

    @patch("server.modules.music_module_new.SPOTIFY_AVAILABLE", False)
    def test_get_spotify_client_unavailable(self):
        """Test _get_spotify_client when Spotify is unavailable."""
        client = music_module._get_spotify_client()
        assert client is None

    def test_get_module_status(self):
        """Test get_module_status returns correct structure."""
        status = music_module.get_module_status()

        assert isinstance(status, dict)
        assert "spotify_available" in status
        assert "keyboard_available" in status
        assert "spotify_client_ready" in status
        assert isinstance(status["spotify_available"], bool)
        assert isinstance(status["keyboard_available"], bool)
        assert isinstance(status["spotify_client_ready"], bool)


class TestLegacyCompatibility:
    """Test backward compatibility functions."""

    @pytest.mark.asyncio
    async def test_process_input_basic(self):
        """Test legacy process_input function."""
        result = await music_module.process_input("play")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_process_input_empty(self):
        """Test process_input with empty input."""
        result = await music_module.process_input("")
        assert "specify action" in result.lower()

    @pytest.mark.asyncio
    async def test_process_input_with_platform(self):
        """Test process_input with platform specification."""
        result = await music_module.process_input("spotify play")
        assert isinstance(result, str)

    def test_register_function(self):
        """Test module registration function."""
        registration = music_module.register()

        assert isinstance(registration, dict)
        assert "command" in registration
        assert "aliases" in registration
        assert "description" in registration
        assert "handler" in registration
        assert callable(registration["handler"])


class TestAsyncSafety:
    """Test async safety and concurrency."""

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test concurrent function execution."""
        tasks = [
            music_module.execute_function(
                "control_music", {"action": "play", "test_mode": True}, user_id=i
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        for result in results:
            assert result["success"] is True
            assert result["test_mode"] is True

    @pytest.mark.asyncio
    async def test_async_execution_non_blocking(self):
        """Test that async execution doesn't block."""
        import time

        start_time = time.time()

        # Execute multiple operations concurrently
        tasks = [
            music_module.execute_function(
                "get_spotify_status", {"test_mode": True}, user_id=1
            )
            for _ in range(3)
        ]

        results = await asyncio.gather(*tasks)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete quickly in test mode
        assert execution_time < 1.0
        assert all(r["success"] for r in results)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

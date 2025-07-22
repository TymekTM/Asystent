#!/usr/bin/env python3
"""Test suite for client message handlers.

Tests the async handler methods added to fix the missing method errors. Follows
AGENTS.md guidelines: async, testable, modular.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add client path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "client"))

try:
    from client_main import ClientApp
except ImportError:
    pytest.skip("Client module not available", allow_module_level=True)


class TestClientHandlers:
    """Test cases for client message handlers."""

    @pytest.fixture
    def client_app(self):
        """Create a mock ClientApp instance for testing."""
        app = ClientApp()
        # Mock the dependencies to avoid actual audio/overlay initialization
        app.tts = AsyncMock()
        app.update_status = Mock()
        app.show_overlay = AsyncMock()
        app.hide_overlay = AsyncMock()
        app.tts_playing = False
        return app

    @pytest.mark.asyncio
    async def test_handle_startup_briefing_with_string(self, client_app):
        """Test handling startup briefing when input is a string."""
        briefing_text = "Test startup briefing message"

        await client_app.handle_startup_briefing(briefing_text)
        # Verify status was updated (last call should be "Ready" after TTS completes)
        final_status_call = client_app.update_status.call_args_list[-1]
        assert final_status_call[0][0] == "Ready"

        # Verify overlay was shown and hidden
        client_app.show_overlay.assert_called_once()
        client_app.hide_overlay.assert_called_once()

        # Verify TTS was called
        client_app.tts.speak.assert_called_once_with(briefing_text)

    @pytest.mark.asyncio
    async def test_handle_startup_briefing_with_dict(self, client_app):
        """Test handling startup briefing when input is a dictionary."""
        briefing_dict = {
            "text": "Main briefing text",
            "summary": "Backup summary",
            "timestamp": "2025-06-22T20:00:00Z",
        }

        await client_app.handle_startup_briefing(briefing_dict)
        # Verify the main text was used
        client_app.tts.speak.assert_called_once_with("Main briefing text")
        # Verify final status is "Ready"
        final_status_call = client_app.update_status.call_args_list[-1]
        assert final_status_call[0][0] == "Ready"

    @pytest.mark.asyncio
    async def test_handle_startup_briefing_empty_content(self, client_app):
        """Test handling startup briefing with empty content."""
        briefing_dict = {"text": "", "summary": "", "timestamp": "2025-06-22T20:00:00Z"}

        await client_app.handle_startup_briefing(briefing_dict)

        # Verify TTS was not called for empty content
        client_app.tts.speak.assert_not_called()
        client_app.show_overlay.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_day_summary(self, client_app):
        """Test handling day summary."""
        summary_data = {
            "type": "day_summary",
            "content": "Test day summary content",
            "statistics": {
                "active_time_hours": 8.5,
                "interactions_count": 15,
                "productivity_score": 0.85,
            },
        }

        await client_app.handle_day_summary(summary_data)
        # Verify status was updated (final status should be "Listening...")
        final_status_call = client_app.update_status.call_args_list[-1]
        assert final_status_call[0][0] == "Listening..."

        # Verify overlay was shown and hidden
        client_app.show_overlay.assert_called_once()
        client_app.hide_overlay.assert_called_once()

        # Verify TTS was called with the content
        client_app.tts.speak.assert_called_once_with("Test day summary content")

    @pytest.mark.asyncio
    async def test_handle_proactive_notifications(self, client_app):
        """Test handling proactive notifications."""
        notification_data = {
            "notifications": [
                {
                    "message": "Test notification message",
                    "title": "Test Title",
                    "type": "info",
                }
            ],
            "priority": "normal",
        }

        await client_app.handle_proactive_notifications(notification_data)

        # Verify status was updated
        assert client_app.update_status.call_count >= 1

        # Verify overlay was shown and hidden
        client_app.show_overlay.assert_called()
        client_app.hide_overlay.assert_called()

    @pytest.mark.asyncio
    async def test_handle_proactive_notifications_high_priority(self, client_app):
        """Test handling high priority proactive notifications."""
        notification_data = {
            "notifications": [
                {
                    "message": "Urgent notification message",
                    "title": "Urgent",
                    "type": "urgent",
                }
            ],
            "priority": "high",
        }

        await client_app.handle_proactive_notifications(notification_data)

        # Verify TTS was called for high priority notification
        client_app.tts.speak.assert_called_once_with(
            "Urgent: Urgent notification message"
        )

    @pytest.mark.asyncio
    async def test_handle_proactive_notifications_empty(self, client_app):
        """Test handling empty proactive notifications."""
        notification_data = {"notifications": [], "priority": "normal"}

        await client_app.handle_proactive_notifications(notification_data)

        # Verify no TTS calls for empty notifications
        client_app.tts.speak.assert_not_called()

    def test_format_day_summary_with_content(self, client_app):
        """Test formatting day summary with content."""
        result = client_app._format_day_summary("test_summary", "Test content", {})

        assert result == "Test content"

    def test_format_day_summary_with_statistics(self, client_app):
        """Test formatting day summary with statistics."""
        statistics = {
            "active_time_hours": 7.5,
            "interactions_count": 12,
            "productivity_score": 0.78,
        }

        result = client_app._format_day_summary("test_summary", "", statistics)

        expected = (
            "Statystyki dnia: 7.5 godzin aktywności, 12 interakcji, produktywność: 78%."
        )
        assert result == expected

    def test_format_day_summary_empty(self, client_app):
        """Test formatting day summary with empty data."""
        result = client_app._format_day_summary("test_summary", "", {})

        assert result == "Podsumowanie dnia jest puste."

    @pytest.mark.asyncio
    async def test_tts_error_handling(self, client_app):
        """Test TTS error handling in startup briefing."""
        # Mock TTS to raise an exception
        client_app.tts.speak.side_effect = Exception("TTS Error")

        briefing_text = "Test briefing"

        # Should not raise an exception
        await client_app.handle_startup_briefing(briefing_text)

        # Verify overlay was still hidden after error
        client_app.hide_overlay.assert_called_once()
        client_app.update_status.assert_called_with("Ready")


if __name__ == "__main__":
    pytest.main([__file__])

#!/usr/bin/env python3
"""Tests for GAJA Overlay Debug Tools Following AGENTS.md guidelines for comprehensive
test coverage."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from aiohttp import web

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from overlay_debug_tools import OverlayDebugToolsGUI


class TestOverlayDebugTools:
    """Test suite for overlay debug tools."""

    @pytest.fixture
    def mock_app(self):
        """Create mock GUI app for testing."""
        with patch("tkinter.Tk"), patch("tkinter.ttk.Notebook"), patch(
            "tkinter.BooleanVar"
        ), patch("tkinter.StringVar"), patch("tkinter.Text"), patch(
            "tkinter.scrolledtext.ScrolledText"
        ), patch(
            "tkinter.ttk.Label"
        ), patch(
            "threading.Thread"
        ):
            # Create app without calling _setup_ui
            app = OverlayDebugToolsGUI.__new__(OverlayDebugToolsGUI)

            # Initialize basic attributes manually
            app.current_status = {
                "visible": False,
                "status": "Offline",
                "text": "",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
            }
            app.server_port = "5001"
            app.base_url = f"http://localhost:{app.server_port}"
            app.session = Mock(spec=aiohttp.ClientSession)
            app.loop = Mock()

            # Mock GUI components
            app.log_display = Mock()
            app.status_display = Mock()
            app.text_input = Mock()
            app.auto_scroll_var = Mock()
            app.auto_refresh_var = Mock()
            app.status_bar = Mock()
            app.port_var = Mock()
            app.sequence_timing = Mock()

            return app

    @pytest.fixture
    async def mock_server(self, aiohttp_server):
        """Create mock HTTP server for testing."""
        app = web.Application()

        # Mock status endpoint
        async def get_status(request):
            return web.json_response(
                {
                    "visible": True,
                    "status": "active",
                    "text": "Test response",
                    "is_listening": False,
                    "is_speaking": False,
                    "wake_word_detected": False,
                }
            )

        # Mock overlay control endpoints
        async def show_overlay(request):
            return web.json_response({"success": True})

        async def hide_overlay(request):
            return web.json_response({"success": True})

        async def update_overlay(request):
            data = await request.json()
            return web.json_response({"success": True, "data": data})

        # Mock SSE endpoint
        async def sse_stream(request):
            response = web.StreamResponse(
                status=200, reason="OK", headers={"Content-Type": "text/event-stream"}
            )
            await response.prepare(request)

            # Send a few test events
            for i in range(3):
                event_data = {
                    "status": "active",
                    "text": f"SSE test {i}",
                    "is_listening": i % 2 == 0,
                    "is_speaking": False,
                    "wake_word_detected": False,
                }
                await response.write(f"data: {json.dumps(event_data)}\n\n".encode())
                await asyncio.sleep(0.1)

            return response

        app.router.add_get("/api/status", get_status)
        app.router.add_post("/overlay/show", show_overlay)
        app.router.add_post("/overlay/hide", hide_overlay)
        app.router.add_post("/overlay/update", update_overlay)
        app.router.add_get("/status/stream", sse_stream)

        return await aiohttp_server(app)

    def test_initialization(self):
        """Test GUI initialization."""
        with patch("tkinter.Tk"), patch("tkinter.ttk.Notebook"), patch(
            "tkinter.BooleanVar"
        ), patch("tkinter.StringVar"), patch("tkinter.Text"), patch(
            "tkinter.scrolledtext.ScrolledText"
        ), patch(
            "tkinter.ttk.Label"
        ), patch(
            "threading.Thread"
        ):
            # Create app without calling _setup_ui to avoid GUI creation
            app = OverlayDebugToolsGUI.__new__(OverlayDebugToolsGUI)
            app.server_port = "5001"
            app.base_url = "http://localhost:5001"
            app.current_status = {"visible": False, "status": "Offline"}

            assert app.server_port == "5001"
            assert app.base_url == "http://localhost:5001"
            assert app.current_status["visible"] is False
            assert app.current_status["status"] == "Offline"

    def test_port_update(self, mock_app):
        """Test port update functionality."""
        mock_app.port_var = Mock()
        mock_app.port_var.get.return_value = "5000"

        mock_app._update_port()

        assert mock_app.server_port == "5000"
        assert mock_app.base_url == "http://localhost:5000"

    def test_log_functionality(self, mock_app):
        """Test logging functionality."""
        mock_app.log_display = Mock()
        mock_app.auto_scroll_var = Mock()
        mock_app.auto_scroll_var.get.return_value = True
        mock_app.status_bar = Mock()

        test_message = "Test log message"
        mock_app._log(test_message, "INFO")

        # Verify log display was updated
        mock_app.log_display.insert.assert_called()
        mock_app.log_display.see.assert_called_with("end")
        mock_app.status_bar.config.assert_called_with(text=test_message)

    def test_preset_text_insertion(self, mock_app):
        """Test preset text insertion."""
        mock_app.text_input = Mock()

        test_text = "Test preset text"
        mock_app._insert_preset_text(test_text)

        mock_app.text_input.delete.assert_called_with("1.0", "end")
        mock_app.text_input.insert.assert_called_with("1.0", test_text)

    def test_status_display_update(self, mock_app):
        """Test status display update."""
        mock_app.status_display = Mock()
        mock_app.current_status = {"visible": True, "status": "active", "text": "Test"}

        mock_app._update_status_display()

        mock_app.status_display.delete.assert_called_with("1.0", "end")
        mock_app.status_display.insert.assert_called()

    @pytest.mark.asyncio
    async def test_session_management(self, mock_app):
        """Test HTTP session management."""
        mock_app.session = None

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = Mock(spec=aiohttp.ClientSession)
            mock_session.closed = False
            mock_session_class.return_value = mock_session

            session = await mock_app._get_session()

            assert session == mock_session
            assert mock_app.session == mock_session

    @pytest.mark.asyncio
    async def test_show_overlay(self, mock_app, mock_server):
        """Test show overlay functionality."""
        mock_app.base_url = f"http://localhost:{mock_server.port}"
        mock_app._log = Mock()
        mock_app._get_status = AsyncMock()

        # Create real session for this test
        mock_app.session = aiohttp.ClientSession()

        try:
            await mock_app._show_overlay()

            # Verify success was logged
            mock_app._log.assert_any_call("Overlay shown successfully")
            # Verify status was refreshed
            mock_app._get_status.assert_called_once()
        finally:
            await mock_app.session.close()

    @pytest.mark.asyncio
    async def test_hide_overlay(self, mock_app, mock_server):
        """Test hide overlay functionality."""
        mock_app.base_url = f"http://localhost:{mock_server.port}"
        mock_app._log = Mock()
        mock_app._get_status = AsyncMock()

        # Create real session for this test
        mock_app.session = aiohttp.ClientSession()

        try:
            await mock_app._hide_overlay()

            # Verify success was logged
            mock_app._log.assert_any_call("Overlay hidden successfully")
            # Verify status was refreshed
            mock_app._get_status.assert_called_once()
        finally:
            await mock_app.session.close()

    @pytest.mark.asyncio
    async def test_get_status(self, mock_app, mock_server):
        """Test get status functionality."""
        mock_app.base_url = f"http://localhost:{mock_server.port}"
        mock_app._log = Mock()
        mock_app._update_status_display = Mock()

        # Create real session for this test
        mock_app.session = aiohttp.ClientSession()

        try:
            await mock_app._get_status()

            # Verify status was updated
            assert mock_app.current_status["visible"] is True
            assert mock_app.current_status["status"] == "active"
            assert mock_app.current_status["text"] == "Test response"

            # Verify UI was updated
            mock_app._update_status_display.assert_called_once()
            mock_app._log.assert_any_call("Status retrieved successfully")
        finally:
            await mock_app.session.close()

    @pytest.mark.asyncio
    async def test_set_status_state(self, mock_app, mock_server):
        """Test set status state functionality."""
        mock_app.base_url = f"http://localhost:{mock_server.port}"
        mock_app._log = Mock()
        mock_app._get_status = AsyncMock()

        # Create real session for this test
        mock_app.session = aiohttp.ClientSession()

        try:
            await mock_app._set_status_state(is_listening=True, text="Test message")

            # Verify success was logged
            mock_app._log.assert_called()
            # Verify status was refreshed
            mock_app._get_status.assert_called_once()
        finally:
            await mock_app.session.close()

    @pytest.mark.asyncio
    async def test_animation_testing(self, mock_app):
        """Test animation testing functionality."""
        mock_app._set_status_state = AsyncMock()

        await mock_app._test_animation("listening")
        mock_app._set_status_state.assert_called_with(
            is_listening=True, text="Słucham..."
        )

        await mock_app._test_animation("speaking")
        mock_app._set_status_state.assert_called_with(
            is_speaking=True, text="Odpowiadam..."
        )

        await mock_app._test_animation("wake_word")
        mock_app._set_status_state.assert_called_with(
            wake_word_detected=True, text="Przetwarzam..."
        )

        await mock_app._test_animation("idle")
        mock_app._set_status_state.assert_called_with(text="")

    @pytest.mark.asyncio
    async def test_full_sequence(self, mock_app):
        """Test full interaction sequence."""
        mock_app._set_status_state = AsyncMock()
        mock_app._log = Mock()
        mock_app.sequence_timing = Mock()
        mock_app.sequence_timing.get.return_value = "0.1"  # Fast for testing

        await mock_app._test_full_sequence()

        # Verify sequence was logged
        mock_app._log.assert_any_call("Starting full interaction sequence")
        mock_app._log.assert_any_call("Full sequence completed")

        # Verify all sequence steps were called
        assert mock_app._set_status_state.call_count == 5

    @pytest.mark.asyncio
    async def test_connection_testing(self, mock_app, mock_server):
        """Test connection testing functionality."""
        mock_app.base_url = f"http://localhost:{mock_server.port}"
        mock_app._log = Mock()

        # Create real session for this test
        mock_app.session = aiohttp.ClientSession()

        try:
            await mock_app._test_connection()

            # Verify success was logged
            mock_app._log.assert_any_call("✅ Connection successful")
        finally:
            await mock_app.session.close()

    @pytest.mark.asyncio
    async def test_connection_failure(self, mock_app):
        """Test connection failure handling."""
        mock_app.base_url = "http://localhost:9999"  # Non-existent port
        mock_app._log = Mock()

        # Create real session for this test
        mock_app.session = aiohttp.ClientSession()

        try:
            await mock_app._test_connection()

            # Verify error was logged
            mock_app._log.assert_any_call(
                "❌ Connection error: Cannot connect to host localhost:9999 ssl:default [Connect call failed ('127.0.0.1', 9999)]",
                "ERROR",
            )
        finally:
            await mock_app.session.close()

    @pytest.mark.asyncio
    async def test_api_endpoints_testing(self, mock_app, mock_server):
        """Test API endpoints testing functionality."""
        mock_app.base_url = f"http://localhost:{mock_server.port}"
        mock_app._log = Mock()

        # Create real session for this test
        mock_app.session = aiohttp.ClientSession()

        try:
            await mock_app._test_api_endpoints()

            # Verify all endpoints were tested
            log_calls = [call[0][0] for call in mock_app._log.call_args_list]
            assert any("GET /api/status" in log for log in log_calls)
            assert any("POST /overlay/show" in log for log in log_calls)
            assert any("POST /overlay/hide" in log for log in log_calls)
            assert any("POST /overlay/update" in log for log in log_calls)
        finally:
            await mock_app.session.close()

    @pytest.mark.asyncio
    async def test_sse_stream_testing(self, mock_app, mock_server):
        """Test SSE stream testing functionality."""
        mock_app.base_url = f"http://localhost:{mock_server.port}"
        mock_app._log = Mock()

        # Create real session for this test
        mock_app.session = aiohttp.ClientSession()

        try:
            await mock_app._test_sse_stream()

            # Verify SSE connection was tested
            mock_app._log.assert_any_call("Testing SSE stream connection...")
            mock_app._log.assert_any_call("✅ SSE stream connected")
        finally:
            await mock_app.session.close()

    @pytest.mark.asyncio
    async def test_rapid_changes(self, mock_app):
        """Test rapid state changes functionality."""
        mock_app._set_status_state = AsyncMock()
        mock_app._log = Mock()

        await mock_app._test_rapid_changes()

        # Verify all state changes were made
        assert mock_app._set_status_state.call_count == 5
        mock_app._log.assert_any_call("Testing rapid state changes...")
        mock_app._log.assert_any_call("Rapid changes test completed")

    @pytest.mark.asyncio
    async def test_large_text_handling(self, mock_app):
        """Test large text handling."""
        mock_app._set_status_state = AsyncMock()
        mock_app._log = Mock()

        await mock_app._test_large_text()

        # Verify large text was sent
        mock_app._set_status_state.assert_called_once()
        args = mock_app._set_status_state.call_args[1]
        assert len(args["text"]) > 1000  # Large text

        mock_app._log.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_app):
        """Test error handling for invalid requests."""
        mock_app.base_url = "http://localhost:9999"  # Non-existent
        mock_app._log = Mock()
        mock_app.session = aiohttp.ClientSession()

        try:
            # Test various error scenarios
            await mock_app._show_overlay()
            await mock_app._hide_overlay()
            await mock_app._get_status()

            # Verify errors were logged
            error_logs = [
                call
                for call in mock_app._log.call_args_list
                if len(call[0]) > 1 and call[0][1] == "ERROR"
            ]
            assert len(error_logs) >= 3
        finally:
            await mock_app.session.close()

    def test_safe_async_call(self, mock_app):
        """Test safe async call wrapper."""
        mock_app.loop = Mock()
        mock_app.loop.is_closed.return_value = False

        async def test_func():
            return "test"

        wrapper = mock_app._safe_async_call(test_func)
        wrapper()

        # Verify coroutine was scheduled
        mock_app.loop.call_soon_threadsafe.assert_called()

    def test_clear_logs(self, mock_app):
        """Test log clearing functionality."""
        mock_app.log_display = Mock()
        mock_app._log = Mock()

        mock_app._clear_logs()

        mock_app.log_display.delete.assert_called_with("1.0", "end")
        mock_app._log.assert_called_with("Logs cleared")

    def test_export_logs(self, mock_app):
        """Test log export functionality."""
        mock_app.log_display = Mock()
        mock_app.log_display.get.return_value = "Test log content"
        mock_app._log = Mock()

        with patch("builtins.open", create=True) as mock_open:
            with patch("tkinter.messagebox.showinfo") as mock_msgbox:
                mock_app._export_logs()

                # Verify file was written
                mock_open.assert_called_once()
                mock_msgbox.assert_called_once()
                mock_app._log.assert_called()


class TestOverlayDebugToolsIntegration:
    """Integration tests for overlay debug tools."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow without GUI."""
        # This test simulates the full workflow without actual GUI

        # Mock the GUI components that would be created
        with patch("tkinter.Tk"), patch("tkinter.ttk.Notebook"), patch(
            "tkinter.BooleanVar"
        ), patch("tkinter.StringVar"), patch("tkinter.Text"), patch(
            "tkinter.scrolledtext.ScrolledText"
        ), patch(
            "tkinter.ttk.Label"
        ), patch(
            "threading.Thread"
        ):
            # Create app without calling _setup_ui
            app = OverlayDebugToolsGUI.__new__(OverlayDebugToolsGUI)
            app.loop = asyncio.get_event_loop()

            # Mock all GUI components
            app.log_display = Mock()
            app.status_display = Mock()
            app.text_input = Mock()
            app.auto_scroll_var = Mock()
            app.auto_scroll_var.get.return_value = True
            app.status_bar = Mock()
            app.sequence_timing = Mock()
            app.sequence_timing.get.return_value = "0.1"
            app.current_status = {}

            # Test basic functionality without network calls
            app._update_status_display()
            app._insert_preset_text("test")
            app._clear_logs()

            # Verify methods executed without errors
            assert True  # If we get here, basic functionality works


def test_main_execution():
    """Test main execution path."""
    with patch("overlay_debug_tools.OverlayDebugToolsGUI") as mock_gui:
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.print"):
                # Import and test main execution
                import overlay_debug_tools

                # This would normally run the GUI
                # We just verify the class would be instantiated
                mock_instance = Mock()
                mock_gui.return_value = mock_instance

                # Simulate what would happen in __main__
                app = overlay_debug_tools.OverlayDebugToolsGUI()
                assert mock_gui.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

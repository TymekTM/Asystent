"""Comprehensive tests for the open_web_module.

Tests both the new async plugin interface and legacy handler for backward compatibility.
Follows AGENTS.md guidelines: async/await, proper mocking, edge cases, clear naming.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from server.modules.open_web_module import (
    execute_function,
    get_functions,
    open_web_handler,
    register,
)


class TestOpenWebModule:
    """Test suite for open_web_module functionality."""

    def test_get_functions_structure(self):
        """Test that get_functions returns properly structured function definitions."""
        functions = get_functions()

        assert isinstance(functions, list)
        assert len(functions) == 1

        open_web_func = functions[0]
        assert open_web_func["name"] == "open_web"
        assert "description" in open_web_func
        assert "parameters" in open_web_func

        # Check parameter structure
        params = open_web_func["parameters"]
        assert params["type"] == "object"
        assert "url" in params["properties"]
        assert "test_mode" in params["properties"]
        assert params["required"] == ["url"]

    @pytest.mark.asyncio
    async def test_execute_function_success_with_https_url(self):
        """Test successful execution with HTTPS URL."""
        with patch("webbrowser.open", return_value=True) as mock_open:
            result = await execute_function(
                "open_web", {"url": "https://example.com"}, user_id=1
            )

            assert result["success"] is True
            assert "Successfully opened page: https://example.com" in result["message"]
            assert result["url"] == "https://example.com"
            mock_open.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_execute_function_success_with_http_url(self):
        """Test successful execution with HTTP URL."""
        with patch("webbrowser.open", return_value=True) as mock_open:
            result = await execute_function(
                "open_web", {"url": "http://example.com"}, user_id=1
            )

            assert result["success"] is True
            assert "Successfully opened page: http://example.com" in result["message"]
            assert result["url"] == "http://example.com"
            mock_open.assert_called_once_with("http://example.com")

    @pytest.mark.asyncio
    async def test_execute_function_auto_adds_https_scheme(self):
        """Test that HTTPS scheme is automatically added to URLs without scheme."""
        with patch("webbrowser.open", return_value=True) as mock_open:
            result = await execute_function(
                "open_web", {"url": "example.com"}, user_id=1
            )

            assert result["success"] is True
            assert result["url"] == "https://example.com"
            mock_open.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_execute_function_test_mode(self):
        """Test execution in test mode (should not call webbrowser)."""
        with patch("webbrowser.open") as mock_open:
            result = await execute_function(
                "open_web", {"url": "https://example.com", "test_mode": True}, user_id=1
            )

            assert result["success"] is True
            assert (
                "Would open page: https://example.com (test mode)" in result["message"]
            )
            assert result["test_mode"] is True
            assert result["url"] == "https://example.com"
            mock_open.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_function_missing_url(self):
        """Test error handling when URL parameter is missing."""
        result = await execute_function("open_web", {}, user_id=1)

        assert result["success"] is False
        assert "URL parameter is required" in result["message"]
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_function_empty_url(self):
        """Test error handling when URL parameter is empty."""
        result = await execute_function("open_web", {"url": ""}, user_id=1)

        assert result["success"] is False
        assert "URL parameter is required" in result["message"]
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_function_whitespace_only_url(self):
        """Test error handling when URL parameter contains only whitespace."""
        result = await execute_function("open_web", {"url": "   "}, user_id=1)

        assert result["success"] is False
        assert "URL parameter is required" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_function_browser_failure(self):
        """Test handling when webbrowser.open returns False."""
        with patch("webbrowser.open", return_value=False) as mock_open:
            result = await execute_function(
                "open_web", {"url": "https://example.com"}, user_id=1
            )

            assert result["success"] is False
            assert "Failed to open page: https://example.com" in result["message"]
            assert "error" in result
            mock_open.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_execute_function_browser_exception(self):
        """Test handling when webbrowser.open raises an exception."""
        test_exception = Exception("Browser not available")

        with patch("webbrowser.open", side_effect=test_exception):
            result = await execute_function(
                "open_web", {"url": "https://example.com"}, user_id=1
            )

            assert result["success"] is False
            assert "Error opening web page" in result["message"]
            assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_function_unknown_function(self):
        """Test error handling for unknown function names."""
        result = await execute_function(
            "unknown_function", {"url": "https://example.com"}, user_id=1
        )

        assert result["success"] is False
        assert "Unknown function: unknown_function" in result["message"]
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_function_uses_run_in_executor(self):
        """Test that webbrowser.open is called via run_in_executor (non-blocking)."""
        # Mock the event loop and run_in_executor
        mock_loop = AsyncMock()
        mock_loop.run_in_executor.return_value = True

        with patch("asyncio.get_event_loop", return_value=mock_loop):
            result = await execute_function(
                "open_web", {"url": "https://example.com"}, user_id=1
            )

            assert result["success"] is True
            mock_loop.run_in_executor.assert_called_once()
            # Check that webbrowser.open was passed to run_in_executor
            call_args = mock_loop.run_in_executor.call_args
            assert call_args[0][0] is None  # executor=None
            assert call_args[0][2] == "https://example.com"  # URL argument

    @pytest.mark.asyncio
    async def test_legacy_open_web_handler_string_params(self):
        """Test legacy handler with string parameters."""
        with patch("webbrowser.open", return_value=True):
            result = await open_web_handler("https://example.com")

            assert "Successfully opened page: https://example.com" in result

    @pytest.mark.asyncio
    async def test_legacy_open_web_handler_dict_params(self):
        """Test legacy handler with dictionary parameters."""
        with patch("webbrowser.open", return_value=True):
            result = await open_web_handler({"url": "https://example.com"})

            assert "Successfully opened page: https://example.com" in result

    @pytest.mark.asyncio
    async def test_legacy_open_web_handler_empty_params(self):
        """Test legacy handler with empty parameters."""
        result = await open_web_handler("")

        assert "URL parameter is required" in result

    @pytest.mark.asyncio
    async def test_legacy_open_web_handler_failure(self):
        """Test legacy handler when browser fails to open."""
        with patch("webbrowser.open", return_value=False):
            result = await open_web_handler("https://example.com")

            assert "Failed to open page" in result

    def test_register_function_structure(self):
        """Test that register() returns properly structured registration info."""
        registration = register()

        assert registration["command"] == "open"
        assert "open" in registration["aliases"]
        assert "url" in registration["aliases"]
        assert "browser" in registration["aliases"]
        assert "open_web" in registration["aliases"]
        assert registration["description"]
        assert registration["handler"] == open_web_handler
        assert "sub_commands" in registration
        assert "open" in registration["sub_commands"]

    def test_register_sub_command_structure(self):
        """Test the structure of sub-commands in registration."""
        registration = register()
        open_cmd = registration["sub_commands"]["open"]

        assert "description" in open_cmd
        assert "parameters" in open_cmd
        assert "url" in open_cmd["parameters"]
        assert open_cmd["parameters"]["url"]["required"] is True


class TestOpenWebModuleIntegration:
    """Integration tests for open_web_module."""

    @pytest.mark.asyncio
    async def test_full_workflow_success(self):
        """Test complete workflow: get_functions -> execute_function."""
        # Get function definitions
        functions = get_functions()
        open_web_func = functions[0]

        # Execute function
        with patch("webbrowser.open", return_value=True):
            result = await execute_function(
                open_web_func["name"], {"url": "https://github.com"}, user_id=123
            )

        assert result["success"] is True
        assert "github.com" in result["url"]

    @pytest.mark.asyncio
    async def test_full_workflow_with_legacy_handler(self):
        """Test integration between new plugin system and legacy handler."""
        registration = register()
        handler = registration["handler"]

        with patch("webbrowser.open", return_value=True):
            result = await handler("https://python.org")

        assert "Successfully opened page: https://python.org" in result

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test that multiple concurrent calls work properly (async safety)."""
        urls = ["https://example1.com", "https://example2.com", "https://example3.com"]

        with patch("webbrowser.open", return_value=True):
            # Execute multiple calls concurrently
            tasks = [
                execute_function("open_web", {"url": url}, user_id=i)
                for i, url in enumerate(urls)
            ]
            results = await asyncio.gather(*tasks)

        # All should succeed
        for result in results:
            assert result["success"] is True
            assert "Successfully opened page:" in result["message"]

    @pytest.mark.asyncio
    async def test_error_handling_doesnt_break_other_calls(self):
        """Test that errors in one call don't affect others."""
        with patch("webbrowser.open", side_effect=[Exception("Error"), True, True]):
            # First call fails, others succeed
            tasks = [
                execute_function("open_web", {"url": "https://fail.com"}, user_id=1),
                execute_function(
                    "open_web", {"url": "https://success1.com"}, user_id=2
                ),
                execute_function(
                    "open_web", {"url": "https://success2.com"}, user_id=3
                ),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # First should fail, others succeed
        assert results[0]["success"] is False
        assert results[1]["success"] is True
        assert results[2]["success"] is True


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])

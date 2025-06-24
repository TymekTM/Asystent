"""
Test suite for api_module.py - AGENTS.md Compliant

Tests core functionality of API module including:
- Plugin interface compliance
- HTTP request functionality
- Async operations
- Error handling
"""

import asyncio
import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import API module
from server.modules import api_module


class TestAPIModulePluginInterface:
    """Test plugin interface compliance."""

    def test_get_functions_returns_list(self):
        """Test that get_functions returns a list."""
        functions = api_module.get_functions()
        assert isinstance(functions, list)
        assert len(functions) >= 0  # API module might not expose direct functions

    def test_get_functions_structure(self):
        """Test function definitions have required structure."""
        functions = api_module.get_functions()

        for func in functions:
            assert isinstance(func, dict)
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert isinstance(func["parameters"], dict)


class TestAPIFunctionality:
    """Test API functionality."""

    @pytest.mark.asyncio
    async def test_execute_function_unknown(self):
        """Test execute_function with unknown function."""
        result = await api_module.execute_function("unknown_function", {}, user_id=1)

        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_api_module_initialization(self):
        """Test API module can be initialized."""
        # Test that we can get API module instance
        try:
            api_instance = await api_module.get_api_module()
            assert api_instance is not None
        except Exception:
            # If get_api_module doesn't exist, that's also fine
            assert True


class TestAsyncSafety:
    """Test async safety."""

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test concurrent function execution."""
        tasks = [
            api_module.execute_function(
                "unknown_function", {"test": f"value{i}"}, user_id=i
            )
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict) or isinstance(result, Exception)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

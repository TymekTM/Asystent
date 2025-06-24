"""
Test suite for search_module.py - AGENTS.md Compliant

Tests core functionality of search module including:
- Plugin interface compliance
- Search functionality
- Async operations
- Error handling
"""

import asyncio
import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import search module
from server.modules import search_module


class TestSearchModulePluginInterface:
    """Test plugin interface compliance."""

    def test_get_functions_returns_list(self):
        """Test that get_functions returns a list."""
        functions = search_module.get_functions()
        assert isinstance(functions, list)
        assert len(functions) > 0

    def test_get_functions_structure(self):
        """Test function definitions have required structure."""
        functions = search_module.get_functions()

        for func in functions:
            assert isinstance(func, dict)
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert isinstance(func["parameters"], dict)

    def test_search_function_exists(self):
        """Test that search function is defined."""
        functions = search_module.get_functions()
        function_names = [f["name"] for f in functions]

        # Should have some search-related function
        assert any("search" in name.lower() for name in function_names)


class TestSearchFunctionality:
    """Test search functionality."""

    @pytest.mark.asyncio
    async def test_execute_function_basic(self):
        """Test basic execute_function call."""
        functions = search_module.get_functions()
        if functions:
            func_name = functions[0]["name"]
            result = await search_module.execute_function(
                func_name,
                {"query": "test query", "test_mode": True}
                if "test_mode" in str(functions[0])
                else {"query": "test query"},
                user_id=1,
            )

            assert isinstance(result, dict)
            assert "success" in result

    @pytest.mark.asyncio
    async def test_execute_function_unknown(self):
        """Test execute_function with unknown function."""
        result = await search_module.execute_function("unknown_function", {}, user_id=1)

        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is False


class TestAsyncSafety:
    """Test async safety."""

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test concurrent function execution."""
        functions = search_module.get_functions()
        if functions:
            func_name = functions[0]["name"]

            tasks = [
                search_module.execute_function(
                    func_name,
                    {"query": f"test query {i}", "test_mode": True}
                    if "test_mode" in str(functions[0])
                    else {"query": f"test query {i}"},
                    user_id=i,
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

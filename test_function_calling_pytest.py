#!/usr/bin/env python3
"""
Pytest unit tests dla function calling system
Kompleksowe testy technicznej funkcjonalności
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any
import sys
import os

# Add server path to import server modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

# Import modules to test
try:
    from server.function_calling_system import FunctionCallingSystem
    from server.ai_module import process_ai_request
    from server.modules import weather_module, core_module, search_module, music_module, api_module
except ImportError as e:
    pytest.skip(f"Cannot import server modules: {e}", allow_module_level=True)


class TestFunctionCallingSystem:
    """Test FunctionCallingSystem class comprehensively"""
    
    @pytest.fixture
    def function_calling_system(self):
        """Create FunctionCallingSystem instance for testing"""
        return FunctionCallingSystem()
    
    @pytest.fixture
    def mock_modules(self):
        """Create mock server modules"""
        mock_weather = Mock()
        mock_weather.get_functions.return_value = [
            {
                "name": "get_weather",
                "description": "Get current weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"}
                    },
                    "required": ["location"]
                }
            }
        ]
        mock_weather.WeatherModule.return_value = Mock()
        mock_weather.WeatherModule.return_value.execute_function = AsyncMock(return_value="Sunny, 20°C")
        
        mock_core = Mock()
        mock_core.get_functions.return_value = [
            {
                "name": "set_timer",
                "description": "Set a timer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "duration": {"type": "string", "description": "Timer duration"}
                    },
                    "required": ["duration"]
                }
            }
        ]
        mock_core.CoreModule.return_value = Mock()
        mock_core.CoreModule.return_value.execute_function = AsyncMock(return_value="Timer set for 5 minutes")
        
        return {
            "weather_module": mock_weather,
            "core_module": mock_core
        }

    def test_function_calling_system_initialization(self, function_calling_system):
        """Test FunctionCallingSystem initialization"""
        assert function_calling_system.modules == {}
        assert function_calling_system.function_handlers == {}

    def test_register_module(self, function_calling_system):
        """Test module registration"""
        module_data = {
            "handler": Mock(),
            "description": "Test module",
            "sub_commands": {
                "test_command": {
                    "function": Mock(),
                    "params": {"test_param": "string"}
                }
            }
        }
        
        function_calling_system.register_module("test_module", module_data)
        
        assert "test_module" in function_calling_system.modules
        assert "test_module" in function_calling_system.function_handlers
        assert "test_module_test_command" in function_calling_system.function_handlers

    @patch('server.function_calling_system.weather_module')
    @patch('server.function_calling_system.core_module')
    def test_convert_modules_to_functions(self, mock_core, mock_weather, function_calling_system):
        """Test conversion of modules to OpenAI function format"""
        # Setup mocks
        mock_weather.get_functions.return_value = [
            {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        ]
        mock_weather.WeatherModule = Mock
        
        mock_core.get_functions.return_value = [
            {
                "name": "set_timer", 
                "description": "Set timer",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        ]
        mock_core.CoreModule = Mock
        
        functions = function_calling_system.convert_modules_to_functions()
        
        # Should have functions from both modules
        assert len(functions) >= 2
        
        # Check function format
        for func in functions:
            assert "type" in func
            assert func["type"] == "function"
            assert "function" in func
            assert "name" in func["function"]
            assert "description" in func["function"]
            assert "parameters" in func["function"]

    @pytest.mark.asyncio
    async def test_execute_function_server_module(self, function_calling_system):
        """Test executing server module function"""
        # Setup mock module instance
        mock_module = Mock()
        mock_module.execute_function = AsyncMock(return_value="Function executed successfully")
        
        function_calling_system.function_handlers["weather_get_weather"] = {
            "type": "server_module",
            "module": mock_module,
            "module_name": "weather",
            "function_name": "get_weather"
        }
        
        result = await function_calling_system.execute_function(
            "weather_get_weather",
            {"location": "Warsaw"}
        )
        
        assert result == "Function executed successfully"
        mock_module.execute_function.assert_called_once_with(
            "get_weather", {"location": "Warsaw"}, user_id=1
        )

    @pytest.mark.asyncio
    async def test_execute_function_not_found(self, function_calling_system):
        """Test executing non-existent function"""
        result = await function_calling_system.execute_function(
            "nonexistent_function",
            {}
        )
        
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_function_exception_handling(self, function_calling_system):
        """Test exception handling in function execution"""
        mock_module = Mock()
        mock_module.execute_function = AsyncMock(side_effect=Exception("Test error"))
        
        function_calling_system.function_handlers["test_function"] = {
            "type": "server_module",
            "module": mock_module,
            "module_name": "test",
            "function_name": "test_func"
        }
        
        result = await function_calling_system.execute_function("test_function", {})
        
        assert "error" in result.lower()
        assert "test error" in result.lower()


class TestServerModuleIntegration:
    """Test integration with actual server modules"""
    
    def test_weather_module_functions(self):
        """Test weather module function definitions"""
        functions = weather_module.get_functions()
        
        assert isinstance(functions, list)
        assert len(functions) >= 1
        
        for func in functions:
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert isinstance(func["parameters"], dict)

    def test_core_module_functions(self):
        """Test core module function definitions"""
        functions = core_module.get_functions()
        
        assert isinstance(functions, list)
        assert len(functions) >= 10  # Core module should have many functions
        
        # Check for expected functions
        function_names = [f["name"] for f in functions]
        expected_functions = ["set_timer", "add_reminder", "add_task"]
        
        for expected in expected_functions:
            assert expected in function_names

    def test_search_module_functions(self):
        """Test search module function definitions"""
        functions = search_module.get_functions()
        
        assert isinstance(functions, list)
        assert len(functions) >= 1
        
        function_names = [f["name"] for f in functions]
        assert any("search" in name.lower() for name in function_names)

    def test_music_module_functions(self):
        """Test music module function definitions"""
        functions = music_module.get_functions()
        
        assert isinstance(functions, list)
        assert len(functions) >= 1

    def test_api_module_functions(self):
        """Test API module function definitions"""
        functions = api_module.get_functions()
        
        assert isinstance(functions, list)
        assert len(functions) >= 1

    @pytest.mark.asyncio
    async def test_weather_module_execution(self):
        """Test weather module function execution"""
        weather_instance = weather_module.WeatherModule()
        
        # Test with mock mode
        result = await weather_instance.execute_function(
            "get_weather", 
            {"location": "Warsaw", "test_mode": True},
            user_id=1
        )
        
        assert isinstance(result, (str, dict))

    @pytest.mark.asyncio
    async def test_core_module_execution(self):
        """Test core module function execution"""
        core_instance = core_module.CoreModule()
        
        # Test timer function
        result = await core_instance.execute_function(
            "set_timer",
            {"duration": "5m", "label": "test timer"},
            user_id=1
        )
        
        assert isinstance(result, (str, dict))


class TestAIModuleIntegration:
    """Test AI module integration with function calling"""
    
    @pytest.mark.asyncio
    @patch('server.ai_module.FunctionCallingSystem')
    async def test_ai_module_function_calling_initialization(self, mock_fc_system):
        """Test that AI module properly initializes function calling"""
        mock_fc_instance = Mock()
        mock_fc_instance.convert_modules_to_functions.return_value = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "Test function",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        mock_fc_system.return_value = mock_fc_instance
        
        # Mock OpenAI response
        with patch('server.ai_module.call_openai_api') as mock_openai:
            mock_openai.return_value = {
                "choices": [{
                    "message": {
                        "content": '{"text": "Test response", "command": "", "params": {}}',
                        "tool_calls": None
                    }
                }]
            }
            
            result = await process_ai_request(
                message="Test message",
                user_id=1,
                conversation_history=[],
                use_function_calling=True
            )
            
            # Verify function calling was initialized
            mock_fc_system.assert_called_once()
            mock_fc_instance.convert_modules_to_functions.assert_called_once()

    @pytest.mark.asyncio
    @patch('server.ai_module.FunctionCallingSystem')
    async def test_ai_module_function_execution(self, mock_fc_system):
        """Test that AI module executes functions when tool calls are present"""
        mock_fc_instance = Mock()
        mock_fc_instance.convert_modules_to_functions.return_value = [
            {
                "type": "function",
                "function": {
                    "name": "weather_get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        mock_fc_instance.execute_function = AsyncMock(return_value="Sunny, 20°C")
        mock_fc_system.return_value = mock_fc_instance
        
        # Mock OpenAI response with tool calls
        with patch('server.ai_module.call_openai_api') as mock_openai:
            mock_openai.return_value = {
                "choices": [{
                    "message": {
                        "content": "I'll check the weather for you.",
                        "tool_calls": [{
                            "function": {
                                "name": "weather_get_weather",
                                "arguments": '{"location": "Warsaw"}'
                            }
                        }]
                    }
                }]
            }
            
            result = await process_ai_request(
                message="What's the weather in Warsaw?",
                user_id=1,
                conversation_history=[],
                use_function_calling=True
            )
            
            # Verify function was executed
            mock_fc_instance.execute_function.assert_called_once()


class TestFunctionCallParameterValidation:
    """Test parameter validation for function calls"""
    
    def test_weather_function_parameters(self):
        """Test weather function parameter validation"""
        functions = weather_module.get_functions()
        weather_func = next(f for f in functions if f["name"] == "get_weather")
        
        params = weather_func["parameters"]
        assert "type" in params
        assert params["type"] == "object"
        assert "properties" in params
        assert "location" in params["properties"]
        assert "required" in params
        assert "location" in params["required"]

    def test_core_timer_parameters(self):
        """Test core timer function parameters"""
        functions = core_module.get_functions()
        timer_func = next(f for f in functions if f["name"] == "set_timer")
        
        params = timer_func["parameters"]
        assert "duration" in params["properties"]
        assert "duration" in params["required"]

    def test_parameter_types(self):
        """Test that all function parameters have correct types"""
        all_modules = [weather_module, core_module, search_module, music_module, api_module]
        
        for module in all_modules:
            functions = module.get_functions()
            for func in functions:
                params = func["parameters"]
                
                # Must have required structure
                assert "type" in params
                assert params["type"] == "object"
                assert "properties" in params
                assert isinstance(params["properties"], dict)
                
                # Check each property has type
                for prop_name, prop_def in params["properties"].items():
                    assert "type" in prop_def
                    assert prop_def["type"] in ["string", "integer", "boolean", "number", "array", "object"]


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_invalid_function_name(self):
        """Test calling invalid function name"""
        fc_system = FunctionCallingSystem()
        result = await fc_system.execute_function("invalid_function", {})
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_parameters(self):
        """Test calling function with invalid parameters"""
        fc_system = FunctionCallingSystem()
        
        # Mock a function handler
        mock_module = Mock()
        mock_module.execute_function = AsyncMock(side_effect=TypeError("Invalid parameters"))
        
        fc_system.function_handlers["test_func"] = {
            "type": "server_module",
            "module": mock_module,
            "module_name": "test",
            "function_name": "test"
        }
        
        result = await fc_system.execute_function("test_func", {"invalid": "params"})
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_module_not_available(self):
        """Test calling function when module is not available"""
        fc_system = FunctionCallingSystem()
        
        # Register handler with None module
        fc_system.function_handlers["unavailable_func"] = {
            "type": "server_module",
            "module": None,
            "module_name": "unavailable",
            "function_name": "test"
        }
        
        result = await fc_system.execute_function("unavailable_func", {})
        assert "error" in result.lower()


class TestPerformance:
    """Test performance characteristics"""
    
    def test_function_loading_performance(self):
        """Test that function loading is reasonably fast"""
        import time
        
        start_time = time.time()
        fc_system = FunctionCallingSystem()
        functions = fc_system.convert_modules_to_functions()
        end_time = time.time()
        
        # Should load functions in under 5 seconds
        assert end_time - start_time < 5.0
        
        # Should load a reasonable number of functions
        assert len(functions) >= 10

    @pytest.mark.asyncio
    async def test_function_execution_performance(self):
        """Test that function execution is reasonably fast"""
        import time
        
        weather_instance = weather_module.WeatherModule()
        
        start_time = time.time()
        await weather_instance.execute_function(
            "get_weather",
            {"location": "Warsaw", "test_mode": True},
            user_id=1
        )
        end_time = time.time()
        
        # Function execution should be under 10 seconds
        assert end_time - start_time < 10.0


class TestCoverage:
    """Test coverage validation"""
    
    def test_all_modules_have_functions(self):
        """Test that all modules provide functions"""
        modules = [weather_module, core_module, search_module, music_module, api_module]
        
        total_functions = 0
        for module in modules:
            functions = module.get_functions()
            assert len(functions) >= 1, f"Module {module} has no functions"
            total_functions += len(functions)
        
        # Should have at least 20 total functions
        assert total_functions >= 20

    def test_function_naming_consistency(self):
        """Test that function names follow consistent patterns"""
        modules = [weather_module, core_module, search_module, music_module, api_module]
        
        for module in modules:
            functions = module.get_functions()
            for func in functions:
                name = func["name"]
                
                # Function names should be snake_case
                assert name.islower()
                assert "_" in name or len(name.split("_")) == 1
                
                # Should not contain spaces or special characters
                assert " " not in name
                assert all(c.isalnum() or c == "_" for c in name)

    def test_function_descriptions_quality(self):
        """Test that function descriptions are meaningful"""
        modules = [weather_module, core_module, search_module, music_module, api_module]
        
        for module in modules:
            functions = module.get_functions()
            for func in functions:
                description = func["description"]
                
                # Description should be meaningful
                assert len(description) >= 10
                assert description[0].isupper()  # Should start with capital letter
                
                # Should contain relevant keywords
                assert any(word in description.lower() for word in ["get", "set", "add", "create", "update", "delete", "search", "play", "stop"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=server", "--cov-report=html", "--cov-report=term-missing"])

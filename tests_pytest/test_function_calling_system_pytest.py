#!/usr/bin/env python3
"""
pytest test for function calling system conversion.
"""

import pytest
import sys
import os

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from function_calling_system import FunctionCallingSystem

def test_function_calling_conversion():
    """Test the conversion of modules to OpenAI function calling format."""
    
    # Mock modules structure similar to what the assistant uses
    test_modules = {
        "core": {
            "description": "Timers, calendar events, reminders, shopping list, to-do tasks",
            "handler": lambda params="", **kwargs: f"Core handler called with: {params}",
            "sub_commands": {
                "set_timer": {
                    "function": lambda params="", **kwargs: f"Timer set for: {params}",
                    "description": "Ustaw timer",
                    "aliases": ["timer"],
                    "params_desc": "<seconds>"
                },
                "view_timers": {
                    "function": lambda params="", **kwargs: "Showing all timers",
                    "description": "Pokaż aktywne timery", 
                    "aliases": ["timers"],
                    "params_desc": ""
                }
            }
        },
        "memory": {
            "description": "Zarządza długoterminową pamięcią asystenta",
            "handler": lambda params="", **kwargs: f"Memory handler called with: {params}",
            "sub_commands": {
                "add": {
                    "function": lambda params="", **kwargs: f"Added to memory: {params}",
                    "description": "Zapisuje nową informację do pamięci",
                    "aliases": []
                },
                "get": {
                    "function": lambda params="", **kwargs: f"Retrieved from memory: {params}",
                    "description": "Pobiera informacje z pamięci",
                    "aliases": ["show", "check"]
                }
            }
        }
    }
    
    # Test function calling system
    fc_system = FunctionCallingSystem(test_modules)
    functions = fc_system.convert_modules_to_functions()
    
    # Basic assertions
    assert len(functions) > 0, "Should generate functions from modules"
    
    # Check function structure
    for func in functions:
        assert "type" in func, "Function should have 'type' field"
        assert func["type"] == "function", "Function type should be 'function'"
        assert "function" in func, "Function should have 'function' field"
        
        func_def = func["function"]
        assert "name" in func_def, "Function should have name"
        assert "description" in func_def, "Function should have description"
        assert "parameters" in func_def, "Function should have parameters"
        
        # Check parameters structure
        params = func_def["parameters"]
        assert params["type"] == "object", "Parameters should be object type"
        assert "properties" in params, "Parameters should have properties"

def test_function_calling_timer_functions():
    """Test that timer functions are correctly generated with proper descriptions."""
    
    test_modules = {
        "core": {
            "description": "Timers, calendar events, reminders, shopping list, to-do tasks",
            "handler": lambda params="", **kwargs: f"Core handler called with: {params}",
            "sub_commands": {
                "set_timer": {
                    "function": lambda params="", **kwargs: f"Timer set for: {params}",
                    "description": "Ustaw timer",
                    "aliases": ["timer"],
                    "params_desc": "<seconds>"
                }
            }
        }
    }
    
    fc_system = FunctionCallingSystem(test_modules)
    functions = fc_system.convert_modules_to_functions()
    
    # Find timer functions
    timer_functions = [f for f in functions if 'timer' in f['function']['name']]
    assert len(timer_functions) > 0, "Should generate timer functions"
    
    # Check enhanced descriptions
    for func in timer_functions:
        desc = func['function']['description']
        assert any(keyword in desc for keyword in ['timer', 'minutnik', 'stoper', 'countdown']), \
            f"Timer function should have enhanced description with keywords: {desc}"

def test_function_calling_execution():
    """Test that function calling system can execute functions."""
    
    executed_functions = []
    
    def mock_timer_function(params="", **kwargs):
        executed_functions.append(("set_timer", str(params)))
        return f"Timer set for: {params}"
    
    test_modules = {
        "core": {
            "description": "Timers, calendar events, reminders, shopping list, to-do tasks",
            "handler": lambda params="", **kwargs: f"Core handler called with: {params}",
            "sub_commands": {
                "set_timer": {
                    "function": mock_timer_function,
                    "description": "Ustaw timer",
                    "aliases": ["timer"],
                    "params_desc": "<seconds>"
                }
            }
        }
    }
    fc_system = FunctionCallingSystem(test_modules)
    
    # Convert modules to register function handlers
    functions = fc_system.convert_modules_to_functions()
    
    # Test function execution
    result = fc_system.execute_function("core_set_timer", {"seconds": "60"})
    
    assert len(executed_functions) == 1, "Function should have been executed"
    assert executed_functions[0][0] == "set_timer", "Correct function should have been called"
    assert "Timer set for:" in result, "Should return function result"

if __name__ == "__main__":
    test_function_calling_conversion()
    test_function_calling_timer_functions()
    test_function_calling_execution()
    print("All function calling tests passed!")

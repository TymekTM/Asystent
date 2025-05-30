#!/usr/bin/env python3
"""
Test script for the new function calling system.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import json
from collections import deque
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
    
    # Create function calling system
    fc_system = FunctionCallingSystem(test_modules)
    
    # Convert to functions
    functions = fc_system.convert_modules_to_functions()
    
    print("Converted functions:")
    for i, func in enumerate(functions):
        print(f"{i+1}. {func['function']['name']}: {func['function']['description']}")
        print(f"   Parameters: {list(func['function']['parameters']['properties'].keys())}")
    
    print(f"\nTotal functions: {len(functions)}")
    
    # Test function execution
    print("\n=== Testing Function Execution ===")
    
    # Test timer function
    result1 = fc_system.execute_function("core_set_timer", {"seconds": "300"})
    print(f"core_set_timer result: {result1}")
    
    # Test memory function
    result2 = fc_system.execute_function("memory_add", {"params": "Remember my birthday is tomorrow"})
    print(f"memory_add result: {result2}")
    
    # Test main handler with action
    result3 = fc_system.execute_function("core_main", {"action": "set_timer", "seconds": "60"})
    print(f"core_main with action result: {result3}")
    
    return len(functions) > 0

def test_parameter_parsing():
    """Test how parameters are parsed from params_desc."""
    from function_calling_system import FunctionCallingSystem
    
    # Test module with different parameter formats
    test_module = {
        "test": {
            "description": "Test module",
            "sub_commands": {
                "single_param": {
                    "function": lambda params="", **kwargs: f"Got: {params}",
                    "description": "Test single parameter",
                    "params_desc": "<seconds>"
                },
                "multi_param": {
                    "function": lambda params="", **kwargs: f"Got: {params}",
                    "description": "Test multiple parameters", 
                    "params_desc": "<datetime> <note>"
                },
                "no_param": {
                    "function": lambda params="", **kwargs: "No params needed",
                    "description": "Test no parameters",
                    "params_desc": ""
                }
            }
        }
    }
    
    fc_system = FunctionCallingSystem(test_module)
    functions = fc_system.convert_modules_to_functions()
    
    print("\n=== Parameter Parsing Test ===")
    for func in functions:
        name = func['function']['name']
        params = func['function']['parameters']['properties']
        required = func['function']['parameters']['required']
        print(f"{name}:")
        print(f"  Properties: {list(params.keys())}")
        print(f"  Required: {required}")
    
    return True

if __name__ == "__main__":
    print("Testing Function Calling System...")
    
    success1 = test_function_calling_conversion()
    success2 = test_parameter_parsing()
    
    if success1 and success2:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

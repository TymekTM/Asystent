#!/usr/bin/env python3
"""
Test function definitions for timer functions
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import json
from function_calling_system import FunctionCallingSystem
from modules import core_module

def test_timer_function_definitions():
    """Test how timer functions are defined for OpenAI"""
    
    # Get core module registration
    core_info = core_module.register()
    modules = {'core': core_info}
    
    # Create function calling system
    fc_system = FunctionCallingSystem(modules)
    functions = fc_system.convert_modules_to_functions()
    
    # Find timer-related functions
    timer_functions = [f for f in functions if 'timer' in f['function']['name'].lower()]
    
    print("=== Timer Function Definitions ===")
    for func in timer_functions:
        print(f"\nFunction: {func['function']['name']}")
        print(f"Description: {func['function']['description']}")
        print(f"Parameters: {json.dumps(func['function']['parameters'], indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    test_timer_function_definitions()

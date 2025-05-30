#!/usr/bin/env python3
"""
Test all function definitions including system functions
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import json
from function_calling_system import FunctionCallingSystem
from modules import core_module

def test_all_function_definitions():
    """Test all function definitions including system functions"""
    
    # Get core module registration
    core_info = core_module.register()
    modules = {'core': core_info}
    
    # Create function calling system
    fc_system = FunctionCallingSystem(modules)
    functions = fc_system.convert_modules_to_functions()
    
    print(f"=== All Function Definitions ({len(functions)} total) ===")
    
    # Show system functions first
    system_functions = [f for f in functions if f['function']['name'].startswith('system_')]
    if system_functions:
        print("\n--- System Functions ---")
        for func in system_functions:
            print(f"Function: {func['function']['name']}")
            print(f"Description: {func['function']['description']}")
            print()
    
    # Show timer functions
    timer_functions = [f for f in functions if 'timer' in f['function']['name'].lower()]
    if timer_functions:
        print("--- Timer Functions ---")
        for func in timer_functions:
            print(f"Function: {func['function']['name']}")
            print(f"Description: {func['function']['description']}")
            print()

if __name__ == "__main__":
    test_all_function_definitions()

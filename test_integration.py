#!/usr/bin/env python3
"""
Integration test for function calling with real modules.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import json
from collections import deque
from function_calling_system import FunctionCallingSystem

def test_with_real_modules():
    """Test with actual module imports."""
    print("=== Testing with Real Modules ===")
    
    # Import real modules
    try:
        from modules import core_module, memory_module, search_module
        
        # Create modules dictionary like the assistant does
        modules = {}
        
        # Register core module
        core_info = core_module.register()
        if 'command' in core_info:
            modules[core_info['command']] = core_info
            
        # Register memory module  
        memory_info = memory_module.register()
        if 'command' in memory_info:
            modules[memory_info['command']] = memory_info
            
        # Register search module
        search_info = search_module.register()
        if 'command' in search_info:
            modules[search_info['command']] = search_info
            
        print(f"Loaded modules: {list(modules.keys())}")
        
        # Create function calling system
        fc_system = FunctionCallingSystem(modules)
        functions = fc_system.convert_modules_to_functions()
        
        print(f"Converted {len(functions)} functions:")
        for func in functions:
            print(f"  - {func['function']['name']}: {func['function']['description']}")
        
        # Test some function calls
        print("\n=== Function Call Tests ===")
        
        # Test core timer function
        result1 = fc_system.execute_function("core_set_timer", {"seconds": "10"})
        print(f"Set timer result: {result1}")
        
        # Test memory add
        result2 = fc_system.execute_function("memory_add", {"params": "Test memory entry"})
        print(f"Memory add result: {result2}")
        
        # Test core main with action
        result3 = fc_system.execute_function("core_main", {
            "action": "view_timers"
        })
        print(f"View timers result: {result3}")
        
        return True
        
    except ImportError as e:
        print(f"Could not import modules: {e}")
        return False
    except Exception as e:
        print(f"Error in real module test: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_openai_function_format():
    """Show how the functions look in OpenAI format."""
    print("\n=== OpenAI Function Format Example ===")
    
    # Import real modules
    try:
        from modules import core_module
        
        core_info = core_module.register()
        modules = {"core": core_info}
        
        fc_system = FunctionCallingSystem(modules)
        functions = fc_system.convert_modules_to_functions()
        
        # Show first function in OpenAI format
        if functions:
            print("Example function definition for OpenAI:")
            print(json.dumps(functions[0], indent=2))
            
        return True
        
    except Exception as e:
        print(f"Error showing OpenAI format: {e}")
        return False

if __name__ == "__main__":
    print("Integration Testing Function Calling System...")
    
    success1 = test_with_real_modules()
    success2 = show_openai_function_format()
    
    if success1 and success2:
        print("\n✅ All integration tests passed!")
    else:
        print("\n❌ Some integration tests failed!")
        sys.exit(1)

#!/usr/bin/env python3
"""
Test the function calling system directly.
"""

import asyncio
import sys
import os
sys.path.append('server')
os.chdir('server')

from plugin_manager import plugin_manager
from function_calling_system import FunctionCallingSystem

async def test_function_calling_system():
    print("Testing function calling system...")
    
    # Initialize plugin manager
    await plugin_manager.discover_plugins()
    
    # Load some plugins
    await plugin_manager.load_plugin('weather_module')
    await plugin_manager.enable_plugin_for_user('1', 'weather_module')
    
    print(f"Plugin registry: {list(plugin_manager.function_registry.keys())}")
    
    # Initialize function calling system
    function_system = FunctionCallingSystem()
    await function_system.initialize()
    
    # Test conversion
    functions = function_system.convert_modules_to_functions()
    print(f"Converted {len(functions)} functions:")
    
    for func in functions:
        print(f"  - {func}")

if __name__ == "__main__":
    asyncio.run(test_function_calling_system())

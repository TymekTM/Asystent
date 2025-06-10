#!/usr/bin/env python3
"""
Debug script to check function registry state during function calling system initialization.
"""

import sys
import os
import asyncio

# Add server directory to Python path for imports
server_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, server_dir)

from plugin_manager import plugin_manager
from function_calling_system import FunctionCallingSystem

async def main():
    print("🔍 Debugging Function Registry and Conversion Process")
    print("=" * 80)
    
    # Initialize plugin manager
    print("📦 Initializing plugin manager...")
    await plugin_manager.discover_plugins()
    
    # Load all discovered plugins
    for plugin_name in list(plugin_manager.plugins.keys()):
        await plugin_manager.load_plugin(plugin_name)
    
    print(f"🧩 Plugin manager function_registry keys: {list(plugin_manager.function_registry.keys())}")
    print(f"📊 Total functions in registry: {len(plugin_manager.function_registry)}")
    
    # Show some sample function info
    print("\n📋 Sample function registry content:")
    for i, (func_name, func_info) in enumerate(plugin_manager.function_registry.items()):
        print(f"  {i+1}. {func_name}: {func_info}")
        if i >= 3:  # Show first 4 functions
            break
    
    print("\n🔄 Testing function conversion...")
    function_calling_system = FunctionCallingSystem()
    
    # Try conversion
    converted_functions = function_calling_system.convert_modules_to_functions()
    
    print(f"✅ Converted {len(converted_functions)} functions")
    
    if converted_functions:
        print("\n📋 Sample converted functions:")
        for i, func in enumerate(converted_functions[:3]):
            print(f"  {i+1}. {func}")
    
    print(f"\n🔗 Function handlers created: {len(function_calling_system.function_handlers)}")
    print(f"🔑 Handler keys: {list(function_calling_system.function_handlers.keys())}")

if __name__ == "__main__":
    asyncio.run(main())

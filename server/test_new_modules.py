"""
Test script for new modules functionality
Skrypt testowy dla nowych modułów - onboarding i plugin monitor
"""

import asyncio
import json
import sys
from pathlib import Path

# Add server path
sys.path.insert(0, str(Path(__file__).parent))

from plugin_manager import plugin_manager
from function_calling_system import FunctionCallingSystem

async def test_new_modules():
    """Test nowych modułów: onboarding i plugin monitor."""
    print("🧪 Testing New Modules Functionality")
    print("=" * 60)
      # Initialize plugin manager
    print("📦 Initializing plugin manager...")
    await plugin_manager.discover_plugins()
    
    # Load all discovered plugins
    for plugin_name in plugin_manager.plugins.keys():
        await plugin_manager.load_plugin(plugin_name)
    
    # Initialize function calling system
    function_system = FunctionCallingSystem()
    await function_system.initialize()
    
    # Count functions
    total_functions = len(plugin_manager.function_registry)
    print(f"✅ Total functions registered: {total_functions}")
    
    # Test onboarding functions
    print("\n🏁 Testing Onboarding Functions:")
    onboarding_functions = [
        key for key in plugin_manager.function_registry.keys() 
        if 'onboarding' in key
    ]
    print(f"   Found {len(onboarding_functions)} onboarding functions:")
    for func in onboarding_functions:
        print(f"   - {func}")
    
    # Test plugin monitor functions  
    print("\n🔧 Testing Plugin Monitor Functions:")
    monitor_functions = [
        key for key in plugin_manager.function_registry.keys() 
        if 'plugin_monitor' in key
    ]
    print(f"   Found {len(monitor_functions)} plugin monitor functions:")
    for func in monitor_functions:
        print(f"   - {func}")
    
    # Test function conversion
    print("\n🔄 Testing Function Conversion:")
    converted_functions = function_system.convert_modules_to_functions()
    print(f"   Converted {len(converted_functions)} functions for OpenAI")
    
    # Find new functions in converted list
    onboarding_converted = [
        f for f in converted_functions 
        if 'onboarding' in f['function']['name']
    ]
    monitor_converted = [
        f for f in converted_functions 
        if 'plugin_monitor' in f['function']['name']
    ]
    
    print(f"   Onboarding functions converted: {len(onboarding_converted)}")
    print(f"   Plugin monitor functions converted: {len(monitor_converted)}")
    
    # Show sample converted functions
    print("\n📋 Sample New Functions:")
    if onboarding_converted:
        func = onboarding_converted[0]
        print(f"   Onboarding: {func['function']['name']}")
        print(f"   Description: {func['function']['description']}")
    
    if monitor_converted:
        func = monitor_converted[0]
        print(f"   Monitor: {func['function']['name']}")
        print(f"   Description: {func['function']['description']}")
    
    print("\n✅ New modules test completed successfully!")
    print(f"📊 Summary: {total_functions} total functions, including {len(onboarding_functions)} onboarding and {len(monitor_functions)} monitoring functions")

if __name__ == "__main__":
    asyncio.run(test_new_modules())

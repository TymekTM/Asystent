"""
Test script to verify all plugin functions work correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "server"))

import asyncio
from plugin_manager import PluginManager

async def test_all_plugins():
    """Test all plugins and their functions."""
    print("🧪 Testing Plugin System...")
    
    # Initialize plugin manager with correct path
    plugin_manager = PluginManager("server/modules")
    
    # Discover plugins
    plugins = await plugin_manager.discover_plugins()
    print(f"📋 Discovered {len(plugins)} plugins:")
    
    for plugin in plugins:
        print(f"  • {plugin.name} - {plugin.description}")
        print(f"    Functions: {', '.join(plugin.functions)}")
        print(f"    Version: {plugin.version}")
        print()
    
    # Test loading plugins
    print("🔄 Testing plugin loading...")
    for plugin_name in plugin_manager.plugins.keys():
        try:
            success = await plugin_manager.load_plugin(plugin_name)
            if success:
                print(f"  ✅ {plugin_name} loaded successfully")
            else:
                print(f"  ❌ {plugin_name} failed to load")
        except Exception as e:
            print(f"  ❌ {plugin_name} error: {e}")
    
    # Test function calling for user
    print("\n🧮 Testing function calls...")
    user_id = "1"
    
    # Enable plugins for test user
    await plugin_manager.enable_plugin_for_user(user_id, "weather_module")
    await plugin_manager.enable_plugin_for_user(user_id, "search_module")
    await plugin_manager.enable_plugin_for_user(user_id, "memory_module")
    await plugin_manager.enable_plugin_for_user(user_id, "api_module")    # Test weather function
    try:
        result = await plugin_manager.call_plugin_function(
            user_id, 
            "weather_module",
            "get_weather", 
            {"location": "Warsaw, Poland"}
        )
        print(f"  ✅ Weather test: {result.get('success', False) if result else False}")
        if result and not result.get('success'):
            print(f"    ⚠️  Message: {result.get('error', result.get('message', 'Unknown'))}")
    except Exception as e:
        print(f"  ❌ Weather test error: {e}")
    
    # Test memory function
    try:
        result = await plugin_manager.call_plugin_function(
            user_id,
            "memory_module",
            "save_memory",
            {
                "memory_type": "preferences",
                "key": "test_preference",
                "value": "This is a test preference"
            }
        )
        print(f"  ✅ Memory save test: {result.get('success', False) if result else False}")
    except Exception as e:
        print(f"  ❌ Memory test error: {e}")
    
    # Test search function (if available)
    try:
        result = await plugin_manager.call_plugin_function(
            user_id,
            "search_module", 
            "search_news",
            {"query": "AI technology"}
        )
        print(f"  ✅ Search test: {result.get('success', False) if result else False}")
        if result and not result.get('success'):
            print(f"    ⚠️  Message: {result.get('error', result.get('message', 'Unknown'))}")
    except Exception as e:
        print(f"  ❌ Search test error: {e}")
    
    print("\n✅ Plugin system testing completed!")

if __name__ == "__main__":
    asyncio.run(test_all_plugins())

#!/usr/bin/env python3

import asyncio
import json
from plugin_manager import plugin_manager
from function_calling_system import FunctionCallingSystem
from ai_module import AIModule
from collections import deque

async def test_ai_with_functions():
    print("=== Testing AI with Function Calling ===")
    
    # Load plugins
    print("Loading plugins...")
    await plugin_manager.discover_plugins()
    for plugin_name in list(plugin_manager.plugins.keys()):
        await plugin_manager.load_plugin(plugin_name)
    
    print(f'Loaded {len(plugin_manager.function_registry)} functions')
    
    # Create AI module
    ai_module = AIModule({})
    
    # Test context with modules
    modules = {}
    for plugin_name, plugin_info in plugin_manager.plugins.items():
        if plugin_info.loaded:
            modules[plugin_name] = plugin_info.module
    
    # Test weather query
    print("\n=== Testing Weather Query ===")
    try:
        context = {
            'user_id': 'test_user',
            'history': [],
            'available_plugins': list(plugin_manager.plugins.keys()),
            'modules': modules,
            'user_name': 'Test User'
        }
        
        response = await ai_module.process_query("Jaka jest pogoda w Warszawie?", context)
        print(f"AI Response: {response}")
        
        # Try to parse response
        try:
            response_data = json.loads(response)
            print(f"Response type: {type(response_data)}")
            print(f"Response content: {response_data}")
            if "function_calls_executed" in response_data:
                print("✅ Function calls were executed!")
        except json.JSONDecodeError:
            print("Response is not JSON:", response)
            
    except Exception as e:
        print(f"Error in weather query: {e}")
        import traceback
        traceback.print_exc()
    
    # Test timer query  
    print("\n=== Testing Timer Query ===")
    try:
        response = await ai_module.process_query("Ustaw timer na 60 sekund", context)
        print(f"AI Response: {response}")
        
        try:
            response_data = json.loads(response)
            if "function_calls_executed" in response_data:
                print("✅ Function calls were executed!")
        except json.JSONDecodeError:
            print("Response is not JSON:", response)
            
    except Exception as e:
        print(f"Error in timer query: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_with_functions())

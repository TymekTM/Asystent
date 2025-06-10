#!/usr/bin/env python3
"""
End-to-end test of AI module with function calling.
Tests the complete pipeline: user query → AI → function call → plugin execution → AI response → TTS
"""

import asyncio
import sys
import os
import json
import logging
from collections import deque

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_module import generate_response, AIModule
from plugin_manager import PluginManager
import config_loader

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ai_with_function_calling():
    """Test AI module with function calling using real plugins."""
    print("🔥 Testing AI Module with Function Calling")
    print("=" * 60)
    
    try:        # Initialize the GLOBAL plugin manager and load plugins
        from plugin_manager import plugin_manager
        await plugin_manager.discover_plugins()
        
        # Load all discovered plugins
        for plugin_name in list(plugin_manager.plugins.keys()):
            await plugin_manager.load_plugin(plugin_name)
        
        # Build modules dict from loaded plugins
        modules = {}
        for plugin_name, plugin_info in plugin_manager.plugins.items():
            if plugin_info.loaded:                modules[plugin_name] = plugin_info.module
        
        print(f"📦 Loaded {len(modules)} plugin modules:")
        for name, module in modules.items():
            # Check if module has get_functions method
            if hasattr(module, 'get_functions'):
                funcs = module.get_functions()
                print(f"  - {name}: {list(funcs.keys()) if hasattr(funcs, 'keys') else len(funcs) if funcs else 0} functions")
            else:
                print(f"  - {name}: no get_functions method")
        
        # Test with weather query
        print("\n🌤️ Testing weather query...")
        conversation_history = deque([
            {"role": "user", "content": "What's the weather in Warsaw?"}
        ])
        
        response = await generate_response(
            conversation_history=conversation_history,
            tools_info="",  # Empty for function calling
            detected_language="en",
            language_confidence=1.0,
            modules=modules,
            use_function_calling=True,
            user_name="TestUser"
        )
        
        print(f"🤖 AI Response: {response}")
        
        # Parse response to check if it's proper JSON for TTS
        try:
            parsed_response = json.loads(response)
            print(f"✅ Response is valid JSON")
            print(f"📢 TTS will receive: '{parsed_response.get('text', 'No text field')}'")
            
            if parsed_response.get('function_calls_executed'):
                print("🎯 Function calls were executed!")
            else:
                print("⚠️ No function calls detected in response")
                
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {response[:200]}...")
        
        print("\n" + "=" * 60)
        
        # Test with search query
        print("\n🔍 Testing search query...")
        conversation_history = deque([
            {"role": "user", "content": "Search for recent news about artificial intelligence"}
        ])
        
        response = await generate_response(
            conversation_history=conversation_history,
            tools_info="",  # Empty for function calling
            detected_language="en",
            language_confidence=1.0,
            modules=modules,
            use_function_calling=True,
            user_name="TestUser"
        )
        
        print(f"🤖 AI Response: {response}")
        
        # Parse response to check if it's proper JSON for TTS
        try:
            parsed_response = json.loads(response)
            print(f"✅ Response is valid JSON")
            print(f"📢 TTS will receive: '{parsed_response.get('text', 'No text field')}'")
            
            if parsed_response.get('function_calls_executed'):
                print("🎯 Function calls were executed!")
            else:
                print("⚠️ No function calls detected in response")
                
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {response[:200]}...")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def test_ai_module_class():
    """Test the AIModule class used by the server."""
    print("\n🏗️ Testing AIModule class...")
    print("=" * 60)
    
    try:
        # Load config
        config = config_loader.load_config()
        
        # Initialize AI module
        ai_module = AIModule(config)        # Initialize plugin manager
        plugin_manager = PluginManager()
        await plugin_manager.discover_plugins()
        
        # Load all discovered plugins
        for plugin_name in list(plugin_manager.plugins.keys()):
            await plugin_manager.load_plugin(plugin_name)
            
        # Build modules dict from loaded plugins
        modules = {}
        for plugin_name, plugin_info in plugin_manager.plugins.items():
            if plugin_info.loaded:
                modules[plugin_name] = plugin_info.module
        
        # Test context similar to server usage
        context = {
            'user_id': 'test_user',
            'history': [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there!'}
            ],
            'available_plugins': list(modules.keys()),
            'modules': modules,
            'user_name': 'TestUser'
        }
        
        # Test weather query
        query = "What's the weather like in New York?"
        response = await ai_module.process_query(query, context)
        
        print(f"🤖 AIModule Response: {response}")
        
        # Parse and validate response
        try:
            parsed_response = json.loads(response)
            print(f"✅ AIModule response is valid JSON")
            print(f"📢 TTS will receive: '{parsed_response.get('text', 'No text field')}'")
            
            if parsed_response.get('function_calls_executed'):
                print("🎯 Function calls were executed via AIModule!")
            else:
                print("⚠️ No function calls detected in AIModule response")
                
        except json.JSONDecodeError:
            print(f"❌ AIModule response is not valid JSON: {response[:200]}...")
        
    except Exception as e:
        print(f"❌ AIModule test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests."""
    print("🚀 Starting End-to-End AI Function Calling Tests")
    print("=" * 80)
    
    await test_ai_with_function_calling()
    await test_ai_module_class()
    
    print("\n✅ End-to-End tests completed!")

if __name__ == "__main__":
    asyncio.run(main())

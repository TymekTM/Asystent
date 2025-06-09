#!/usr/bin/env python3

"""
Simple test script to test AI function calling directly
"""

import asyncio
import json
import sys
import os
from collections import deque

# Add the server directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from server.ai_module import AIModule, generate_response
from server.plugin_manager import plugin_manager  # Use the global instance
from server.config_loader import load_config

async def test_ai_function_calling():
    """Test AI function calling through the AIModule."""
    
    print("="*60)
    print("TESTING AI MODULE FUNCTION CALLING")
    print("="*60)
    
    # Load config
    config = load_config("server/server_config.json")
    
    # Initialize AI module
    ai_module = AIModule(config)
    
    # Initialize plugin manager by discovering plugins
    await plugin_manager.discover_plugins()
    print(f"Discovered plugins: {list(plugin_manager.plugins.keys())}")
    
    # Enable some plugins for user 1 (simulate user having plugins enabled)
    for plugin_name in ['core_module', 'search_module', 'weather_module', 'memory_module']:
        if plugin_name in plugin_manager.plugins:
            await plugin_manager.enable_plugin_for_user('1', plugin_name)
            print(f"Enabled plugin: {plugin_name}")
    
    # Get plugins for user 1
    user_plugins = plugin_manager.get_modules_for_user('1')
    print(f"Available plugins for user 1: {list(user_plugins.keys())}")
    
    # Test queries that should trigger function calls
    test_queries = [
        "What time is it now?",
        "Search for information about Python programming",
        "Play some relaxing music",
        "What's the weather like today?",
        "Remember that I like coffee in the morning",
        "What did I just tell you to remember?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: {query} ---")
        
        # Prepare context
        context = {
            'user_id': '1',
            'history': [],
            'available_plugins': list(user_plugins.keys()),
            'modules': user_plugins,
            'user_name': 'Test User'
        }
        
        try:
            # Process query through AI module
            response = await ai_module.process_query(query, context)
            print(f"Response: {response}")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response)
                if parsed.get("command"):
                    print(f"✓ Function call detected: {parsed['command']}")
                    print(f"  Parameters: {parsed.get('params', {})}")
                else:
                    print(f"⚠ No function call - plain text response")
            except json.JSONDecodeError:
                print(f"⚠ Non-JSON response: {response}")
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 40)

async def test_generate_response_directly():
    """Test the generate_response function directly."""
    
    print("\n" + "="*60)
    print("TESTING GENERATE_RESPONSE DIRECTLY")
    print("="*60)
    
    # Initialize plugin manager by discovering plugins
    await plugin_manager.discover_plugins()
    
    # Enable some plugins for user 1
    for plugin_name in ['core_module', 'search_module', 'weather_module', 'memory_module']:
        if plugin_name in plugin_manager.plugins:
            await plugin_manager.enable_plugin_for_user('1', plugin_name)
    
    # Get plugins for user 1  
    user_plugins = plugin_manager.get_modules_for_user('1')
    
    # Test queries
    test_queries = [
        "What time is it now?",
        "Search for Python tutorials"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Direct Test {i}: {query} ---")
        
        conversation_history = deque([
            {"role": "user", "content": query}
        ])
        
        tools_info = f"Dostępne pluginy: {', '.join(user_plugins.keys())}"
        
        try:
            response = generate_response(
                conversation_history=conversation_history,
                tools_info=tools_info,
                detected_language="pl",
                language_confidence=1.0,
                modules=user_plugins,
                use_function_calling=True,
                user_name="Test User"
            )
            
            print(f"Response: {response}")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response)
                if parsed.get("command"):
                    print(f"✓ Function call detected: {parsed['command']}")
                    print(f"  Parameters: {parsed.get('params', {})}")
                else:
                    print(f"⚠ No function call - plain text response")
            except json.JSONDecodeError:
                print(f"⚠ Non-JSON response: {response}")
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_ai_function_calling())
    asyncio.run(test_generate_response_directly())

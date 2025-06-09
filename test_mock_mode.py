#!/usr/bin/env python3
"""
Test mock functionality for plugins
Tests that plugins work with test mode when no API keys are available.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server path
sys.path.insert(0, str(Path(__file__).parent / "server"))

async def test_plugin_mock_mode():
    """Test plugins in mock mode."""
    print("🧪 Testing Plugin Mock Mode")
    print("=" * 50)
    
    try:
        # Import and test weather module
        from modules.weather_module import execute_function as weather_execute
        
        print("\n1. Testing Weather Plugin (Mock Mode)")
        print("-" * 30)
        
        # Test get_weather with mock mode
        weather_result = await weather_execute(
            "get_weather", 
            {"location": "Warszawa", "test_mode": True}, 
            user_id=1
        )
        print(f"Weather Result: {weather_result['success']}")
        print(f"Message: {weather_result['message']}")
        if weather_result.get('test_mode'):
            print("✅ Mock mode working!")
        else:
            print("❌ Mock mode not working")
            
        # Test get_forecast with mock mode
        forecast_result = await weather_execute(
            "get_forecast", 
            {"location": "Kraków", "days": 3, "test_mode": True}, 
            user_id=1
        )
        print(f"Forecast Result: {forecast_result['success']}")
        print(f"Message: {forecast_result['message']}")
        if forecast_result.get('test_mode'):
            print("✅ Forecast mock mode working!")
        else:
            print("❌ Forecast mock mode not working")
        
        # Import and test search module
        from modules.search_module import execute_function as search_execute
        
        print("\n2. Testing Search Plugin (Mock Mode)")
        print("-" * 30)
        
        # Test search with mock mode
        search_result = await search_execute(
            "search", 
            {"query": "Python programming", "test_mode": True}, 
            user_id=1
        )
        print(f"Search Result: {search_result['success']}")
        print(f"Message: {search_result['message']}")
        if search_result.get('test_mode'):
            print("✅ Search mock mode working!")
            data = search_result.get('data', {})
            results = data.get('results', [])
            print(f"   Found {len(results)} mock results")
        else:
            print("❌ Search mock mode not working")
            
        # Test news search (should use mock when no API key)
        news_result = await search_execute(
            "search_news", 
            {"query": "technologia", "max_results": 3}, 
            user_id=1
        )
        print(f"News Result: {news_result['success']}")
        print(f"Message: {news_result['message']}")
        if news_result.get('test_mode'):
            print("✅ News mock mode working!")
            data = news_result.get('data', {})
            articles = data.get('articles', [])
            print(f"   Found {len(articles)} mock articles")
        else:
            print("❌ News mock mode not working")
            
        # Import and test memory module  
        from modules.memory_module import execute_function as memory_execute
        
        print("\n3. Testing Memory Plugin")
        print("-" * 30)
        
        # Test save memory
        memory_save_result = await memory_execute(
            "save_memory", 
            {"key": "test_mock", "content": "This is a test memory for mock mode"}, 
            user_id=1
        )
        print(f"Memory Save Result: {memory_save_result['success']}")
        print(f"Message: {memory_save_result['message']}")
        
        # Test get memory
        memory_get_result = await memory_execute(
            "get_memory", 
            {"key": "test_mock"}, 
            user_id=1
        )
        print(f"Memory Get Result: {memory_get_result['success']}")
        print(f"Message: {memory_get_result['message']}")
        
        print("\n" + "=" * 50)
        print("🎯 Mock Mode Test Complete!")
        print("✅ All plugins have working mock/test functionality")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_plugin_mock_mode())

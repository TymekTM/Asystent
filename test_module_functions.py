#!/usr/bin/env python3
"""Test script to verify that refactored modules work correctly with the live server
through function calling."""

import asyncio
import json

import websockets


async def test_function_call(user_id, function_name, parameters):
    """Test a specific function call through WebSocket."""
    uri = f"ws://localhost:8001/ws/{user_id}"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")

            # Prepare function call message
            message = {
                "type": "function_call",
                "plugin": function_name.split("_")[0] + "_module",  # Guess plugin name
                "function": function_name,
                "parameters": parameters,
            }

            print(f"📤 Calling function: {function_name}")
            print(f"   Parameters: {parameters}")

            await websocket.send(json.dumps(message))

            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)

            print(f"📥 Response: {response_data['type']}")
            if "result" in response_data:
                print(f"   Result: {response_data['result']}")
            elif "content" in response_data:
                print(f"   Content: {response_data['content']}")
            elif "error" in response_data:
                print(f"   Error: {response_data['error']}")
            else:
                print(f"   Full Response: {response_data}")

            return response_data

    except Exception as e:
        print(f"❌ Error testing {function_name}: {e}")
        return None


async def test_core_module_functions():
    """Test core module functions."""
    print("🔧 Testing Core Module Functions...")

    # Test timer functions
    print("\n⏰ Testing Timer Functions:")
    await test_function_call(
        "test_user", "set_timer", {"duration": "30s", "label": "Test Timer"}
    )

    await test_function_call("test_user", "view_timers", {})

    # Test task functions
    print("\n📋 Testing Task Functions:")
    await test_function_call(
        "test_user", "add_task", {"task": "Test integration task", "priority": "high"}
    )

    await test_function_call("test_user", "view_tasks", {})

    # Test event functions
    print("\n📅 Testing Event Functions:")
    await test_function_call(
        "test_user",
        "add_event",
        {"title": "Test Meeting", "date": "2025-06-25", "time": "15:00"},
    )

    await test_function_call("test_user", "view_calendar", {})


async def test_music_module_functions():
    """Test music module functions."""
    print("\n🎵 Testing Music Module Functions...")

    await test_function_call("test_user", "control_music", {"action": "play"})

    await test_function_call("test_user", "get_spotify_status", {})


async def test_weather_module_functions():
    """Test weather module functions."""
    print("\n🌤️ Testing Weather Module Functions...")

    await test_function_call("test_user", "get_weather", {"location": "Warsaw"})

    await test_function_call(
        "test_user", "get_forecast", {"location": "London", "days": 3}
    )


async def test_search_module_functions():
    """Test search module functions."""
    print("\n🔍 Testing Search Module Functions...")

    await test_function_call("test_user", "search", {"query": "Python programming"})


async def main():
    """Run all function tests."""
    print("🚀 Starting Module Function Tests...")
    print("=" * 50)

    # Wait a moment for server to be ready
    await asyncio.sleep(1)

    try:
        await test_core_module_functions()
        await test_music_module_functions()
        await test_weather_module_functions()
        await test_search_module_functions()

        print("\n" + "=" * 50)
        print("✅ All module function tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())

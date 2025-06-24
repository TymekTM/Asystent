#!/usr/bin/env python3
"""Test script that enables plugins for a user and then tests function calling."""

import asyncio
import json

import websockets


async def enable_plugin_for_user(user_id, plugin_name):
    """Enable a plugin for a user via WebSocket."""
    uri = f"ws://localhost:8001/ws/{user_id}"

    try:
        async with websockets.connect(uri) as websocket:
            message = {
                "type": "plugin_toggle",
                "plugin": plugin_name,
                "action": "enable",
            }

            print(f"🔌 Enabling plugin: {plugin_name}")
            await websocket.send(json.dumps(message))

            response = await websocket.recv()
            response_data = json.loads(response)

            if response_data.get("type") == "plugin_toggled":
                print(f"✅ Plugin {plugin_name} enabled successfully")
                return True
            else:
                print(f"❌ Failed to enable plugin {plugin_name}: {response_data}")
                return False

    except Exception as e:
        print(f"❌ Error enabling plugin {plugin_name}: {e}")
        return False


async def test_function_call(user_id, plugin_name, function_name, parameters):
    """Test a specific function call through WebSocket."""
    uri = f"ws://localhost:8001/ws/{user_id}"

    try:
        async with websockets.connect(uri) as websocket:
            message = {
                "type": "function_call",
                "plugin": plugin_name,
                "function": function_name,
                "parameters": parameters,
            }

            print(f"📤 Calling function: {plugin_name}.{function_name}")

            await websocket.send(json.dumps(message))

            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)

            print(f"📥 Response: {response_data['type']}")
            if response_data.get("type") != "error":
                print("✅ Function call successful")
                if "result" in response_data:
                    print(f"   Result preview: {str(response_data['result'])[:200]}...")
                return True
            else:
                print(
                    f"❌ Function call failed: {response_data.get('message', 'Unknown error')}"
                )
                return False

    except Exception as e:
        print(f"❌ Error testing {plugin_name}.{function_name}: {e}")
        return False


async def main():
    """Run comprehensive plugin enabling and function testing."""
    print("🚀 Starting Plugin Enable & Function Test...")
    print("=" * 60)

    user_id = "test_user"

    # First, enable all plugins
    plugins_to_enable = [
        "core_module",
        "music_module",
        "weather_module",
        "search_module",
    ]

    print("🔌 Enabling plugins for user...")
    print("-" * 30)

    for plugin in plugins_to_enable:
        await enable_plugin_for_user(user_id, plugin)
        await asyncio.sleep(0.5)  # Small delay

    print("\n⏳ Waiting for plugins to initialize...")
    await asyncio.sleep(2)

    # Now test functions
    print("\n🧪 Testing functions...")
    print("-" * 30)

    test_cases = [
        {
            "plugin": "core_module",
            "function": "read_file",
            "parameters": {"file_path": "f:/Asystent/README.md", "max_lines": 3},
        },
        {
            "plugin": "core_module",
            "function": "set_timer",
            "parameters": {"duration": "10s", "label": "Test Timer"},
        },
        {
            "plugin": "music_module",
            "function": "get_random_music",
            "parameters": {"genre": "pop", "limit": 1},
        },
        {
            "plugin": "weather_module",
            "function": "get_weather",
            "parameters": {"location": "Warsaw"},
        },
        {
            "plugin": "search_module",
            "function": "web_search",
            "parameters": {"query": "Python programming", "max_results": 1},
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(
            f"\n🧪 Test {i}/{len(test_cases)}: {test_case['plugin']}.{test_case['function']}"
        )
        print("-" * 40)

        success = await test_function_call(
            user_id, test_case["plugin"], test_case["function"], test_case["parameters"]
        )

        results.append(
            {
                "test": f"{test_case['plugin']}.{test_case['function']}",
                "success": success,
            }
        )

        await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print("=" * 60)

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")

    if successful < total:
        print("\n❌ Failed Tests:")
        for result in results:
            if not result["success"]:
                print(f"   - {result['test']}")

    if successful == total:
        print("\n🎉 All tests passed! Plugin system is working correctly.")
        print("✅ Server-client integration verified successfully!")
    else:
        print(f"\n⚠️  {total - successful} test(s) failed.")
        print("Check server logs for more details.")


if __name__ == "__main__":
    asyncio.run(main())

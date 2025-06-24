#!/usr/bin/env python3
"""Test script to verify that refactored modules work correctly with the live server
through function calling."""

import asyncio
import json

import websockets


async def test_function_call(user_id, plugin_name, function_name, parameters):
    """Test a specific function call through WebSocket."""
    uri = f"ws://localhost:8001/ws/{user_id}"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")

            # Prepare function call message
            message = {
                "type": "function_call",
                "plugin": plugin_name,
                "function": function_name,
                "parameters": parameters,
            }

            print(f"📤 Calling function: {plugin_name}.{function_name}")
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
            elif response_data["type"] == "error":
                print(
                    f"   Error Message: {response_data.get('message', 'Unknown error')}"
                )
            else:
                print(f"   Full Response: {response_data}")

            return response_data

    except Exception as e:
        print(f"❌ Error testing {plugin_name}.{function_name}: {e}")
        return None


async def main():
    """Run comprehensive module function tests."""
    print("🚀 Starting Module Function Tests...")
    print("=" * 50)

    user_id = "test_user"

    # Test różnych funkcji modułów
    test_cases = [
        {
            "plugin": "core_module",
            "function": "read_file",
            "parameters": {"file_path": "f:/Asystent/README.md", "max_lines": 5},
        },
        {
            "plugin": "core_module",
            "function": "set_timer",
            "parameters": {"duration": "30s", "label": "Test Timer"},
        },
        {"plugin": "core_module", "function": "view_timers", "parameters": {}},
        {
            "plugin": "core_module",
            "function": "add_task",
            "parameters": {"task": "Test integration task", "priority": "high"},
        },
        {"plugin": "core_module", "function": "view_tasks", "parameters": {}},
        {
            "plugin": "music_module",
            "function": "get_random_music",
            "parameters": {"genre": "pop", "limit": 1},
        },
        {
            "plugin": "music_module",
            "function": "search_music",
            "parameters": {"query": "test song", "limit": 2},
        },
        {
            "plugin": "weather_module",
            "function": "get_weather",
            "parameters": {"location": "Warsaw"},
        },
        {
            "plugin": "weather_module",
            "function": "get_forecast",
            "parameters": {"location": "Warsaw", "days": 3},
        },
        {
            "plugin": "search_module",
            "function": "web_search",
            "parameters": {"query": "Python programming", "max_results": 2},
        },
        {
            "plugin": "search_module",
            "function": "search_news",
            "parameters": {"query": "artificial intelligence", "limit": 2},
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(
            f"\n🧪 Test {i}/{len(test_cases)}: {test_case['plugin']}.{test_case['function']}"
        )
        print("-" * 40)

        result = await test_function_call(
            user_id, test_case["plugin"], test_case["function"], test_case["parameters"]
        )

        results.append(
            {
                "test": f"{test_case['plugin']}.{test_case['function']}",
                "success": result is not None and result.get("type") != "error",
                "result": result,
            }
        )

        # Small delay between tests
        await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY:")
    print("=" * 50)

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")

    if successful < total:
        print("\n❌ Failed Tests:")
        for result in results:
            if not result["success"]:
                error_msg = "Unknown error"
                if result["result"] and "message" in result["result"]:
                    error_msg = result["result"]["message"]
                print(f"   - {result['test']}: {error_msg}")

    if successful == total:
        print("\n🎉 All tests passed! Function calling system is working correctly.")
    else:
        print(
            f"\n⚠️  {total - successful} test(s) failed. Check server logs for details."
        )


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Test integracji AI z rzeczywistym zapytaniem."""

import asyncio
import json

import websockets


async def test_ai_integration():
    """Test rzeczywistego AI query z numerycznym user_id."""

    print("🧠 Testing AI Integration...")

    # Test 1: Numeryczny user_id (powinien działać)
    print("Test 1: Numeric user_id")
    try:
        async with websockets.connect("ws://localhost:8001/ws/12345") as ws:
            message = {
                "type": "ai_query",
                "query": "Hello, how are you?",
                "context": {},
            }

            await ws.send(json.dumps(message))
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            response_data = json.loads(response)

            print(f"✅ Numeric user_id response: {response_data.get('type')}")
            if response_data.get("type") == "ai_response":
                print(f"   Content: {response_data.get('response', '')[:100]}...")
    except Exception as e:
        print(f"❌ Numeric user_id failed: {e}")

    await asyncio.sleep(1)

    # Test 2: String user_id (test naszej poprawki)
    print("Test 2: String user_id")
    try:
        async with websockets.connect("ws://localhost:8001/ws/test_user_string") as ws:
            message = {
                "type": "ai_query",
                "query": "What is the weather like?",
                "context": {},
            }

            await ws.send(json.dumps(message))
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            response_data = json.loads(response)

            print(f"✅ String user_id response: {response_data.get('type')}")
            if response_data.get("type") == "ai_response":
                print(f"   Content: {response_data.get('response', '')[:100]}...")
    except Exception as e:
        print(f"❌ String user_id failed: {e}")

    print("🎯 AI Integration Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_ai_integration())

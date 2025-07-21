#!/usr/bin/env python3
"""Practical test of ask_for_clarification function through real API calls.

Tests actual AI integration with clarification scenarios.
"""

import asyncio
import json
from datetime import datetime

import requests
import websockets


async def test_websocket_conversation():
    """Test asking for clarification through WebSocket like real conversation."""
    print("🚀 Testing ask_for_clarification through WebSocket conversation")
    print("=" * 60)

    try:
        # Connect to WebSocket
        uri = "ws://localhost:8001/ws/test_user"  # WebSocket requires user_id
        print(f"📡 Connecting to {uri}...")

        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")

            # Test scenarios that should trigger clarification
            test_cases = [
                {
                    "name": "Weather without location",
                    "message": "jaka jest pogoda",
                    "expected_clarification": True,
                },
                {
                    "name": "Timer without duration",
                    "message": "ustaw timer",
                    "expected_clarification": True,
                },
                {
                    "name": "Music without specification",
                    "message": "włącz muzykę",
                    "expected_clarification": True,
                },
                {
                    "name": "Clear request (should not trigger)",
                    "message": "jaka jest pogoda w Warszawie",
                    "expected_clarification": False,
                },
            ]

            for i, test_case in enumerate(test_cases, 1):
                print(f"\n📝 Test {i}: {test_case['name']}")
                print(f"   Message: '{test_case['message']}'")

                # Send message
                message = {
                    "type": "query",  # Changed from "message" to "query"
                    "query": test_case["message"],  # Changed from "text" to "query"
                    "context": {},
                    "user_id": "test_user",
                    "timestamp": datetime.now().isoformat(),
                }

                await websocket.send(json.dumps(message))
                print("   📤 Message sent")

                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)

                    print(f"   📥 Response type: {response_data.get('type', 'unknown')}")

                    if response_data.get("type") == "clarification_request":
                        print("   🔍 CLARIFICATION REQUESTED!")
                        print(f"   Question: {response_data.get('question', 'N/A')}")
                        print(f"   Context: {response_data.get('context', 'N/A')}")

                        # Check TTS behavior
                        actions = response_data.get("actions", {})
                        if actions.get("wait_for_tts_completion"):
                            print("   ✅ Correct: Will wait for TTS completion")
                        else:
                            print("   ❌ Wrong: Should wait for TTS completion")

                        if actions.get("start_recording_after_tts"):
                            print("   ✅ Correct: Will start recording after TTS")
                        else:
                            print("   ❌ Wrong: Should start recording after TTS")

                        if test_case["expected_clarification"]:
                            print("   ✅ Expected clarification - PASSED")
                        else:
                            print("   ❌ Unexpected clarification - FAILED")

                    elif response_data.get("type") == "ai_response":
                        print("   💬 AI response received")
                        # Print the actual response to see what AI said
                        message = response_data.get("message", "")
                        print(
                            f"   AI said: '{message[:100]}{'...' if len(message) > 100 else ''}'"
                        )

                        if test_case["expected_clarification"]:
                            print(
                                "   ❌ Expected clarification but got normal response - FAILED"
                            )
                            print(
                                "   💡 AI should have used ask_for_clarification function!"
                            )
                        else:
                            print("   ✅ Expected normal response - PASSED")
                    elif response_data.get("type") == "response":
                        print("   💬 Normal response received")
                        if test_case["expected_clarification"]:
                            print(
                                "   ❌ Expected clarification but got normal response - FAILED"
                            )
                        else:
                            print("   ✅ Expected normal response - PASSED")
                    else:
                        print(
                            f"   ❓ Unexpected response type: {response_data.get('type')}"
                        )

                except TimeoutError:
                    print("   ⏰ Timeout waiting for response")
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON decode error: {e}")

                # Wait between tests
                await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")


def test_server_health():
    """Test if server is responding correctly."""
    print("🔧 Testing server health...")

    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server health check passed")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server health check error: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Practical ask_for_clarification testing")
    print("=" * 60)

    # Check server health first
    if not test_server_health():
        print("❌ Server is not responding. Please check if server is running.")
        return

    print("\n🔍 Testing clarification scenarios...")
    await test_websocket_conversation()

    print("\n" + "=" * 60)
    print("✅ Practical testing completed!")
    print("\nExpected behavior:")
    print("- Unclear requests should trigger clarification_request")
    print("- TTS should complete before recording starts")
    print("- Clear requests should get normal responses")


if __name__ == "__main__":
    asyncio.run(main())

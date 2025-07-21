#!/usr/bin/env python3
"""Test przykładowej konwersacji z AI używając ask_for_clarification."""

import asyncio
import json
import os
import sys
from pathlib import Path

import websockets

# Add server path to imports
sys.path.insert(0, str(Path(__file__).parent / "server"))


async def test_ai_clarification_conversation():
    """Test rozmowy z AI używając ask_for_clarification."""

    print("🤖 Testing AI clarification conversation via WebSocket...")
    print("⚠️  Make sure the server is running first!")
    print()

    # Test scenarios where AI should ask for clarification
    test_scenarios = [
        {
            "name": "Weather without location",
            "query": "Jaka jest pogoda?",
            "expected": "AI should ask for location",
        },
        {
            "name": "Music without specification",
            "query": "Puść muzykę",
            "expected": "AI should ask what music to play",
        },
        {
            "name": "Timer without duration",
            "query": "Postaw timer",
            "expected": "AI should ask for duration",
        },
        {
            "name": "Reminder without details",
            "query": "Przypomnij mi",
            "expected": "AI should ask what to remind and when",
        },
    ]

    try:
        # Connect to WebSocket server
        uri = "ws://localhost:8001/ws/test_user"

        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")

            # Wait for handshake
            handshake = await websocket.recv()
            print(f"📡 Handshake: {handshake}")

            # Test each scenario
            for i, scenario in enumerate(test_scenarios, 1):
                print(f"\n{'='*60}")
                print(f"🧪 Test {i}: {scenario['name']}")
                print(f"📝 Query: '{scenario['query']}'")
                print(f"🎯 Expected: {scenario['expected']}")
                print("-" * 60)

                # Send query
                message = {
                    "type": "ai_query",
                    "query": scenario["query"],
                    "timestamp": "2025-07-21T15:00:00.000Z",
                }

                await websocket.send(json.dumps(message))
                print(f"📤 Sent: {scenario['query']}")

                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    response_data = json.loads(response)

                    print(f"📥 Response type: {response_data.get('type', 'unknown')}")

                    if response_data.get("type") == "clarification_request":
                        # This is what we want to see!
                        clarification = response_data.get("data", {})
                        print("🎉 SUCCESS: AI asked for clarification!")
                        print(
                            f"❓ Question: {clarification.get('question', 'No question')}"
                        )
                        print(
                            f"📝 Context: {clarification.get('context', 'No context')}"
                        )
                        print(f"🔧 Actions: {clarification.get('actions', {})}")

                        # Test response with clarification
                        if scenario["name"] == "Weather without location":
                            clarification_response = {
                                "type": "ai_query",
                                "query": "Warszawa",
                                "timestamp": "2025-07-21T15:00:10.000Z",
                            }
                        elif scenario["name"] == "Music without specification":
                            clarification_response = {
                                "type": "ai_query",
                                "query": "Nagraj Halsey",
                                "timestamp": "2025-07-21T15:00:10.000Z",
                            }
                        else:
                            clarification_response = {
                                "type": "ai_query",
                                "query": "5 minut",
                                "timestamp": "2025-07-21T15:00:10.000Z",
                            }

                        print(
                            f"🔄 Sending clarification: {clarification_response['query']}"
                        )
                        await websocket.send(json.dumps(clarification_response))

                        # Wait for final response
                        final_response = await asyncio.wait_for(
                            websocket.recv(), timeout=30.0
                        )
                        final_data = json.loads(final_response)
                        print(f"✅ Final response: {final_data.get('type', 'unknown')}")

                    elif response_data.get("type") == "ai_response":
                        # Regular response - check if it's asking for clarification in text
                        ai_response = response_data.get("data", {}).get("response", "")
                        try:
                            parsed_ai_response = json.loads(ai_response)
                            ai_text = parsed_ai_response.get("text", "")
                        except:
                            ai_text = ai_response

                        print(f"🤖 AI Response: {ai_text[:200]}...")

                        # Check if AI mentioned needing more info
                        clarification_indicators = [
                            "nie podał",
                            "jakiej",
                            "jakiego",
                            "gdzie",
                            "kiedy",
                            "więcej",
                            "sprecyzuj",
                            "dla jakiego miasta",
                            "co dokładnie",
                        ]

                        if any(
                            indicator in ai_text.lower()
                            for indicator in clarification_indicators
                        ):
                            print(
                                "✅ GOOD: AI recognized need for clarification in text"
                            )
                        else:
                            print("⚠️  AI did not explicitly ask for clarification")

                    else:
                        print(f"❓ Unexpected response type: {response_data}")

                except TimeoutError:
                    print("⏰ Timeout waiting for response")
                except Exception as e:
                    print(f"❌ Error: {e}")

                # Wait between tests
                await asyncio.sleep(2)

            print(f"\n{'='*60}")
            print("🎉 All clarification tests completed!")

    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure the server is running: python manage.py start-server")


if __name__ == "__main__":
    asyncio.run(test_ai_clarification_conversation())

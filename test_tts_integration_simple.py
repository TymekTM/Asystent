#!/usr/bin/env python3
"""Prosty test integracji TTS z rzeczywistym klientem."""

import asyncio
import json

import websockets
from websockets.exceptions import WebSocketException


async def test_tts_integration():
    """Test rzeczywistej integracji TTS poprzez WebSocket."""

    print("🔊 Testing TTS Integration...")

    try:
        uri = "ws://localhost:8001/ws/test_tts_user"
        print(f"Connecting to: {uri}")

        async with websockets.connect(uri, ping_interval=None) as ws:
            print("✅ WebSocket connected")

            # Test zapytanie które powinno wywołać TTS
            message = {
                "type": "ai_query",
                "query": "Powiedz mi coś ciekawego",
                "context": {"user_name": "TTS Tester"},
            }

            print(f"Sending TTS test query: {message['query']}")
            await ws.send(json.dumps(message))

            print("Waiting for AI response...")
            response = await asyncio.wait_for(ws.recv(), timeout=15.0)
            response_data = json.loads(response)

            print(f"Response type: {response_data.get('type')}")

            if response_data.get("type") == "ai_response":
                ai_response = response_data.get("response", "")
                print(f"✅ AI Response received (length: {len(ai_response)})")
                print(f"   Preview: {ai_response[:100]}...")

                # Sprawdź czy odpowiedź zawiera tekst
                if ai_response and len(ai_response) > 10:
                    print("✅ TTS Integration: AI generated meaningful text response")

                    # Sprawdź czy odpowiedź jest w formacie JSON (z komendami TTS)
                    try:
                        parsed_response = json.loads(ai_response)
                        if (
                            isinstance(parsed_response, dict)
                            and "text" in parsed_response
                        ):
                            print(
                                "✅ TTS Integration: Response in proper JSON format for TTS"
                            )
                            print(f"   TTS Text: {parsed_response['text'][:100]}...")
                        else:
                            print(
                                "⚠️  TTS Integration: Response not in JSON format (may still work)"
                            )
                    except json.JSONDecodeError:
                        print(
                            "⚠️  TTS Integration: Response is plain text (may still work)"
                        )

                    return True
                else:
                    print("❌ TTS Integration: AI response too short or empty")
                    return False

            elif response_data.get("type") == "error":
                print(
                    f"❌ TTS Integration: Error from server: {response_data.get('message', '')}"
                )
                return False
            else:
                print(
                    f"❌ TTS Integration: Unexpected response type: {response_data.get('type')}"
                )
                return False

    except WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except TimeoutError:
        print("❌ Timeout waiting for response")
        return False
    except Exception as e:
        print(f"❌ TTS Integration test failed: {e}")
        return False


async def test_voice_command_simulation():
    """Test symulacji komendy głosowej."""

    print("\n🎤 Testing Voice Command Simulation...")

    try:
        uri = "ws://localhost:8001/ws/test_voice_user"

        async with websockets.connect(uri, ping_interval=None) as ws:
            print("✅ WebSocket connected for voice test")

            # Symulacja komendy głosowej
            voice_message = {
                "type": "ai_query",
                "query": "Jaka jest dzisiaj pogoda?",
                "context": {"input_type": "voice", "user_name": "Voice Tester"},
            }

            print(f"Sending voice command: {voice_message['query']}")
            await ws.send(json.dumps(voice_message))

            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            response_data = json.loads(response)

            if response_data.get("type") == "ai_response":
                print("✅ Voice command processed successfully")
                return True
            else:
                print(f"❌ Voice command failed: {response_data}")
                return False

    except Exception as e:
        print(f"❌ Voice command test failed: {e}")
        return False


async def main():
    """Uruchom wszystkie testy TTS."""

    print("🧪 Starting TTS Integration Tests...")
    print("=" * 50)

    # Test 1: Podstawowa integracja TTS
    tts_test_result = await test_tts_integration()

    # Test 2: Symulacja komendy głosowej
    voice_test_result = await test_voice_command_simulation()

    print("\n" + "=" * 50)
    print("🎯 TTS Integration Test Results:")
    print(f"   Basic TTS Integration: {'✅ PASS' if tts_test_result else '❌ FAIL'}")
    print(f"   Voice Command Simulation: {'✅ PASS' if voice_test_result else '❌ FAIL'}")

    if tts_test_result and voice_test_result:
        print("\n🎉 All TTS Integration Tests PASSED!")
        return True
    else:
        print("\n⚠️  Some TTS Integration Tests FAILED!")
        print("   - Check if the server is running on localhost:8001")
        print("   - Ensure AI module is properly configured")
        print("   - Verify TTS system is available")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)

#!/usr/bin/env python3
"""Prosty test overlay - wysyła dane do działającego klienta"""

import asyncio
import json

import websockets


async def simple_test():
    print("🧪 PROSTY TEST OVERLAY")
    print("======================")

    try:
        print("🔌 Łączę się z klientem WebSocket...")
        uri = "ws://localhost:6001"

        async with websockets.connect(uri) as websocket:
            print("✅ Połączono!")

            # Test 1 - wymuszenie widoczności
            print("\n📤 Test 1: Wymuszenie widoczności overlay")
            test1 = {
                "type": "status",
                "data": {
                    "status": "🔴 WIDOCZNY TEST",
                    "text": "OVERLAY JEST WIDOCZNY!",
                    "is_listening": False,
                    "is_speaking": False,
                    "wake_word_detected": False,
                    "show_content": True,
                    "overlay_enabled": True,
                    "overlay_visible": True,
                },
            }
            await websocket.send(json.dumps(test1))
            print("⏰ Czekam 10 sekund - sprawdź czy overlay jest widoczny!")
            await asyncio.sleep(10)

            # Test 2 - stan mówienia
            print("\n📤 Test 2: Stan mówienia")
            test2 = {
                "type": "status",
                "data": {
                    "status": "🗣️ MÓWIĘ",
                    "text": "Asystent teraz mówi!",
                    "is_listening": False,
                    "is_speaking": True,
                    "wake_word_detected": False,
                    "show_content": True,
                    "overlay_enabled": True,
                },
            }
            await websocket.send(json.dumps(test2))
            print("⏰ Czekam 8 sekund...")
            await asyncio.sleep(8)

            # Test 3 - ukrycie
            print("\n📤 Test 3: Ukrywanie overlay")
            test3 = {
                "type": "status",
                "data": {
                    "status": "ready",
                    "text": "",
                    "is_listening": False,
                    "is_speaking": False,
                    "wake_word_detected": False,
                    "show_content": False,
                    "overlay_enabled": True,
                    "overlay_visible": False,
                },
            }
            await websocket.send(json.dumps(test3))
            print("✅ Overlay powinien się ukryć")

    except Exception as e:
        print(f"❌ Błąd: {e}")


if __name__ == "__main__":
    asyncio.run(simple_test())

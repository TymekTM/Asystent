#!/usr/bin/env python3
"""
Prosty test WebSocket serwera - sprawdza czy problem jest w implementacji
"""

import asyncio
import json

import websockets


async def simple_handler(websocket, path):
    """Prosty handler WebSocket."""
    print(f"✅ Połączenie: {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"📥 Otrzymano: {message}")
            # Echo z powrotem
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("❌ Połączenie zamknięte")
    except Exception as e:
        print(f"❌ Błąd: {e}")


async def start_simple_server():
    """Uruchom prosty serwer WebSocket."""
    print("🚀 Uruchamianie prostego serwera WebSocket na 127.0.0.1:6001")

    try:
        server = await websockets.serve(simple_handler, "127.0.0.1", 6001)
        print("✅ Serwer uruchomiony!")

        # Test połączenia po 2 sekundach
        await asyncio.sleep(2)

        print("🔍 Testuję połączenie z serwerem...")
        try:
            async with websockets.connect("ws://127.0.0.1:6001") as websocket:
                print("✅ Połączenie udane!")
                await websocket.send("Test message")
                response = await websocket.recv()
                print(f"📥 Odpowiedź: {response}")
                return True
        except Exception as e:
            print(f"❌ Błąd połączenia: {e}")
            return False

    except Exception as e:
        print(f"❌ Błąd serwera: {e}")
        return False


async def main():
    """Test główny."""
    print("🧪 TEST PROSTEGO WEBSOCKET SERWERA")
    print("=" * 50)

    result = await start_simple_server()

    if result:
        print("\n🎉 WebSocket działa poprawnie!")
    else:
        print("\n❌ Problem z WebSocket")

    return result


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\nWynik: {'SUKCES' if success else 'BŁĄD'}")
    except KeyboardInterrupt:
        print("\n🛑 Test przerwany")
    except Exception as e:
        print(f"\n💥 Błąd: {e}")

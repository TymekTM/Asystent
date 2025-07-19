#!/usr/bin/env python3
"""
Debug komunikacji overlay
"""

import asyncio
import websockets
import json

async def debug_communication():
    print("🔧 DEBUG KOMUNIKACJI OVERLAY")
    print("============================")
    
    try:
        # Sprawdź WebSocket server klienta
        print("🔌 Sprawdzam WebSocket server klienta...")
        uri = "ws://localhost:6001"
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket server klienta działa")
            
            # Nasłuchuj wiadomości od overlay
            print("👂 Nasłuchuję wiadomości od overlay...")
            
            # Wyślij stan testowy
            test_status = {
                "type": "status", 
                "data": {
                    "status": "DEBUG TEST",
                    "text": "🔴 Test komunikacji - overlay powinien to zobaczyć!",
                    "is_listening": True,
                    "is_speaking": False,
                    "wake_word_detected": True,
                    "show_content": True,
                    "overlay_enabled": True,
                    "overlay_visible": True
                }
            }
            
            print(f"📤 Wysyłam test: {test_status}")
            await websocket.send(json.dumps(test_status))
            
            # Czekaj na odpowiedź
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"📨 Otrzymano od overlay: {response}")
            except asyncio.TimeoutError:
                print("⏰ Brak odpowiedzi od overlay w 5 sekund")
            
            # Poczekaj chwilę i sprawdź czy overlay reaguje
            print("⏳ Czekam 10 sekund - sprawdź czy overlay się zmienił...")
            await asyncio.sleep(10)
            
    except Exception as e:
        print(f"❌ Błąd: {e}")

if __name__ == "__main__":
    asyncio.run(debug_communication())

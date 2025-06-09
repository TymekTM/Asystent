#!/usr/bin/env python3
"""
Szybki test AI - sprawdza czy AI odpowiada i używa gpt-4.1-nano
"""

import asyncio
import websockets
import json

async def test_ai():
    """Test AI przez WebSocket"""
    uri = "ws://localhost:8001/ws/test_client"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Połączono z serwerem")
            
            # Test AI query
            ai_message = {
                "type": "ai_query",
                "query": "Powiedz coś krótko po polsku i pokaż jaki model używasz",
                "timestamp": 12345
            }
            
            await websocket.send(json.dumps(ai_message))
            print("📤 Wysłano zapytanie AI")
            
            # Oczekiwanie na odpowiedź
            response = await websocket.recv()
            data = json.loads(response)
            
            print("📥 Odpowiedź AI:")
            if data.get("type") == "ai_response":
                response_data = json.loads(data.get("response", "{}"))
                print(f"   Text: {response_data.get('text', 'Brak tekstu')}")
                print(f"   Model: {data.get('model', 'Nieznany')}")
            else:
                print(f"   Nieoczekiwana odpowiedź: {data}")
            
    except Exception as e:
        print(f"❌ Błąd: {e}")

if __name__ == "__main__":
    print("🚀 Test AI z gpt-4.1-nano")
    asyncio.run(test_ai())

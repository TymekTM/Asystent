"""
Test end-to-end systemu GAJA.
"""

import asyncio
import json
import websockets
import time

async def test_system():
    """Test pełnego systemu klient-serwer."""
    print("🧪 Testing GAJA system end-to-end...")
    
    try:
        # Połącz się z serwerem jak klient
        uri = "ws://localhost:8000/ws/test"
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to server")
            
            # Wyślij test query
            test_message = {
                "type": "ai_query",
                "data": {
                    "query": "Przetestuj system",
                    "context": {
                        "source": "test",
                        "user_name": "Test User"
                    }
                }
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent test query")
            
            # Czekaj na odpowiedź
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(response)
            
            print(f"📥 Received response: {data['type']}")
            if data['type'] == 'ai_response':
                print(f"🤖 AI Response: {data.get('response', 'No response')}")
                print("✅ System test PASSED!")
            else:
                print(f"❌ Unexpected response type: {data}")
                
    except asyncio.TimeoutError:
        print("⏰ Test timed out - server may not be responding")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_system())

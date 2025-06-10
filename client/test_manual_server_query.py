#!/usr/bin/env python3
"""
Test manual wakeword trigger
"""

import asyncio
import json
import time
import websockets
import threading

async def simulate_wakeword_trigger():
    """Symuluj wykrycie wakeword i zapytanie do serwera"""
    
    # Connect to server
    uri = "ws://localhost:8000/ws/1"
    
    print("📡 Connecting to server...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to server")
            
            # Send a test query
            test_query = "Jaka jest pogoda w Warszawie?"
            message = {
                "type": "ai_query",
                "query": test_query,
                "context": {
                    "source": "voice",
                    "user_name": "Test User"
                }
            }
            
            print(f"📤 Sending query: {test_query}")
            await websocket.send(json.dumps(message))
            
            # Wait for response
            print("⏳ Waiting for AI response...")
            response = await websocket.recv()
            
            try:
                response_data = json.loads(response)
                print(f"📥 Server response: {response_data}")
                
                if response_data.get('type') == 'ai_response':
                    ai_response = response_data.get('response', '')
                    print(f"🤖 AI Response: {ai_response}")
                    
                    # Parse AI response if it's JSON
                    try:
                        if isinstance(ai_response, str):
                            ai_data = json.loads(ai_response)
                            text = ai_data.get('text', '')
                            if text:
                                print(f"📝 AI Text: {text}")
                                print("✅ Full pipeline test completed successfully!")
                            else:
                                print("❌ No text in AI response")
                        else:
                            print(f"❌ Unexpected response format: {type(ai_response)}")
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse AI response JSON: {e}")
                        print(f"Raw response: {ai_response}")
                else:
                    print(f"❌ Unexpected response type: {response_data.get('type')}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse server response: {e}")
                print(f"Raw response: {response}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_wakeword_trigger())

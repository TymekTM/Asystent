#!/usr/bin/env python3
"""
Quick test to verify client-server communication.
"""

import asyncio
import json
import websockets
import time

async def test_connection():
    """Test the WebSocket connection to the server."""
    try:
        # Connect to server
        uri = "ws://localhost:8000/ws/test_user"
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to server!")
            
            # Send a simple query
            test_message = {
                "type": "ai_query",
                "query": "Hello, this is a test message",
                "context": {
                    "test": True
                }
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ Message sent!")
            
            # Wait for response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)
                print(f"✅ Received response: {data.get('type', 'unknown')}")
                if data.get('type') == 'ai_response':
                    print(f"AI Response: {data.get('response', 'No response')[:100]}...")
                
            except asyncio.TimeoutError:
                print("⚠️ No response received within 30 seconds")
            
            # Test plugin list
            plugin_message = {
                "type": "plugin_list"
            }
            
            await websocket.send(json.dumps(plugin_message))
            print("✅ Plugin list request sent!")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"✅ Plugin list response: {data}")
                  except asyncio.TimeoutError:
                print("⚠️ No plugin list response received")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== GAJA Client-Server Connection Test ===")
    asyncio.run(test_connection())
    print("=== Test Completed ===")

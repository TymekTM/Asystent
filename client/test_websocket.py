"""
Simple WebSocket test client
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/1"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Send a test message
            test_message = {
                "type": "test",
                "data": {"message": "hello"}
            }
            
            await websocket.send(json.dumps(test_message))
            print("Message sent")
            
            # Wait for response
            response = await websocket.recv()
            print(f"Response: {response}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())

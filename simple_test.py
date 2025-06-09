"""
Bardzo prosty test klienta
"""
import asyncio
import websockets
import json

async def simple_test():
    try:
        print("Connecting to ws://localhost:8000/ws/1...")
        websocket = await websockets.connect("ws://localhost:8000/ws/1")
        print("Connected!")
        
        message = {"type": "ai_query", "query": "Test", "context": {}}
        await websocket.send(json.dumps(message))
        print("Message sent!")
        
        response = await websocket.recv()
        print(f"Response: {response}")
        
        await websocket.close()
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(simple_test())

#!/usr/bin/env python3
"""
Test prostego WebSocket server
"""

import asyncio
import websockets
import json

async def handle_connection(websocket, path):
    print(f"✅ Klient połączył się: {websocket.remote_address}")
    try:
        await websocket.send(json.dumps({"message": "Hello from server!"}))
        async for message in websocket:
            print(f"📨 Otrzymano: {message}")
            await websocket.send(json.dumps({"echo": message}))
    except websockets.exceptions.ConnectionClosed:
        print("🔗 Klient się rozłączył")
    except Exception as e:
        print(f"❌ Błąd: {e}")

async def main():
    print("🚀 Uruchamiam prosty WebSocket server na porcie 6000")
    
    server = await websockets.serve(handle_connection, "localhost", 6000)
    print("✅ Server uruchomiony - nasłuchuje na ws://localhost:6000")
    
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())

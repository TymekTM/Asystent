#!/usr/bin/env python3
"""
Simple test client to test WebSocket communication with server.
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket():
    uri = "ws://localhost:8001/ws/test_client"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to {uri}")
            
            # Test AI query
            ai_message = {
                "type": "ai_query",
                "message": "Hello, how are you?"
            }
            await websocket.send(json.dumps(ai_message))
            logger.info("Sent AI query")
            
            # Wait for response
            response = await websocket.recv()
            data = json.loads(response)
            logger.info(f"AI Response: {data}")
            
            # Test plugin toggle
            plugin_message = {
                "type": "plugin_toggle",
                "plugin": "weather_module",
                "action": "disable"
            }
            await websocket.send(json.dumps(plugin_message))
            logger.info("Sent plugin toggle request")
            
            # Wait for response
            response = await websocket.recv()
            data = json.loads(response)
            logger.info(f"Plugin toggle response: {data}")
            
            # Test plugin toggle back to enabled
            plugin_message = {
                "type": "plugin_toggle",
                "plugin": "weather_module",
                "action": "enable"
            }
            await websocket.send(json.dumps(plugin_message))
            logger.info("Sent plugin enable request")
            
            # Wait for response
            response = await websocket.recv()
            data = json.loads(response)
            logger.info(f"Plugin enable response: {data}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())

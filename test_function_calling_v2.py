#!/usr/bin/env python3
"""
Test function calling - first enable weather plugin, then test function calling.
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_function_calling_with_plugin():
    uri = "ws://localhost:8001/ws/function_test2"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to {uri}")
            
            # First enable the weather plugin
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
            
            # Now test AI query that should trigger a function call
            ai_message = {
                "type": "ai_query",
                "message": "What's the weather like in Warsaw? Please check the current weather."
            }
            await websocket.send(json.dumps(ai_message))
            logger.info("Sent weather query that should trigger function call")
            
            # Wait for multiple responses (AI might call functions)
            for i in range(10):  # Wait for up to 10 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    data = json.loads(response)
                    logger.info(f"Response {i+1}: Type={data.get('type')}, Content={str(data)[:200]}...")
                    
                    if data.get('type') == 'ai_response':
                        logger.info("Final AI response received")
                        break
                        
                except asyncio.TimeoutError:
                    logger.info("No more messages received")
                    break
            
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_function_calling_with_plugin())

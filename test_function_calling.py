#!/usr/bin/env python3
"""
Test function calling through AI system.
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_function_calling():
    uri = "ws://localhost:8001/ws/function_test"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to {uri}")
            
            # Test AI query that should trigger a function call
            ai_message = {
                "type": "ai_query",
                "message": "What's the weather like in Warsaw?"
            }
            await websocket.send(json.dumps(ai_message))
            logger.info("Sent weather query that should trigger function call")
            
            # Wait for multiple responses (AI might call functions)
            for i in range(5):  # Wait for up to 5 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)
                    logger.info(f"Response {i+1}: {data}")
                    
                    if data.get('type') == 'ai_response':
                        break
                        
                except asyncio.TimeoutError:
                    logger.info("No more messages received")
                    break
            
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_function_calling())

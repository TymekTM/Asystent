#!/usr/bin/env python3
"""
Debug tester - sprawdzi format odpowiedzi z serwera
"""

import asyncio
import json
import logging
import os
import time
import websockets
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_single_test():
    """Debug single test to see response format"""
    # Load environment
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    server_url = "ws://localhost:8001/ws/debug_test_user"
    
    try:
        # Connect
        websocket = await websockets.connect(server_url)
        logger.info(f"🔗 Connected to WebSocket: {server_url}")
        
        # Handshake
        handshake_message = {"type": "handshake"}
        await websocket.send(json.dumps(handshake_message))
        
        response = await websocket.recv()
        handshake_response = json.loads(response)
        logger.info(f"📝 Handshake response: {handshake_response}")
        
        if handshake_response.get("type") != "handshake_response":
            logger.error("Handshake failed")
            return
        
        # Send AI query
        ai_message = {
            "type": "ai_query",
            "query": "Jaka jest pogoda w Warszawie?",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🚀 Sending query: {ai_message}")
        await websocket.send(json.dumps(ai_message))
        
        # Get response
        response = await websocket.recv()
        logger.info(f"📄 Raw response: {response}")
        
        try:
            parsed_response = json.loads(response)
            logger.info(f"📊 Parsed response: {json.dumps(parsed_response, indent=2, ensure_ascii=False)}")
            
            # Analyze structure
            if "data" in parsed_response:
                data = parsed_response["data"]
                logger.info(f"🔍 Data keys: {list(data.keys())}")
                
                if "response" in data:
                    response_content = data["response"]
                    logger.info(f"🎯 Response content: {response_content}")
                    logger.info(f"🎯 Response type: {type(response_content)}")
                    
                    # Try to parse response content if it's a string
                    if isinstance(response_content, str):
                        try:
                            parsed_content = json.loads(response_content)
                            logger.info(f"✅ Parsed response content: {json.dumps(parsed_content, indent=2, ensure_ascii=False)}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ Response content is not JSON: {e}")
                    
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse response: {e}")
        
        await websocket.close()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_single_test())

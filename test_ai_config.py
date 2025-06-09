#!/usr/bin/env python3
"""
Test script to verify AI configuration and provider status
"""

import asyncio
import json
import websockets
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ai_config():
    """Test AI configuration and provider status"""
    uri = "ws://localhost:8001/ws/1"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to server")
            
            # Test simple AI query to verify OpenAI integration
            test_query = {
                "type": "ai_query",
                "query": "Który provider AI obecnie używasz i jaki model?",
                "timestamp": 12345
            }
            
            await websocket.send(json.dumps(test_query))
            logger.info("📤 Sent AI query: Which AI provider and model are you using?")
            
            response = await websocket.recv()
            response_data = json.loads(response)
            
            logger.info("📥 Server response:")
            logger.info(f"Type: {response_data.get('type')}")
            logger.info(f"Response: {response_data.get('response')}")
            
            print("\n" + "="*60)
            print("🤖 AI PROVIDER TEST RESULTS")
            print("="*60)
            print(f"Response: {response_data.get('response')}")
            print("="*60)
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_config())

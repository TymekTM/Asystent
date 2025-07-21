#!/usr/bin/env python3
"""Simple WebSocket Connection Test Test basic WebSocket connectivity before stress
testing."""

import asyncio
import json
import logging

import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WS_URL = "ws://localhost:8001/ws"


async def test_basic_websocket():
    """Test basic WebSocket connection."""
    try:
        logger.info("Testing basic WebSocket connection...")

        # Try different WebSocket URLs
        urls_to_try = [
            "ws://localhost:8001/ws",
            "ws://localhost:8001/ws/",
            "ws://localhost:8001/websocket",
            "ws://localhost:8001/",
        ]

        for url in urls_to_try:
            try:
                logger.info(f"Trying URL: {url}")
                async with websockets.connect(url, timeout=5) as ws:
                    logger.info(f"✅ Connected to {url}")

                    # Send test message
                    test_message = json.dumps(
                        {"type": "test", "data": "Hello WebSocket!"}
                    )

                    await ws.send(test_message)
                    logger.info("✅ Message sent")

                    # Try to receive response
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=5)
                        logger.info(f"✅ Received: {response}")
                    except TimeoutError:
                        logger.info("⚠️ No response received (timeout)")

                    return True

            except Exception as e:
                logger.warning(f"❌ Failed to connect to {url}: {e}")
                continue

        logger.error("❌ All WebSocket connection attempts failed")
        return False

    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")
        return False


async def test_websocket_with_user_id():
    """Test WebSocket connection with user_id parameter."""
    try:
        url = "ws://localhost:8001/ws?user_id=test_user"
        logger.info(f"Testing WebSocket with user_id: {url}")

        async with websockets.connect(url, timeout=5) as ws:
            logger.info("✅ Connected with user_id")

            test_message = json.dumps(
                {"type": "query", "data": "Test message", "user_id": "test_user"}
            )

            await ws.send(test_message)
            logger.info("✅ Message sent")

            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                logger.info(f"✅ Received: {response}")
            except TimeoutError:
                logger.info("⚠️ No response received (timeout)")

            return True

    except Exception as e:
        logger.error(f"❌ WebSocket with user_id failed: {e}")
        return False


async def main():
    """Main test runner."""
    logger.info("🧪 Testing WebSocket Connectivity")
    logger.info("=" * 40)

    # Test basic connection
    basic_result = await test_basic_websocket()

    # Test with user_id
    user_id_result = await test_websocket_with_user_id()

    logger.info("=" * 40)
    if basic_result or user_id_result:
        logger.info("✅ At least one WebSocket test succeeded")
        return 0
    else:
        logger.error("❌ All WebSocket tests failed")
        return 1


if __name__ == "__main__":
    import sys

    result = asyncio.run(main())
    sys.exit(result)

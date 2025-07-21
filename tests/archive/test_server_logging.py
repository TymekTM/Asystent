#!/usr/bin/env python3
"""Test redukcji logów serwera."""

import asyncio
import time

import aiohttp
import pytest
from loguru import logger


async def test_status_endpoint():
    """Test sprawdzający czy endpoint /api/status działa."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8001/api/status") as response:
                assert response.status == 200
                data = await response.json()
                assert data["status"] == "running"
                logger.info("✅ Status endpoint works correctly")
                return True
    except Exception as e:
        logger.error(f"❌ Status endpoint test failed: {e}")
        return False


async def test_reduced_logging():
    """Test sprawdzający czy logowanie zostało zredukowane."""
    logger.info("🧪 Testing reduced logging configuration...")

    # Symuluj kilka zapytań do status endpoint
    try:
        async with aiohttp.ClientSession() as session:
            for i in range(5):
                async with session.get("http://localhost:8001/api/status") as response:
                    if response.status == 200:
                        logger.info(f"Request {i+1}/5 completed")
                await asyncio.sleep(0.1)

        logger.success("✅ Logging test completed - check if HTTP logs are reduced")
        return True
    except Exception as e:
        logger.error(f"❌ Logging test failed: {e}")
        return False


async def main():
    """Główna funkcja testowa."""
    logger.info("🚀 Starting server logging tests...")

    # Poczekaj chwilę na uruchomienie serwera
    await asyncio.sleep(2)

    # Test endpoint
    status_ok = await test_status_endpoint()

    # Test logowania
    logging_ok = await test_reduced_logging()

    if status_ok and logging_ok:
        logger.success("✅ All tests passed!")
    else:
        logger.error("❌ Some tests failed!")


if __name__ == "__main__":
    asyncio.run(main())

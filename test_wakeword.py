#!/usr/bin/env python3
"""
Test wakeword detection
"""

import asyncio
import logging
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'client'))

from client.audio_modules.simple_wakeword_detector import WakewordDetector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def wakeword_callback():
    """Callback when wakeword is detected."""
    logger.info("🔊 WAKEWORD DETECTED! Assistant should respond now.")

async def main():
    """Test wakeword detection."""
    logger.info("Starting wakeword detection test...")
    
    # Wakeword config
    config = {
        "enabled": True,
        "sensitivity": 0.6,
        "keyword": "gaja",
        "device_id": None  # Use default device
    }
    
    # Create detector
    detector = WakewordDetector(config, wakeword_callback)
    
    # Start detection
    await detector.start()
    
    logger.info("Wakeword detection is running. Say 'gaja' to test.")
    logger.info("Press Ctrl+C to stop...")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
        await detector.stop()
        logger.info("Stopped.")

if __name__ == "__main__":
    asyncio.run(main())

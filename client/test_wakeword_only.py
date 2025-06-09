"""
Test client z debugowaniem wakeword detection
"""

import asyncio
import json
import sys
from pathlib import Path
from loguru import logger
import threading
import time

# Dodaj ścieżkę klienta do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from audio_modules.advanced_wakeword_detector import create_wakeword_detector


class TestClient:
    """Test client do debugowania wakeword detection."""
    
    def __init__(self):
        self.wakeword_detector = None
        self.callback_called = False
        
    def simple_callback(self, query: str = None):
        """Prosty callback do testowania."""
        self.callback_called = True
        if query:
            logger.success(f"🎯 CALLBACK CALLED WITH QUERY: '{query}'")
        else:
            logger.success("🎯 CALLBACK CALLED (no query)")
    
    async def test_wakeword_detection(self):
        """Test wakeword detection."""
        logger.info("🚀 Starting wakeword detection test...")
        
        # Load config
        config_path = Path("client_config.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {
                "wakeword": {
                    "enabled": True,
                    "keyword": "gaja",
                    "sensitivity": 0.6,
                    "device_id": 14,
                    "stt_silence_threshold_ms": 2000
                }
            }
        
        wakeword_config = config.get('wakeword', {})
        logger.info(f"📋 Wakeword config: {wakeword_config}")
        
        # Create wakeword detector
        try:
            self.wakeword_detector = create_wakeword_detector(
                config=wakeword_config,
                callback=self.simple_callback
            )
            logger.success("✅ Wakeword detector created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating wakeword detector: {e}")
            return
        
        # Start detection
        try:
            logger.info("🎤 Starting wakeword detection...")
            self.wakeword_detector.start_detection()
            logger.success("✅ Wakeword detection started")
        except Exception as e:
            logger.error(f"❌ Error starting wakeword detection: {e}")
            return
        
        # Wait and monitor
        logger.info("👂 Listening for wakeword detection for 30 seconds...")
        logger.info("🗣️  Try saying 'gaja' or one of the wake words...")
        
        for i in range(30):
            await asyncio.sleep(1)
            if self.callback_called:
                logger.success(f"🎉 SUCCESS! Callback was called after {i+1} seconds!")
                break
            if i % 5 == 0:
                logger.info(f"⏰ Still listening... {30-i} seconds remaining")
        
        if not self.callback_called:
            logger.warning("⚠️  No callback detected in 30 seconds")
        
        # Stop detection
        try:
            self.wakeword_detector.stop_detection()
            logger.info("🛑 Wakeword detection stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping wakeword detection: {e}")


async def main():
    """Main test function."""
    # Setup logging
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )
    
    logger.info("🔍 Starting GAJA Wakeword Detection Test...")
    
    test_client = TestClient()
    await test_client.test_wakeword_detection()


if __name__ == "__main__":
    asyncio.run(main())

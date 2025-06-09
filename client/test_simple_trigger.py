"""
Simple test to verify manual trigger detection
"""

import asyncio
import json
import sys
import time
import threading
from pathlib import Path
from loguru import logger

# Dodaj ścieżkę klienta do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from audio_modules.advanced_wakeword_detector import create_wakeword_detector


class SimpleTriggerTest:
    """Simple manual trigger test."""
    
    def __init__(self):
        self.callback_called = False
        
    async def simple_callback(self, query: str = None):
        """Simple callback."""
        self.callback_called = True
        logger.success(f"🎯 CALLBACK CALLED! Query: '{query}'")
    
    def test_manual_trigger(self):
        """Test manual trigger."""
        logger.info("🚀 Starting simple manual trigger test...")
        
        # Simple config
        config = {
            "enabled": True,
            "keyword": "gaja",
            "sensitivity": 0.6,
            "device_id": 14,
            "stt_silence_threshold_ms": 1000
        }
        
        # Create detector
        detector = create_wakeword_detector(config, self.simple_callback)
        
        # Start detection
        logger.info("🔄 Starting detection...")
        detector.start_detection()
        
        # Wait for startup
        time.sleep(2)
        
        # Check if detection thread is running
        logger.info(f"📊 Detection running: {detector.is_running}")
        logger.info(f"📊 Thread alive: {detector.detection_thread.is_alive() if detector.detection_thread else 'No thread'}")
        
        # Trigger manually
        logger.info("🔥 Triggering manual detection...")
        detector.trigger_manual_detection()
        
        # Wait and check
        time.sleep(5)
        
        if self.callback_called:
            logger.success("✅ Simple trigger test PASSED!")
        else:
            logger.error("❌ Simple trigger test FAILED")
        
        # Stop
        detector.stop_detection()


def main():
    """Main function."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    test = SimpleTriggerTest()
    test.test_manual_trigger()


if __name__ == "__main__":
    main()

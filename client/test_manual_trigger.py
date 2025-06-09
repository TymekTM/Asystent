"""
Test manual trigger for wakeword detection
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from loguru import logger
import threading

# Dodaj ścieżkę klienta do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from audio_modules.advanced_wakeword_detector import create_wakeword_detector
from audio_modules.whisper_asr import create_whisper_asr


class ManualTriggerTest:
    """Test manual trigger functionality."""
    
    def __init__(self):
        self.wakeword_detector = None
        self.whisper_asr = None
        self.callback_called = False
        
    async def callback(self, query: str = None):
        """Test callback."""
        self.callback_called = True
        if query:
            logger.success(f"🎯 MANUAL TRIGGER CALLBACK WITH QUERY: '{query}'")
        else:
            logger.success("🎯 MANUAL TRIGGER CALLBACK (no query)")
    
    async def run_test(self):
        """Run the manual trigger test."""
        logger.info("🚀 Starting manual trigger test...")
        
        # Load config
        config = {
            "enabled": True,
            "keyword": "gaja", 
            "sensitivity": 0.6,
            "device_id": 14,
            "stt_silence_threshold_ms": 2000
        }
        
        try:
            # Initialize components
            self.wakeword_detector = create_wakeword_detector(config, self.callback)
            
            # Initialize Whisper ASR
            whisper_config = {"model": "base", "language": "pl"}
            self.whisper_asr = create_whisper_asr(whisper_config)
            
            # Set whisper for wakeword detector
            self.wakeword_detector.set_whisper_asr(self.whisper_asr)
            
            # Start detection
            logger.info("📡 Starting wakeword detection...")
            self.wakeword_detector.start_detection()
            
            # Wait for setup
            await asyncio.sleep(2)
            
            # Trigger manual detection
            logger.info("🔥 Triggering manual detection...")
            self.wakeword_detector.trigger_manual_detection()
            
            # Wait for callback
            logger.info("⏳ Waiting for callback...")
            await asyncio.sleep(10)
            
            if self.callback_called:
                logger.success("✅ Manual trigger test PASSED!")
            else:
                logger.error("❌ Manual trigger test FAILED - callback not called")
                
        except Exception as e:
            logger.error(f"💥 Error in manual trigger test: {e}")
        finally:
            if self.wakeword_detector:
                self.wakeword_detector.stop_detection()


async def main():
    """Main function."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    test = ManualTriggerTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())

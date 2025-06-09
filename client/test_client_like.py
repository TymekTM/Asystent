"""
Test that exactly matches the client setup
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
from audio_modules.whisper_asr import create_whisper_asr


class ClientLikeTest:
    """Test that mimics the exact client setup."""
    
    def __init__(self):
        self.callback_called = False
        
    async def on_wakeword_detected(self, query: str = None):
        """Callback exactly like the client."""
        self.callback_called = True
        if query:
            logger.success(f"🎯 CLIENT-LIKE CALLBACK WITH QUERY: '{query}'")
        else:            logger.success("🎯 CLIENT-LIKE CALLBACK (no query)")
    
    async def test_client_like_setup(self):
        """Test client-like setup."""
        logger.info("🚀 Starting client-like test...")
        
        # Load config like client
        config = {
            "enabled": True,
            "keyword": "gaja",
            "sensitivity": 0.6,
            "device_id": 14,
            "stt_silence_threshold_ms": 2000
        }
        
        try:
            # Create detector like client
            wakeword_detector = create_wakeword_detector(config, self.on_wakeword_detected)
            
            # Initialize Whisper ASR like client
            whisper_config = {"model": "base", "language": "pl"}
            whisper_asr = create_whisper_asr(whisper_config)
            
            # Set whisper for detector like client
            wakeword_detector.set_whisper_asr(whisper_asr)
            
            # Start detection like client
            logger.info("📡 Starting wakeword detection...")
            wakeword_detector.start_detection()
            
            # Wait for startup
            await asyncio.sleep(3)
            
            # Get current event loop info
            loop = asyncio.get_running_loop()
            logger.info(f"🔄 Current event loop: {loop}")
            logger.info(f"🔄 Loop running: {loop.is_running()}")
            
            # Trigger manually
            logger.info("🔥 Triggering manual detection...")
            wakeword_detector.trigger_manual_detection()
            
            # Wait for callback like client - shorter wait with more checks
            for i in range(20):  # 20 iterations of 0.5s = 10s total
                await asyncio.sleep(0.5)
                if self.callback_called:
                    logger.success(f"✅ Client-like test PASSED after {i*0.5:.1f}s!")
                    return
                
            logger.error("❌ Client-like test FAILED - callback not called within 10s")
                
        except Exception as e:
            logger.error(f"💥 Error in client-like test: {e}")
        finally:
            if 'wakeword_detector' in locals():
                wakeword_detector.stop_detection()


async def main():
    """Main function."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    test = ClientLikeTest()
    await test.test_client_like_setup()


if __name__ == "__main__":
    asyncio.run(main())

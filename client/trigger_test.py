"""
Simple script to trigger the manual wakeword detection
"""
import asyncio
import sys
from pathlib import Path

# Add client path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.INFO)

from audio_modules.advanced_wakeword_detector import create_wakeword_detector

async def test_callback(query: str):
    print(f"CALLBACK RECEIVED: {query}")
    return True

async def main():
    # Create a test config
    config = {
        "enabled": True,
        "keyword": "gaja",
        "sensitivity": 0.6,
        "device_id": None,
        "stt_silence_threshold_ms": 2000
    }
    
    print("Creating wakeword detector...")
    detector = create_wakeword_detector(config, test_callback)
    
    print("Starting detection...")
    detector.start_detection()
    
    # Wait a moment for initialization
    await asyncio.sleep(3)
    
    print("Triggering manual detection...")
    detector.trigger_manual_detection()
    
    # Wait for callback
    await asyncio.sleep(10)
    
    print("Stopping detection...")
    detector.stop_detection()

if __name__ == "__main__":
    asyncio.run(main())

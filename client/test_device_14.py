"""
Test wakeword detection with proper device ID
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add client path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import our modules
from audio_modules.advanced_wakeword_detector import create_wakeword_detector

async def test_callback(query: str):
    """Test callback function."""
    print(f"🎯 CALLBACK TRIGGERED: '{query}'")
    
async def main():
    print("🎤 Testing wakeword detection with device ID 14...")
    
    # Config matching client_config.json
    config = {
        "enabled": True,
        "keyword": "gaja",
        "sensitivity": 0.6,
        "device_id": 14,
        "stt_silence_threshold_ms": 2000
    }
    
    # Create detector
    detector = create_wakeword_detector(config, test_callback)
      # Import and create real Whisper ASR
    from audio_modules.whisper_asr import create_whisper_asr
    
    whisper_config = {
        "model": "base",
        "language": "pl"
    }
    
    whisper_asr = create_whisper_asr(whisper_config)
    detector.set_whisper_asr(whisper_asr)
    
    print("🚀 Starting detection...")
    detector.start_detection()
    
    print("⏰ Waiting 30 seconds for detection... Try speaking 'gaja' or press manual trigger")
    await asyncio.sleep(30)
    
    print("🛑 Stopping detection...")
    detector.stop_detection()
    print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(main())

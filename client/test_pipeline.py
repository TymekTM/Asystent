#!/usr/bin/env python3
"""
Test pełnego pipeline: wakeword -> ASR -> AI -> TTS -> overlay
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add client directory to path
sys.path.insert(0, str(Path(__file__).parent))

from audio_modules.whisper_asr import WhisperASR
from audio_modules.tts_module import TTSModule

async def test_pipeline():
    """Test pełnego pipeline"""
    print("🧪 Testing full pipeline...")
    
    # 1. Test AI query simulation (normally comes from wakeword + ASR)
    test_query = "Jaka jest pogoda?"
    
    # 2. Simulate sending to server and getting response
    print(f"📤 Simulating query: {test_query}")
    
    # Mock AI response (normally comes from server)
    mock_ai_response = {
        "text": "Dziś jest piękna pogoda, słonecznie i 22 stopnie Celsjusza.",
        "command": "",
        "params": {}
    }
    
    # 3. Test TTS
    print("🔊 Testing TTS...")
    try:
        tts = TTSModule()
        await tts.speak(mock_ai_response["text"])
        print("✅ TTS test completed")
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
    
    print("🎯 Pipeline test completed")

if __name__ == "__main__":
    asyncio.run(test_pipeline())

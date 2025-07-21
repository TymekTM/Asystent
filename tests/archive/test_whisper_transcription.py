#!/usr/bin/env python3
"""Test Whisper ASR transcription capability."""
import os
import sys

import numpy as np

sys.path.append(os.path.abspath("."))


def test_whisper_transcription():
    """Test podstawowej funkcjonalności Whisper ASR."""
    print("🧪 Testing Whisper ASR transcription...")

    try:
        # Import and create Whisper ASR
        from client.audio_modules.whisper_asr import create_whisper_asr

        whisper_asr = create_whisper_asr()
        print(f"✅ Created Whisper ASR: available={whisper_asr.available}")

        if not whisper_asr.available:
            print("❌ Whisper ASR not available")
            return False

        print(f"📍 Model: {whisper_asr.model_id}")

        # Test with synthetic audio (silence)
        print("\n🔊 Testing with silence...")
        silence = np.zeros(16000, dtype=np.float32)  # 1 second of silence
        result = whisper_asr.transcribe(silence, sample_rate=16000)
        print(f"Silence result: '{result}'")

        # Test with synthetic audio (noise)
        print("\n🔊 Testing with random noise...")
        noise = np.random.normal(0, 0.1, 16000).astype(np.float32)
        result = whisper_asr.transcribe(noise, sample_rate=16000)
        print(f"Noise result: '{result}'")

        # Test with synthetic audio (sine wave - like speech)
        print("\n🔊 Testing with sine wave...")
        duration = 1.0
        sample_rate = 16000
        frequency = 440  # A4 note
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        sine_wave = np.sin(frequency * 2 * np.pi * t).astype(np.float32) * 0.3
        result = whisper_asr.transcribe(sine_wave, sample_rate=16000)
        print(f"Sine wave result: '{result}'")

        print("\n✅ Whisper ASR transcription test completed")
        return True

    except Exception as e:
        print(f"❌ Error testing Whisper: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_whisper_transcription()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

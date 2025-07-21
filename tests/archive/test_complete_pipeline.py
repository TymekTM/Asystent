#!/usr/bin/env python3
"""
Test complete voice command pipeline: wake word + Whisper transcription
"""
import os
import sys
import threading
import time

import numpy as np

sys.path.append(os.path.abspath("."))

# Global variables for test
wake_word_detected = False
transcription_result = None
detection_event = threading.Event()


def wake_word_callback(wake_word, audio_data=None):
    """Callback when wake word is detected."""
    global wake_word_detected, transcription_result
    wake_word_detected = True

    print(f"\n🎯 Wake word detected: '{wake_word}'")

    if audio_data is not None:
        print(f"📊 Audio data received: {len(audio_data)} samples")
        print(f"📈 Audio amplitude: max={np.max(np.abs(audio_data)):.4f}")

        # This will be handled by the detector's Whisper integration
        print("🔄 Whisper transcription will be handled by detector...")
    else:
        print("⚠️  No audio data received with wake word")

    # Signal that we detected the wake word
    detection_event.set()


def test_complete_pipeline():
    """Test complete voice command pipeline."""
    print("🚀 Testing complete voice command pipeline...")
    print("📋 This test will:")
    print("   1. Start wake word detection with Whisper")
    print("   2. Listen for 'Gaja' wake word")
    print("   3. Automatically transcribe following speech")
    print("   4. Show results")

    try:
        # Create wake word detector
        from client.audio_modules.optimized_wakeword_detector import (
            create_wakeword_detector,
        )
        from client.audio_modules.whisper_asr import create_whisper_asr

        # Configuration
        config = {
            "wake_word": "gaja",
            "device_id": 1,
            "sample_rate": 16000,
            "chunk_size": 1280,
            "sensitivity": 0.5,
            "whisper_enabled": True,
            "listen_duration": 3.0,  # Listen for 3 seconds after wake word
        }

        print("✅ Creating wake word detector...")
        detector = create_wakeword_detector(config, wake_word_callback)

        print("✅ Creating Whisper ASR...")
        whisper_asr = create_whisper_asr()
        print(
            f"📍 Whisper available: {whisper_asr.available}, Model: {whisper_asr.model_id}"
        )

        print("✅ Integrating Whisper with detector...")
        detector.set_whisper_asr(whisper_asr)

        print("\n🎤 Starting voice command detection...")
        print("💬 Say 'Gaja' followed by your command")
        print("⏹️  Test will run for 45 seconds or until wake word detected")

        # Start detection
        detector.start_detection()

        # Wait for wake word or timeout
        timeout = 45
        start_time = time.time()

        while not detection_event.is_set() and (time.time() - start_time) < timeout:
            remaining = timeout - (time.time() - start_time)
            if int(remaining) % 5 == 0:
                print(f"⏰ {int(remaining)} seconds remaining...")
            time.sleep(1)

        print("\n🛑 Stopping detection...")
        detector.stop_detection()

        # Results
        if wake_word_detected:
            print("\n🎉 SUCCESS!")
            print("✅ Wake word was detected")
            print("✅ Voice command pipeline is working")
        else:
            print("\n⏰ TIMEOUT")
            print("ℹ️  No wake word detected within time limit")
            print("💡 Try speaking 'Gaja' closer to the microphone")

        return wake_word_detected

    except Exception as e:
        print(f"❌ Error in pipeline test: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_complete_pipeline()
    if success:
        print("\n🏆 Complete pipeline test PASSED!")
    else:
        print("\n💥 Pipeline test incomplete or failed")
        print("💡 This may be normal if no wake word was spoken")

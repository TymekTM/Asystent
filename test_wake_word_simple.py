#!/usr/bin/env python3
"""Simple wake word detection test to verify the system works."""

import os
import sys
import time

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client")
)


def test_wake_word_detection():
    """Test wake word detection in isolation."""
    try:
        # Set up logging
        import logging

        logging.basicConfig(level=logging.DEBUG)

        # Import our optimized wake word detector
        from client.audio_modules.optimized_wakeword_detector import (
            create_wakeword_detector,
        )

        print("✅ Imported wake word detector successfully")

        # Define callback
        def wake_word_callback(transcribed_text):
            print(f"🎉 WAKE WORD DETECTED! Transcribed text: '{transcribed_text}'")

        # Create detector
        config = {
            "sensitivity": 0.5,  # Lower sensitivity for testing
            "keyword": "gaja",
            "device_id": 1,  # Use working device
        }

        detector = create_wakeword_detector(config, wake_word_callback)
        print("✅ Created wake word detector")

        # Add real Whisper ASR
        from client.audio_modules.whisper_asr import create_whisper_asr

        whisper_asr = create_whisper_asr()
        print(
            f"✅ Created Whisper ASR: available={whisper_asr.available}, model={whisper_asr.model_id}"
        )

        detector.set_whisper_asr(whisper_asr)
        print("✅ Added real Whisper ASR")

        # Start detection
        print("🎤 Starting wake word detection...")
        print("💬 Try saying 'Gaja' followed by a command")
        print("⏹️  Press Ctrl+C to stop")

        detector.start_detection()

        # Keep running
        try:
            print("⏳ Running for 30 seconds...")
            for i in range(30):
                time.sleep(1)
                if i % 5 == 0:
                    print(f"⏰ {30-i} seconds remaining...")
        except KeyboardInterrupt:
            print("\n🛑 Stopping detection...")

        detector.stop_detection()
        print("✅ Detection stopped")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_wake_word_detection()

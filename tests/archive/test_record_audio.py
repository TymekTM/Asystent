#!/usr/bin/env python3
"""Test record_command_audio function directly."""

import logging
import os
import sys
import threading

import numpy as np

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client")
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)


def test_record_command_audio():
    """Test the record_command_audio function directly."""
    try:
        from client.audio_modules.wakeword_detector import record_command_audio

        print("✅ Imported record_command_audio successfully")

        # Create stop event
        stop_event = threading.Event()

        print("🎤 Starting 5-second test recording...")
        print("💬 Please speak now!")

        # Record for 5 seconds
        audio_data = record_command_audio(
            mic_device_id=54,
            vad_silence_duration_ms=2000,  # Use same as in actual code
            stop_event=stop_event,
        )

        if audio_data is not None:
            print(
                f"✅ Recorded audio: shape={audio_data.shape}, dtype={audio_data.dtype}"
            )
            max_amp = np.max(np.abs(audio_data))
            mean_amp = np.mean(np.abs(audio_data))
            print(f"📊 Max amplitude: {max_amp:.6f}")
            print(f"📊 Mean amplitude: {mean_amp:.6f}")

            if max_amp > 0.001:
                print("✅ Good audio signal recorded!")
            else:
                print("❌ Audio signal too weak")
        else:
            print("❌ No audio recorded")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_record_command_audio()

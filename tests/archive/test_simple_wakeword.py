#!/usr/bin/env python3
"""Simple wakeword detection test with original 1.3.0 code."""

import os
import sys
import time
from pathlib import Path

import numpy as np

# Add paths
sys.path.append(str(Path(__file__).parent))

from config import load_config


def simple_wakeword_test():
    """Simple test of wakeword detection without full assistant."""
    print("🎤 Simple Wakeword Detection Test - GAJA 1.3.0")
    print("=" * 60)

    # Load config
    config = load_config()

    mic_device_id = config.get("MIC_DEVICE_ID", None)
    wake_word = config.get("WAKE_WORD", "gaja")
    sensitivity = config.get("WAKE_WORD_SENSITIVITY_THRESHOLD", 0.35)

    print("📊 Configuration:")
    print(f"   Microphone ID: {mic_device_id}")
    print(f"   Wake word: {wake_word}")
    print(f"   Sensitivity: {sensitivity}")
    print()

    if mic_device_id is None:
        print(
            "❌ No microphone configured. Run: python configure_microphone_1_3_0.py set <ID>"
        )
        return

    print("🚀 Starting simple wakeword detection test...")
    print("💡 This version uses original OpenWakeWord models without modifications")
    print("🛑 Press Ctrl+C to stop")
    print()

    try:
        # Import and test OpenWakeWord directly
        print("📦 Loading OpenWakeWord...")
        import openwakeword
        from openwakeword import Model

        # Load custom model for GAJA
        model_path = "resources/openWakeWord/Gaja1.tflite"
        if not os.path.exists(model_path):
            print(f"❌ Model file not found: {model_path}")
            return

        oww_model = Model(wakeword_models=[model_path], inference_framework="tflite")
        print(f"✅ Custom GAJA model loaded from {model_path}")

        # Test audio input
        print("🔊 Testing audio input...")
        import sounddevice as sd

        sample_rate = 16000
        chunk_size = 1280  # Standard for OpenWakeWord

        print(f"🎤 Listening for '{wake_word}' on device {mic_device_id}...")
        print("📊 Audio levels and detection status will be shown below:")
        print()

        def audio_callback(indata, frames, time, status):
            """Audio callback for real-time processing."""
            if status:
                print(f"⚠️  Audio status: {status}")

            # Convert to the format expected by OpenWakeWord
            audio_frame = indata[:, 0].astype(np.float32)

            # Get prediction
            prediction = oww_model.predict(audio_frame)

            # Check audio levels
            rms = np.sqrt(np.mean(audio_frame**2))
            max_amp = np.max(np.abs(audio_frame))

            # Show detection status
            detected_words = []
            for word, score in prediction.items():
                if score > sensitivity:
                    detected_words.append(f"{word}({score:.3f})")

            status_line = f"🔊 RMS: {rms:.6f}, Max: {max_amp:.4f}"
            if detected_words:
                status_line += f" | 🎉 DETECTED: {', '.join(detected_words)}"

            print(f"\r{status_line:<80}", end="", flush=True)

        # Start audio stream
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            device=mic_device_id,
            blocksize=chunk_size,
            callback=audio_callback,
            dtype="float32",
        ):
            print("🎯 Listening... Say 'gaja' to test detection")
            while True:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping wakeword detection...")
        print("✅ Test completed.")

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Install with: pip install openwakeword")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    simple_wakeword_test()

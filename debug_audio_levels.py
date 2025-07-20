#!/usr/bin/env python3
"""Debug tool to monitor audio levels and wakeword detection in real-time."""

import sys
import time
from pathlib import Path

# Add client path
sys.path.append(str(Path(__file__).parent / "client"))

import json

import numpy as np
from audio_modules.wakeword_detector import OptimizedWakeWordDetector


def load_config():
    """Load client configuration."""
    config_path = Path("client/client_config.json")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def debug_callback(keyword):
    """Callback for wakeword detection."""
    print(f"\n🎉 WAKEWORD DETECTED: '{keyword}' at {time.strftime('%H:%M:%S')}")


def monitor_audio_levels():
    """Monitor audio levels in real-time."""
    print("🎤 Audio Level Monitor - GAJA Wakeword Debug Tool")
    print("=" * 60)

    config = load_config()
    wakeword_config = config["wakeword"]

    print("📊 Configuration:")
    print(f"   Device ID: {wakeword_config['device_id']}")
    print(f"   Sensitivity: {wakeword_config['sensitivity']}")
    print(f"   Keyword: {wakeword_config['keyword']}")
    print()

    # Create detector with debug callback
    detector = OptimizedWakeWordDetector(
        sensitivity=wakeword_config["sensitivity"],
        keyword=wakeword_config["keyword"],
        device_id=wakeword_config["device_id"],
    )

    detector.add_detection_callback(debug_callback)

    # Override the audio processing to show levels
    original_process_frame = detector._process_audio_frame

    def debug_process_frame(audio_frame):
        """Debug version that shows audio levels."""
        # Calculate audio levels
        energy = np.mean(audio_frame**2)
        max_amplitude = np.max(np.abs(audio_frame))

        # Show levels every second
        if hasattr(debug_process_frame, "last_time"):
            if time.time() - debug_process_frame.last_time > 1.0:
                print(
                    f"🔊 Audio: Energy={energy:.6f}, Max={max_amplitude:.4f}, Time={time.strftime('%H:%M:%S')}"
                )
                debug_process_frame.last_time = time.time()
        else:
            debug_process_frame.last_time = time.time()

        # Call original processing
        return original_process_frame(audio_frame)

    detector._process_audio_frame = debug_process_frame

    print("🚀 Starting wakeword detection...")
    print("💡 Say 'gaja' to test detection")
    print("📊 Audio levels will be shown every second")
    print("🛑 Press Ctrl+C to stop")
    print()

    try:
        detector.start_detection()

        # Keep running until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping audio monitoring...")
        detector.stop_detection()
        print("✅ Stopped.")


if __name__ == "__main__":
    monitor_audio_levels()

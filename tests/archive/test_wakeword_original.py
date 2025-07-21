#!/usr/bin/env python3
"""Test wakeword detection with original 1.3.0 code."""

import sys
import threading
import time
from pathlib import Path

# Add paths
sys.path.append(str(Path(__file__).parent))

from audio_modules.wakeword_detector import run_wakeword_detection

from config import load_config


def wakeword_callback(transcribed_text):
    """Callback when wakeword is detected."""
    print(f"\n🎉 WAKEWORD DETECTED: '{transcribed_text}' at {time.strftime('%H:%M:%S')}")


def test_wakeword_original():
    """Test the original wakeword detection."""
    print("🎤 Original Wakeword Detection Test - GAJA 1.3.0")
    print("=" * 60)

    # Load config
    config = load_config()

    mic_device_id = config.get("MIC_DEVICE_ID", None)
    stt_silence_threshold = config.get("STT_SILENCE_THRESHOLD", 500)
    wake_word = config.get("WAKE_WORD", "gaja")
    wake_word_sensitivity = config.get("WAKE_WORD_SENSITIVITY_THRESHOLD", 0.35)

    print("📊 Configuration:")
    print(f"   Microphone ID: {mic_device_id}")
    print(f"   Wake word: {wake_word}")
    print(f"   Sensitivity: {wake_word_sensitivity}")
    print(f"   STT silence threshold: {stt_silence_threshold}ms")
    print()

    if mic_device_id is None:
        print(
            "❌ No microphone configured. Run: python configure_microphone_1_3_0.py set <ID>"
        )
        return

    print("🚀 Starting original wakeword detection...")
    print("💡 Say 'gaja' to test detection")
    print("🛑 Press Ctrl+C to stop")
    print()

    # Create events
    should_exit = threading.Event()
    manual_trigger_event = threading.Event()

    # Mock objects (since we're just testing detection)
    class MockTTS:
        def speak_text(self, text, interrupt=False):
            print(f"🔊 TTS would say: {text}")

    class MockWhisperASR:
        pass

    class MockLoop:
        def call_soon_threadsafe(self, func, *args):
            func(*args)

    tts = MockTTS()
    whisper_asr = MockWhisperASR()
    loop = MockLoop()

    try:
        # Start wakeword detection
        run_wakeword_detection(
            mic_device_id=mic_device_id,
            stt_silence_threshold_ms=stt_silence_threshold,
            wake_word_config_name=wake_word,
            tts_module=tts,
            process_query_callback_async=wakeword_callback,
            async_event_loop=loop,
            oww_sensitivity_threshold=wake_word_sensitivity,
            whisper_asr_instance=whisper_asr,
            manual_listen_trigger_event=manual_trigger_event,
            stop_detector_event=should_exit,
        )

    except KeyboardInterrupt:
        print("\n🛑 Stopping wakeword detection...")
        should_exit.set()
        print("✅ Stopped.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_wakeword_original()

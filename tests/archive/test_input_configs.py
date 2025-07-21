#!/usr/bin/env python3
"""Test different InputStream configurations."""

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


def test_config(name, **kwargs):
    """Test a specific InputStream configuration."""
    print(f"\n=== {name} ===")
    print(f"Config: {kwargs}")

    audio_buffer = []

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", **kwargs
        ) as stream:
            print("Recording 2 seconds...")

            for i in range(40):  # 2 seconds worth
                if "blocksize" in kwargs:
                    audio_chunk, overflowed = stream.read(kwargs["blocksize"])
                else:
                    audio_chunk, overflowed = stream.read(800)  # Default chunk size

                if overflowed:
                    print(f"WARNING: Overflow at chunk {i}")

                audio_buffer.append(audio_chunk)

                # Check first few chunks
                if i < 5:
                    chunk_max = np.max(np.abs(audio_chunk))
                    print(
                        f"  Chunk {i}: shape={audio_chunk.shape}, amp={chunk_max:.6f}"
                    )

    except Exception as e:
        print(f"❌ Error: {e}")
        return

    if audio_buffer:
        full_audio = np.concatenate(audio_buffer, axis=0)
        max_amp = np.max(np.abs(full_audio))
        print(f"📊 Result: max_amp={max_amp:.6f}, shape={full_audio.shape}")

        if max_amp > 0.001:
            print("✅ Good signal!")
        else:
            print("❌ No signal")
    else:
        print("❌ No audio")


# Test different configurations
print("🔍 Testing different InputStream configurations...")

# Test with device 1 (default)
print("\n🎯 Testing with device 1 (default)...")
test_config("Device 1 - blocksize=800", blocksize=800, device=1)

print("\n🎯 Testing with device None (system default)...")
test_config("Device None - blocksize=800", blocksize=800, device=None)

#!/usr/bin/env python3
"""Test InputStream with exact same settings as record_command_audio."""


import numpy as np
import sounddevice as sd

# Constants from wakeword_detector.py
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 50
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # 800 samples

print(f"Using CHUNK_SAMPLES = {CHUNK_SAMPLES}")


def test_chunked_recording():
    """Test chunked recording like in record_command_audio."""
    print("🎤 Testing chunked recording (like record_command_audio)...")
    print("💬 Please speak now!")

    audio_buffer = []

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=54,
            blocksize=CHUNK_SAMPLES,
        ) as stream:
            print("Listening for 3 seconds...")

            # Record for 3 seconds worth of chunks
            num_chunks = int(3 * SAMPLE_RATE / CHUNK_SAMPLES)  # ~60 chunks

            for i in range(num_chunks):
                audio_chunk, overflowed = stream.read(CHUNK_SAMPLES)
                if overflowed:
                    print(f"WARNING: Input overflowed at chunk {i}!")

                audio_buffer.append(audio_chunk)

                # Check amplitude of this chunk
                chunk_max = np.max(np.abs(audio_chunk))
                if chunk_max > 0.001:
                    print(f"Chunk {i}: amplitude {chunk_max:.6f} ✅")
                elif i % 10 == 0:  # Print every 10th chunk if silent
                    print(f"Chunk {i}: amplitude {chunk_max:.6f}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

    if audio_buffer:
        # Combine all chunks
        full_audio = np.concatenate(audio_buffer, axis=0)
        print("\n📊 Full recording:")
        print(f"   Shape: {full_audio.shape}")
        print(f"   Max amplitude: {np.max(np.abs(full_audio)):.6f}")
        print(f"   Mean amplitude: {np.mean(np.abs(full_audio)):.6f}")
        print(f"   Total chunks: {len(audio_buffer)}")

        return full_audio
    else:
        print("❌ No audio recorded")
        return None


if __name__ == "__main__":
    test_chunked_recording()

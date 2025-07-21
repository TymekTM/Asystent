#!/usr/bin/env python3
"""Test different audio devices to find working microphone."""


import numpy as np
import sounddevice as sd


def test_device(device_id):
    """Test a specific device for recording."""
    try:
        print(f"\n=== Testing Device {device_id} ===")
        devices = sd.query_devices()
        device_info = devices[device_id]
        print(f"Device name: {device_info['name']}")
        print(f"Max input channels: {device_info['max_input_channels']}")

        if device_info["max_input_channels"] == 0:
            print("❌ No input channels available")
            return False

        print("🎤 Recording 3 seconds... please speak!")
        recording = sd.rec(
            int(3 * 16000),
            samplerate=16000,
            channels=1,
            device=device_id,
            dtype="float32",
        )
        sd.wait()

        max_amp = np.max(np.abs(recording))
        mean_amp = np.mean(np.abs(recording))
        print(f"📊 Max amplitude: {max_amp:.6f}")
        print(f"📊 Mean amplitude: {mean_amp:.6f}")

        if max_amp > 0.001:
            print("✅ Good signal!")
            return True
        else:
            print("❌ No signal or too weak")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# Test current device and some alternatives
test_devices = [54, 1, 16, 55, 0]  # Current + some likely candidates

print("🔍 Testing audio devices to find working microphone...")

for device_id in test_devices:
    if test_device(device_id):
        print(f"\n🎉 Device {device_id} works! Use this in config.")
        break
else:
    print("\n❌ No working microphone found in tested devices")

# Also test default device
print("\n=== Testing Default Device ===")
default_device = sd.default.device[0]
print(f"Default input device: {default_device}")
if default_device is not None:
    test_device(default_device)

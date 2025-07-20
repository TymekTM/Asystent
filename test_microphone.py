import sounddevice as sd

print("=== DOSTĘPNE URZĄDZENIA AUDIO INPUT ===")
devices = sd.query_devices()
for i, device in enumerate(devices):
    if device["max_input_channels"] > 0:
        print(f"Device {i}: {device['name']} - {device['max_input_channels']} channels")

print("\n=== DEFAULT INPUT DEVICE ===")
default_input = sd.default.device[0]
print(f"Default input: {default_input}")
if default_input is not None:
    print(f"Default device: {devices[default_input]['name']}")

# Test microphone access
print("\n=== TEST MICROPHONE ACCESS ===")
try:
    print("Testing 2-second recording...")
    import numpy as np

    recording = sd.rec(int(2 * 16000), samplerate=16000, channels=1, device=54)
    sd.wait()
    max_amp = np.max(np.abs(recording))
    print(f"Recorded 2 seconds, max amplitude: {max_amp:.6f}")
    if max_amp > 0.001:
        print("✅ Microphone working - good signal")
    else:
        print("❌ Microphone signal too weak or not working")
except Exception as e:
    print(f"❌ Error testing microphone: {e}")

import sounddevice as sd

# pobranie listy wszystkich urządzeń
devices = sd.query_devices()

# wyświetlenie tylko urządzeń nagrywających (input)
print("Urządzenia nagrywające (input):")
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"ID: {i} | Nazwa: {device['name']}")

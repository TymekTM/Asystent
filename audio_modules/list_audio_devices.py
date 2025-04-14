import sounddevice as sd

print("Dostępne urządzenia wejściowe (mikrofony):")
devices = sd.query_devices()
input_devices = [device for device in devices if device['max_input_channels'] > 0]

if not input_devices:
    print("Nie znaleziono żadnych urządzeń wejściowych (mikrofonów).")
else:
    for i, device in enumerate(devices):
         # Sprawdzamy, czy urządzenie ma kanały wejściowe
         if device['max_input_channels'] > 0:
              # Sprawdzamy, czy to domyślne urządzenie wejściowe systemu
              is_default = (i == sd.default.device[0])
              default_marker = " (Domyślny)" if is_default else ""
              print(f"  ID: {i}, Nazwa: {device['name']}{default_marker}")

print("\nSkopiuj ID wybranego mikrofonu i wklej je jako wartość dla 'MIC_DEVICE_ID' w pliku config.json.")
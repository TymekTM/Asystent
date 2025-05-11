import sounddevice as sd

def list_input_audio_devices():
    """Returns a list of available audio input device descriptions."""
    try:
        devices = sd.query_devices()
        result = []
        for i, device in enumerate(devices):
            if device.get('max_input_channels', 0) > 0:
                result.append(f"{device.get('name')} (Index: {i})")
        return result
    except Exception as e:
        # Return error indicator
        return [f"Could not retrieve audio devices: {e}"]

if __name__ == '__main__':
    # CLI behavior for listing devices
    print("Dostępne urządzenia wejściowe (mikrofony):")
    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device.get('max_input_channels', 0) > 0:
                is_default = (i == sd.default.device[0])
                default_marker = " (Domyślny)" if is_default else ""
                print(f"  ID: {i}, Nazwa: {device.get('name')}{default_marker}")
    except Exception:
        print("Nie można pobrać urządzeń wejściowych (mikrofony).")
    print("\nSkopiuj ID wybranego mikrofonu i wklej je jako wartość dla 'MIC_DEVICE_ID' w pliku config.json.")
import logging
from .sounddevice_loader import get_sounddevice, is_sounddevice_available

# Load sounddevice using our centralized loader
sd = get_sounddevice()
SOUNDDEVICE_AVAILABLE = is_sounddevice_available()
if SOUNDDEVICE_AVAILABLE:
    logging.getLogger(__name__).info("sounddevice loaded successfully via loader")
else:    logging.getLogger(__name__).warning("sounddevice not available - will be installed on demand")

def list_input_audio_devices():
    """Returns a list of available audio input device descriptions."""
    if not SOUNDDEVICE_AVAILABLE:
        return ["SoundDevice not available - audio devices cannot be listed"]
    
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

def get_microphone_devices():
    """Returns a list of available audio input devices in a format suitable for API responses.
    
    Returns:
        list: A list of dictionaries with device information
              Each dictionary contains: id, name, is_default
    """
    if not SOUNDDEVICE_AVAILABLE:
        return [{
            "id": "0",
            "name": "SoundDevice not available",
            "is_default": True
        }]
    
    try:
        devices = sd.query_devices()
        result = []
        default_input_device = sd.default.device[0]
        
        for i, device in enumerate(devices):
            if device.get('max_input_channels', 0) > 0:  # It's an input device (microphone)
                is_default = (i == default_input_device)
                result.append({
                    "id": str(i),
                    "name": device.get('name', f"Device {i}"),
                    "is_default": is_default
                })
        
        # If no devices were found, add a placeholder
        if not result:
            result.append({
                "id": "-1",
                "name": "No microphone devices found",
                "is_default": False
            })
            
        return result
    except Exception as e:
        logging.error(f"Error getting microphone devices: {str(e)}")
        # Return error indicator
        return [{"id": "-1", "name": f"Error retrieving devices: {str(e)}", "is_default": False}]

if __name__ == '__main__':
    # CLI behavior for listing devices
    print("Dostępne urządzenia wejściowe (mikrofony):")
    if not SOUNDDEVICE_AVAILABLE:
        print("SoundDevice nie jest dostępny - nie można wyświetlić urządzeń audio.")
    else:
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
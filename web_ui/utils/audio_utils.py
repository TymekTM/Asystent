import os
import sys
import subprocess
import tempfile
import sounddevice as sd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from audio_modules.ffmpeg_installer import ensure_ffmpeg_installed
from core.config import logger

def convert_audio(input_path: str) -> str:
    """Convert any audio file to WAV and return new path."""
    # Ensure ffmpeg is installed and available
    ensure_ffmpeg_installed()
    wav_path = input_path + '.wav'
    subprocess.run([
        'ffmpeg', '-y', '-i', input_path,
        '-ar', '16000', '-ac', '1', wav_path
    ], check=True, capture_output=True)
    return wav_path

def get_assistant_instance():
    """Get the assistant instance for audio processing."""
    from assistant import Assistant
    global _assistant_instance
    if '_assistant_instance' not in globals() or _assistant_instance is None:
        _assistant_instance = Assistant()
    return _assistant_instance

def transcribe_audio(wav_path: str) -> str:
    """Transcribe WAV file via assistant instance if available."""
    try:
        assistant = get_assistant_instance()
        if getattr(assistant, 'whisper_asr', None):
            return assistant.whisper_asr.transcribe(wav_path)
        if getattr(assistant, 'speech_recognizer', None):
            return assistant.speech_recognizer.transcribe_file(wav_path)
    except Exception:
        pass
    return ''

def cleanup_files(*paths: str):
    """Remove temp files, ignore errors."""
    for p in paths:
        try:
            os.remove(p)
        except Exception:
            pass

def get_audio_input_devices():
    """Gets a list of available audio input devices with IDs and names."""
    devices = []
    try:
        sd_devices = sd.query_devices()
        default_input_device_index = sd.default.device[0]  # Get default input device index
        for i, device in enumerate(sd_devices):
            if device['max_input_channels'] > 0:
                is_default = (i == default_input_device_index)
                devices.append({
                    "id": i,
                    "name": device['name'],
                    "is_default": is_default
                })
    except Exception as e:
        logger.error(f"Error querying audio devices: {e}")
        # Optionally return a default/error indicator
        devices.append({"id": "error", "name": "Nie można pobrać urządzeń", "is_default": False})
    return devices

# Pre-load assistant on startup to avoid delay on first message
_assistant_instance = None  # defer Assistant instantiation to avoid ASR load errors on startup

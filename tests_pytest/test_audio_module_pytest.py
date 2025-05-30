import pytest
# Defensive import for sounddevice to handle PyInstaller bundling issues
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError as e:
    sd = None
    SOUNDDEVICE_AVAILABLE = False
    pytest.skip(f"Sounddevice not available: {e}", allow_module_level=True)

from unittest.mock import patch, MagicMock
import sys
import os
import importlib # ADDED: For reloading modules
# REMOVED: import speech_recognition - will be imported from audio_modules if needed or mocked

# Add project root to sys.path to allow importing audio_modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from audio_modules import list_audio_devices
from audio_modules import tts_module
from audio_modules import wakeword_detector
from audio_modules import whisper_asr
# Import the config module directly to mock load_config
import config # MODIFIED: Import config directly
# REMOVED: from audio_modules import speech_recognition

# Mock config for tests
@pytest.fixture(autouse=True) # MODIFIED: Added autouse=True
def mock_config_for_audio_tests(monkeypatch):
    # --- Mock config values --- 
    sample_config = {
        "MIC_DEVICE_ID": 0, 
        "WAKE_WORD": "testword",
        "WHISPER_MODEL": "mock_whisper_model"
    }
    # MODIFIED: Mock config.load_config directly
    mocked_load_config = MagicMock(return_value=sample_config.copy())
    monkeypatch.setattr(config, 'load_config', mocked_load_config)
    monkeypatch.setattr(config, "CONFIG_FILE", "dummy_config.json") # Keep this for save_config if it's used

    # ADDED: Reload modules that might have loaded config at import time
    importlib.reload(list_audio_devices)
    importlib.reload(wakeword_detector) # MODIFIED: Uncommented to reload wakeword_detector
    importlib.reload(tts_module) # ADDED: Reload tts_module

    # --- Mock other audio components ---
    monkeypatch.setattr(whisper_asr, 'WhisperASR', MagicMock())

    # --- Comprehensive TTS Mocking ---
    # This aims to neutralize the global _tts_module_instance created on tts_module.py import
    original_tts_module_class = tts_module.TTSModule # Store original class

    # 1. Mock the TTSModule class itself, so any new instantiations are harmless mocks.
    #    This is for code that might do `TTSModule()`.
    mock_tts_class_level_instance = MagicMock(spec=original_tts_module_class) # Use original class for spec
    async def async_magic_mock_method(*args, **kwargs): return # Generic async no-op
    
    mock_tts_class_level_instance.speak = MagicMock(side_effect=async_magic_mock_method)
    mock_tts_class_level_instance.cancel = MagicMock()
    # Make TTSModule() return this pre-configured mock.
    monkeypatch.setattr(tts_module, 'TTSModule', MagicMock(return_value=mock_tts_class_level_instance))

    # 2. Aggressively mock the global _tts_module_instance that was created on tts_module.py import.
    #    This instance is the one that starts the problematic asyncio task and is used by the module-level speak().
    #    Replacing it with a MagicMock prevents its original __init__ from running and starting tasks.
    mock_global_tts_instance = MagicMock(spec=original_tts_module_class) # Use original class for spec
    mock_global_tts_instance.speak = MagicMock(side_effect=async_magic_mock_method) # Reuse async no-op
    mock_global_tts_instance.cancel = MagicMock()
    monkeypatch.setattr(tts_module, '_tts_module_instance', mock_global_tts_instance)

    # 2. Aggressively mock the global _tts_module_instance that was created on tts_module.py import.
    #    This instance is the one that starts the problematic thread and is used by tts_module.speak().
    if hasattr(tts_module, '_tts_module_instance') and tts_module._tts_module_instance is not None:
        original_global_instance = tts_module._tts_module_instance

        # Patch its _start_cleanup_task to do nothing.
        # Note: This is on the instance; _start_cleanup_task in __init__ already ran.
        # This is more of a safeguard if it were called again.
        monkeypatch.setattr(original_global_instance, '_start_cleanup_task', MagicMock())

        # Patch its _cleanup_temp_files_loop so if the thread is already running, 
        # it calls this harmless async function and exits quickly.
        monkeypatch.setattr(original_global_instance, '_cleanup_temp_files_loop', MagicMock(side_effect=async_magic_mock_method))
        
        # Patch its speak and cancel methods to be no-op async/sync mocks.
        monkeypatch.setattr(original_global_instance, 'speak', MagicMock(side_effect=async_magic_mock_method))
        monkeypatch.setattr(original_global_instance, 'cancel', MagicMock())
        
        # Attempt to stop any ongoing subprocess if current_process exists
        if hasattr(original_global_instance, 'current_process') and original_global_instance.current_process:
            try:
                original_global_instance.current_process.terminate()
                original_global_instance.current_process.wait(timeout=0.1)
            except Exception: # Broad except as we just want to try to clean up
                pass # Ignore errors during this best-effort cleanup
            monkeypatch.setattr(original_global_instance, 'current_process', None)

    # --- Mock Wakeword components (no longer SpeechRecognition specific) ---
    monkeypatch.setattr(wakeword_detector, 'play_beep', MagicMock())


@pytest.fixture
def mock_sd_devices():
    """Mocks sounddevice.query_devices() to return a list of dummy devices."""
    devices = [
        {"name": "Device 0 (Input)", "hostapi": 0, "max_input_channels": 2, "index": 0},
        {"name": "Device 1 (Output)", "hostapi": 0, "max_output_channels": 2, "index": 1},
        {"name": "Device 2 (Input/Output)", "hostapi": 1, "max_input_channels": 1, "max_output_channels": 2, "index": 2},
        {"name": "Device 3 (Input)", "hostapi": 0, "max_input_channels": 1, "index": 3},
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        yield devices

def test_list_input_audio_devices_success(mock_sd_devices): # REMOVED mock_config_for_audio_tests
    """Test listing input audio devices."""
    input_devices = list_audio_devices.list_input_audio_devices()
    assert len(input_devices) == 3 # Device 0, 2, 3
    assert "Device 0 (Input)" in input_devices[0]
    assert "Device 2 (Input/Output)" in input_devices[1] # Check correct mapping
    assert "Device 3 (Input)" in input_devices[2]
    assert "(Index: 0)" in input_devices[0]
    assert "(Index: 2)" in input_devices[1]
    assert "(Index: 3)" in input_devices[2]


def test_list_input_audio_devices_no_devices(monkeypatch): # REMOVED mock_config_for_audio_tests
    """Test listing input audio devices when no devices are available."""
    monkeypatch.setattr(sd, "query_devices", lambda: [])
    input_devices = list_audio_devices.list_input_audio_devices()
    assert len(input_devices) == 0

def test_list_input_audio_devices_query_devices_error(monkeypatch): # REMOVED mock_config_for_audio_tests
    """Test listing input audio devices when sounddevice.query_devices() raises an error."""
    def mock_query_devices_error():
        raise sd.PortAudioError("Test error")
    monkeypatch.setattr(sd, "query_devices", mock_query_devices_error)
    
    input_devices = list_audio_devices.list_input_audio_devices()
    assert len(input_devices) == 1
    assert "Could not retrieve audio devices" in input_devices[0]

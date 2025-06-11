import json
import importlib
from pathlib import Path
from types import SimpleNamespace

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mode_integrator
from client.audio_modules.bing_tts_module import TTSModule as BingTTS
from client.audio_modules.tts_module import TTSModule as OpenAITTS

# Dummy ASR classes used for testing to avoid heavy loading
class DummyWhisperASR:
    pass

class DummyOpenAIASR:
    pass

MODE_FILE = None  # Placeholder, will be set dynamically in tests using tmp_path

def _set_mode(mode: str, mode_file: Path):
    data = {"current_mode": mode}
    with mode_file.open('w', encoding='utf-8') as f:
        json.dump(data, f)

def _reload_integrator(monkeypatch):
    return importlib.reload(mode_integrator)

def test_poor_man_mode(monkeypatch, tmp_path):
    mode_file = tmp_path / "user_modes.json"
    _set_mode('poor_man', mode_file)
    monkeypatch.setattr('client.audio_modules.whisper_asr.create_whisper_asr', lambda config=None: DummyWhisperASR())
    monkeypatch.setattr('client.audio_modules.openai_asr.create_openai_asr', lambda config=None: DummyOpenAIASR())
    monkeypatch.setattr('mode_integrator.MODE_FILE', mode_file)  # Redirect MODE_FILE to temporary file
    mi = _reload_integrator(monkeypatch)
    assert isinstance(mi.user_integrator.tts_module, BingTTS)
    assert isinstance(mi.user_integrator.asr_module, DummyWhisperASR)

def test_paid_mode(monkeypatch, tmp_path):
    mode_file = tmp_path / "user_modes.json"
    _set_mode('paid', mode_file)
    monkeypatch.setattr('client.audio_modules.whisper_asr.create_whisper_asr', lambda config=None: DummyWhisperASR())
    monkeypatch.setattr('client.audio_modules.openai_asr.create_openai_asr', lambda config=None: DummyOpenAIASR())
    monkeypatch.setattr('mode_integrator.MODE_FILE', mode_file)  # Redirect MODE_FILE to temporary file
    mi = _reload_integrator(monkeypatch)
    assert isinstance(mi.user_integrator.tts_module, OpenAITTS)
    assert isinstance(mi.user_integrator.asr_module, DummyOpenAIASR)

import os
import pytest
from pathlib import Path
from modules.see_screen_module import capture_screen

class DummyDevice:
    def grab(self):
        return b'data'

class DummyImg:
    def save(self, path):
        open(path, 'wb').close()

def test_no_libraries(monkeypatch, tmp_path):
    # No capture libraries available
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', None)
    monkeypatch.setattr('modules.see_screen_module.pyautogui', None)
    monkeypatch.setattr('modules.see_screen_module.ImageGrab', None)
    # Ensure encode and beep not called
    res = capture_screen("any", conversation_history=None)
    assert res == "Nie można wykonać zrzutu ekranu - brak odpowiedniej biblioteki."


def test_os_makedirs_exception(monkeypatch, tmp_path):
    # Simulate error creating directory
    monkeypatch.chdir(tmp_path)
    def fake_mkdir(path, exist_ok=False):
        raise OSError("mkdir failed")
    monkeypatch.setattr('os.makedirs', fake_mkdir)
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', None)
    monkeypatch.setattr('modules.see_screen_module.pyautogui', None)
    monkeypatch.setattr('modules.see_screen_module.ImageGrab', None)
    res = capture_screen("", conversation_history=None)
    assert "Błąd przy wykonywaniu zrzutu ekranu: mkdir failed" in res


def test_chat_exception_returns_error(monkeypatch, tmp_path):
    # Simulate dxcam capture then chat exception
    monkeypatch.chdir(tmp_path)
    # Setup dxcam
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', DummyDevice())
    # Codec library present
    class Cv2Mod:
        @staticmethod
        def imwrite(p, arr): open(p, 'wb').close()
    monkeypatch.setattr('modules.see_screen_module.cv2', Cv2Mod)
    # Disable beep and encode
    monkeypatch.setattr('modules.see_screen_module.play_beep', lambda t: None)
    monkeypatch.setattr('modules.see_screen_module.encode_image_to_base64', lambda p: 'img')
    # Chat raises
    def fake_chat(**kwargs):
        raise RuntimeError("chat fail")
    monkeypatch.setattr('modules.see_screen_module.chat_with_providers', fake_chat)
    # Now call with conversation to force chat
    res = capture_screen("param", conversation_history=[{}])
    assert "Błąd przy wykonywaniu zrzutu ekranu: chat fail" in res

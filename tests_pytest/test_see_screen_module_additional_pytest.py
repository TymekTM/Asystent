import os
import pytest
from pathlib import Path

from modules.see_screen_module import capture_screen

# Dummy classes for testing
class DummyImg:
    def save(self, path):
        open(path, 'wb').close()

class DummyGrabDev:
    def __init__(self, arr=None):
        self._arr = arr

    def grab(self):
        return self._arr

@pytest.fixture(autouse=True)
def disable_beep(monkeypatch):
    # Disable beep to avoid side effects
    monkeypatch.setattr('modules.see_screen_module.play_beep', lambda t: None)
    yield


def test_dxcam_error_no_cv2(tmp_path, monkeypatch):
    # Simulate dxcam present but cv2 missing
    monkeypatch.chdir(tmp_path)
    # Set dxcam_device to device that returns a dummy array
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', DummyGrabDev(arr=object()))
    # Remove cv2
    monkeypatch.setattr('modules.see_screen_module.cv2', None)

    result = capture_screen("", conversation_history=[])
    assert "cv2 nie jest dostępne" in result


def test_dxcam_grab_returns_none(tmp_path, monkeypatch):
    # Simulate dxcam present but grab returns None
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', DummyGrabDev(arr=None))
    # Provide dummy cv2 to reach grab-none branch
    monkeypatch.setattr('modules.see_screen_module.cv2', type('cv2', (), {
        'imwrite': staticmethod(lambda p, a: None)
    }))

    result = capture_screen("test", conversation_history=[])
    assert "DXcam zwrócił None" in result


def test_fallback_imagegrab_cleanup(tmp_path, monkeypatch):
    # Simulate no dxcam, no pyautogui, but ImageGrab available
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', None)
    monkeypatch.setattr('modules.see_screen_module.pyautogui', None)

    # Dummy PIL ImageGrab
    class DummyIG:
        @staticmethod
        def grab():
            return DummyImg()
    monkeypatch.setattr('modules.see_screen_module.ImageGrab', DummyIG)

    # Patch base64 encoding
    monkeypatch.setattr('modules.see_screen_module.encode_image_to_base64', lambda p: "base64str")
    result = capture_screen("?", conversation_history=None)
    assert result == "base64str"

    # The file should have been removed but folder remains
    screenshots = Path(tmp_path) / "screenshots"
    assert screenshots.exists()
    assert list(screenshots.iterdir()) == []


def test_file_persistence_with_conversation(tmp_path, monkeypatch):
    # Simulate dxcam capture with conversation
    monkeypatch.chdir(tmp_path)
    dummy_arr = object()
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', DummyGrabDev(arr=dummy_arr))
    # Dummy cv2 to write file
    def fake_imwrite(p, a):
        open(p, 'wb').close()
    monkeypatch.setattr('modules.see_screen_module.cv2', type('cv2', (), {'imwrite': staticmethod(fake_imwrite)}))

    # Patch encoding
    monkeypatch.setattr('modules.see_screen_module.encode_image_to_base64', lambda p: "b64data")

    # Capture chat arguments
    captured = {}
    def fake_chat(model, messages, images):
        captured['messages'] = messages
        captured['images'] = images
        return {"message": {"content": "reply content"}}
    monkeypatch.setattr('modules.see_screen_module.chat_with_providers', fake_chat)
    monkeypatch.setattr('modules.see_screen_module.remove_chain_of_thought', lambda x: x)

    out = capture_screen("paramX", conversation_history=[{'role':'user','content':'hello'}])
    assert out == "reply content"

    # Screenshot file should persist
    screenshots = Path(tmp_path) / "screenshots"
    files = list(screenshots.iterdir())
    assert len(files) == 1
    # Ensure correct message content and image passed
    assert any("paramX" in m.get('content', '') for m in captured['messages'])
    assert captured['images'] == ["b64data"]

import os
import base64
import pytest
from pathlib import Path

from modules.see_screen_module import encode_image_to_base64, capture_screen, dxcam_device

# Dummy classes for testing
class DummyImg:
    def save(self, path):
        open(path, 'wb').close()

class DummyGrabDev:
    def __init__(self, arr=None):
        self._arr = arr

    def grab(self):
        return self._arr

class DummyDevice:
    def grab(self):
        return b'data'

@pytest.fixture(autouse=True)
def disable_beep(monkeypatch):
    # Disable beep to avoid side effects
    monkeypatch.setattr('modules.see_screen_module.play_beep', lambda t: None)
    yield

def test_encode_image_to_base64(tmp_path):
    f = tmp_path / "img.png"
    content = b"\x89PNG\r\n\x1a\n"
    f.write_bytes(content)
    b64 = encode_image_to_base64(str(f))
    assert isinstance(b64, str)
    assert base64.b64decode(b64).startswith(b"\x89PNG")

@ pytest.mark.parametrize("device,expected", [
    (True, True),
    (False, False)
])
def test_capture_screen_fallback(tmp_path, monkeypatch, device, expected):
    # Simulate absence of dxcam_device
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', None)
    # patch pyautogui
    class DummyImg:
        def save(self, p): open(p, 'wb')
    class DummyPG:
        @staticmethod
        def screenshot(): return DummyImg()
    monkeypatch.setattr('modules.see_screen_module.pyautogui', DummyPG)
    # patch encode to return known str
    monkeypatch.setattr('modules.see_screen_module.encode_image_to_base64', lambda p: "fakeimg")
    # ignore play_beep
    monkeypatch.setattr('modules.see_screen_module.play_beep', lambda t: None)
    out = capture_screen("param", conversation_history=None)
    assert out == "fakeimg"

def test_capture_with_conversation(monkeypatch, tmp_path):
    # Change cwd so screenshots written to tmp_path/screenshots
    monkeypatch.chdir(tmp_path)
    # monkeypatch dxcam_device to return dummy image array
    class DummyArr: pass
    class DummyDev:
        def grab(self):
            return DummyArr()
    monkeypatch.setattr('modules.see_screen_module.dxcam_device', DummyDev())
    # patch beep and cv2.imwrite, encode and chat
    monkeypatch.setattr('modules.see_screen_module.play_beep', lambda t: None)
    def fake_imwrite(path, arr): open(path, 'wb').close()
    monkeypatch.setattr('modules.see_screen_module.cv2', type('cv2', (), {'imwrite': staticmethod(fake_imwrite)}))
    monkeypatch.setattr('modules.see_screen_module.encode_image_to_base64', lambda p: "b64")
    monkeypatch.setattr('modules.see_screen_module.chat_with_providers', lambda **kwargs: {"message": {"content": "out"}})
    monkeypatch.setattr('modules.see_screen_module.remove_chain_of_thought', lambda x: x)
    # Invoke
    out = capture_screen("what?", conversation_history=[{'role':'user','content':'hi'}])
    assert out == "out"

def test_register_structure():
    reg = capture_screen.__self__ if hasattr(capture_screen, '__self__') else None
    # Instead directly import register
    from modules.see_screen_module import register
    r = register()
    assert 'command' in r and 'handler' in r

# Additional tests from test_see_screen_module_additional_pytest.py and edge_cases
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

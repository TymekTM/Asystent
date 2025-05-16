import os
import base64
import pytest
from modules.see_screen_module import encode_image_to_base64, capture_screen, dxcam_device

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

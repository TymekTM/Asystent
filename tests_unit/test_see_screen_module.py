import sys
import os
# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import unittest
import os
import base64
from unittest.mock import patch, MagicMock
from modules import see_screen_module

class TestSeeScreenModule(unittest.TestCase):
    @patch("modules.see_screen_module.dxcam")
    def test_dxcam_device_init(self, mock_dxcam):
        # Sprawdza czy dxcam_device jest inicjalizowane
        mock_dxcam.create.return_value = MagicMock()
        import importlib
        importlib.reload(see_screen_module)
        self.assertTrue(hasattr(see_screen_module, "dxcam_device"))

    def test_encode_image_to_base64(self):
        # Tworzy tymczasowy plik obrazu
        test_path = "test_img.png"
        with open(test_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        result = see_screen_module.encode_image_to_base64(test_path)
        self.assertIsInstance(result, str)
        os.remove(test_path)

    @patch("modules.see_screen_module.dxcam_device", None)
    @patch("modules.see_screen_module.pyautogui")
    @patch("modules.see_screen_module.encode_image_to_base64") # Mock encoding
    @patch("os.makedirs") # Mock directory creation
    @patch("os.path.exists", return_value=True) # Assume directory exists
    def test_capture_screen_fallback(self, mock_exists, mock_makedirs, mock_encode, mock_pyautogui):
        # Sprawdza fallback na pyautogui i mockuje operacje plikowe
        mock_screenshot = MagicMock()
        mock_pyautogui.screenshot.return_value = mock_screenshot
        mock_encode.return_value = "fake_base64_string"
        result = see_screen_module.capture_screen("test", conversation_history=None)
        mock_pyautogui.screenshot.assert_called_once()
        mock_screenshot.save.assert_called_once() # Check if save was called
        mock_encode.assert_called_once() # Check if encode was called
        self.assertEqual(result, "fake_base64_string")

    def test_register(self):
        reg = see_screen_module.register()
        self.assertIn("command", reg)
        self.assertIn("handler", reg)

if __name__ == '__main__':
    unittest.main()

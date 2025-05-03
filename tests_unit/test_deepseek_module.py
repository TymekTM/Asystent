import sys
import os
# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import unittest
from unittest.mock import patch, MagicMock
from modules import deepseek_module

class TestDeepseekModule(unittest.TestCase):
    @patch("modules.deepseek_module.play_beep")
    @patch("modules.deepseek_module.chat_with_providers")
    @patch("modules.deepseek_module.remove_chain_of_thought", side_effect=lambda x: x)
    def test_deep_reasoning_handler_success(self, mock_remove_cot, mock_chat, mock_beep):
        mock_chat.return_value = {"message": {"content": "Wynik"}}
        result = deepseek_module.deep_reasoning_handler("test", conversation_history=None)
        self.assertEqual(result, "Wynik")
        mock_beep.assert_called_once_with("deep")
        mock_chat.assert_called()
        mock_remove_cot.assert_called()

    def test_deep_reasoning_handler_empty_params(self):
        result = deepseek_module.deep_reasoning_handler("")
        self.assertIn("Podaj treść", result)

    @patch("modules.deepseek_module.play_beep")
    @patch("modules.deepseek_module.chat_with_providers", side_effect=Exception("fail"))
    def test_deep_reasoning_handler_exception(self, mock_chat, mock_beep):
        result = deepseek_module.deep_reasoning_handler("test")
        self.assertIn("Błąd w deep reasoning", result)

    def test_register(self):
        reg = deepseek_module.register()
        self.assertIn("command", reg)
        self.assertIn("handler", reg)

if __name__ == '__main__':
    unittest.main()

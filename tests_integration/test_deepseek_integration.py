import unittest
from unittest.mock import patch, MagicMock
from modules.deepseek_module import deep_reasoning_handler, register

class TestDeepseekIntegration(unittest.TestCase):
    @patch("modules.deepseek_module.chat_with_providers")
    @patch("modules.deepseek_module.play_beep")
    @patch("modules.deepseek_module.remove_chain_of_thought", side_effect=lambda x: x)
    def test_deepseek_full_flow(self, mock_remove, mock_beep, mock_chat):
        mock_chat.return_value = {"message": {"content": "Integracja OK"}}
        # Obtain handler from register
        handler = register()["handler"]
        # Call with conversation_history to go through full path
        result = handler("integration test", conversation_history=[{"role":"user","content":"hi"}])
        self.assertEqual(result, "Integracja OK")
        mock_beep.assert_called_once_with("deep")
        mock_chat.assert_called()

if __name__ == '__main__':
    unittest.main()

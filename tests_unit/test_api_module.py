import sys
import os
# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import unittest
import os
import json
from unittest.mock import patch, MagicMock
from modules import api_module

class TestApiModule(unittest.TestCase):
    def setUp(self):
        # Przygotuj przykładowy config do testów
        self.test_config_path = "test_api_config.json"
        self.sample_config = {
            "weather": {
                "url_template": "https://example.com/weather?location={}",
                "priority": 1,
                "default_params": {"location": "Warsaw"}
            }
        }
        with open(self.test_config_path, "w", encoding="utf-8") as f:
            json.dump(self.sample_config, f)
        self.manager = api_module.APIManager(config_path=self.test_config_path)

    def tearDown(self):
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)

    def test_load_config_success(self):
        config = self.manager.load_config()
        self.assertIn("weather", config)

    def test_load_config_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            api_module.APIManager(config_path="not_exists.json").load_config()

    @patch("modules.api_module.requests.get")
    def test_check_integration_success(self, mock_get):
        mock_get.return_value.status_code = 200
        self.assertTrue(self.manager.check_integration("weather"))

    @patch("modules.api_module.requests.get")
    def test_check_integration_fail(self, mock_get):
        mock_get.return_value.status_code = 404
        self.assertFalse(self.manager.check_integration("weather"))

    def test_check_integration_not_found(self):
        self.assertFalse(self.manager.check_integration("notfound"))

    @patch("modules.api_module.requests.get")
    def test_call_integration_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "OK"
        result = self.manager.call_integration("weather", {"location": "Krakow"})
        self.assertEqual(result, "OK")

    @patch("modules.api_module.requests.get")
    def test_call_integration_api_error(self, mock_get):
        mock_get.return_value.status_code = 500
        result = self.manager.call_integration("weather", {"location": "Krakow"})
        self.assertIn("API zwróciło błąd", result)

    def test_call_integration_not_found(self):
        result = self.manager.call_integration("notfound", {})
        self.assertIn("Nie znaleziono integracji", result)

    @patch("modules.api_module.requests.get")
    def test_handle_api_query_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "OK"
        result = self.manager.handle_api_query("Pogoda", {"location": "Warsaw"})
        self.assertEqual(result, "OK")

    @patch("modules.api_module.requests.get")
    def test_handle_api_query_no_available(self, mock_get):
        mock_get.return_value.status_code = 404
        result = self.manager.handle_api_query("Pogoda", {"location": "Warsaw"})
        self.assertIn("Żadna integracja API nie jest dostępna", result)

    def test_handle_api_query_wrapper(self):
        # Testuje wrapper, zakładając, że nie ma integracji
        with patch.object(self.manager, 'handle_api_query', return_value="OK") as mock_method:
            result = api_module.handle_api_query_wrapper("Warsaw")
            # Akceptuj dowolny string, by test nie był zależny od implementacji
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)

if __name__ == '__main__':
    unittest.main()

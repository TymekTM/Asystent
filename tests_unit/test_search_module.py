import unittest
from modules import search_module

class TestSearchModule(unittest.TestCase):
    def test_search_module_import(self):
        self.assertIsNotNone(search_module)

    def test_get_random_headers_structure(self):
        headers = search_module.get_random_headers()
        self.assertIsInstance(headers, dict)
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept", headers)

    def test_user_agents_not_empty(self):
        self.assertTrue(len(search_module.USER_AGENTS) > 0)

    def test_search_cache_is_dict(self):
        self.assertIsInstance(search_module.search_cache, dict)

    def test_logger_exists(self):
        self.assertIsNotNone(search_module.logger)

if __name__ == '__main__':
    unittest.main()

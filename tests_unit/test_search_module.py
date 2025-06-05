import sys
import os
# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import unittest
from unittest.mock import patch
import asyncio
import inspect

from modules import search_module

class TestSearchModule(unittest.TestCase):
    def test_search_module_import(self):
        self.assertIsNotNone(search_module)

    def test_get_random_headers_structure(self):
        # Use the correct name 'random_headers'
        headers = search_module.random_headers()
        self.assertIsInstance(headers, dict)
        self.assertIn('User-Agent', headers)
        self.assertIn('Accept', headers)

    def test_user_agents_not_empty(self):
        self.assertTrue(len(search_module.USER_AGENTS) > 0)

    def test_search_cache_is_dict(self):
        # Check the SearchCache class exists
        self.assertTrue(inspect.isclass(search_module.SearchCache))

    @patch('modules.search_module.DDGS')
    def test_search_ddg_success(self, mock_ddgs):
        mock_instance = mock_ddgs.return_value
        mock_instance.text.return_value = [{'href': 'http://example.com'}]
        search_module._ddgs = mock_instance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(search_module._search_duckduckgo("hello"))
        loop.close()
        self.assertEqual(result, ['http://example.com'])

if __name__ == '__main__':
    unittest.main()

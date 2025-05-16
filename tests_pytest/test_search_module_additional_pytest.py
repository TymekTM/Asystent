import pytest
import asyncio
import time
from modules.search_module import (
    normalize_query,
    is_similar,
    random_headers,
    extract_text,
    SearchCache,
    PAGE_CHAR_LIMIT,
)


def test_normalize_query_removes_punctuation_and_lower():
    assert normalize_query("Hello, World!") == "hello world"
    assert normalize_query("Test--Test") == "testtest"


def test_is_similar_true_and_false():
    assert is_similar("one two three", "three two one")
    assert not is_similar("", "test")
    assert not is_similar("a b", "c d")


def test_random_headers_keys_and_values():
    headers = random_headers()
    assert isinstance(headers, dict)
    assert 'User-Agent' in headers
    assert 'Accept' in headers


def test_extract_text_paragraphs():
    html = "<html><body><p>First</p><p>Second</p><p>Third</p></body></html>"
    assert extract_text(html) == "First Second Third"


def test_search_cache_put_get_and_evict(monkeypatch):
    cache = SearchCache(maxlen=2)
    now = time.time()
    # put two entries
    cache.put('a', (now, 'param', 'resA'))
    cache.put('b', (now, 'param', 'resB'))
    # get existing
    assert cache.get('a', now) == 'resA'
    # add third entry to evict oldest entry
    cache.put('c', (now, 'param', 'resC'))
    assert cache.get('b', now) == 'resB'
    assert cache.get('a', now) is None


def test_search_handler_empty_param(monkeypatch):
    import modules.search_module as sm
    coro = sm.search_handler("", None)
    result = asyncio.get_event_loop().run_until_complete(coro)
    assert "Podaj zapytanie wyszukiwania" in result

@pytest.mark.asyncio
async def test_search_handler_no_results(monkeypatch):
    import modules.search_module as sm
    # monkeypatch duckduckgo search to return empty
    monkeypatch.setattr(sm, '_search_duckduckgo', lambda query: [])
    res = await sm.search_handler("query", None)
    assert res == "Nie znaleziono wyników."

@pytest.mark.asyncio
async def test_search_handler_fetch_and_summary(monkeypatch):
    import modules.search_module as sm
    # simulate duckduckgo returns list of urls
    monkeypatch.setattr(sm, '_search_duckduckgo', lambda q: ["url1"])
    # simulate httpx.AsyncClient context manager
    class DummyResp:
        def __init__(self, content):
            self.status_code = 200
            self.headers = {"content-type": "text/html"}
            self.content = content

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def get(self, url, headers, follow_redirects):
            return DummyResp(b"<html><body><p>Test content</p></body></html>")

    monkeypatch.setattr(sm.httpx, 'AsyncClient', DummyClient)
    # disable beep
    monkeypatch.setattr(sm, 'play_beep', lambda *args, **kwargs: None)
    # monkeypatch chat and removal
    monkeypatch.setattr(sm, 'chat_with_providers', lambda *args, **kwargs: {"message": {"content": "summ"}})
    monkeypatch.setattr(sm, 'remove_chain_of_thought', lambda s: s)
    res = await sm.search_handler("query", None)
    assert "summ" in res

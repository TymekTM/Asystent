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
    search_handler,
    _search_cache,
    USER_AGENTS,
)


@pytest.mark.parametrize("input,expected", [
    ("Hello, World!", "hello world"),
    ("TEST? query.", "test query"),
])
def test_normalize_query(input, expected):
    assert normalize_query(input) == expected


def test_normalize_query_removes_punctuation_and_lower():
    assert normalize_query("Hello, World!") == "hello world"
    assert normalize_query("Test--Test") == "testtest"


def test_is_similar_true():
    q1 = "this is a test"
    q2 = "this is test"
    assert is_similar(q1, q2)


def test_is_similar_true_and_false():
    assert is_similar("one two three", "three two one")
    assert not is_similar("", "test")
    assert not is_similar("a b", "c d")


def test_is_similar_false():
    assert not is_similar("a b c", "x y z")


def test_random_headers_structure():
    hdr = random_headers()
    assert isinstance(hdr, dict)
    assert 'User-Agent' in hdr and 'Accept' in hdr
    assert hdr['User-Agent'] in USER_AGENTS


def test_random_headers_keys_and_values():
    headers = random_headers()
    assert isinstance(headers, dict)
    assert 'User-Agent' in headers
    assert 'Accept' in headers


def test_extract_text():
    html = '<html><body><p>First</p><p>Second</p></body></html>'
    txt = extract_text(html)
    assert 'First' in txt and 'Second' in txt


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


def test_search_handler_cached(monkeypatch):
    # Preload cache and run handler synchronously
    key = normalize_query("cached test")
    # Insert cache with current timestamp to avoid TTL expiration
    now = pytest.importorskip('time').time()
    _search_cache.put(key, (now, "cached test", "CACHED_RESULT"))
    res = asyncio.run(search_handler("cached test"))
    assert res == "CACHED_RESULT"


def test_search_handler_flow(monkeypatch):
    # Simulate no cache and run handler synchronously
    monkeypatch.setattr('modules.search_module._search_cache.get', lambda q, now: None)
    # patch play_beep to accept two args (name, blocking)
    monkeypatch.setattr('modules.search_module.play_beep', lambda name, block=False: None)
    # return a coroutine to await
    monkeypatch.setattr('modules.search_module._search_duckduckgo', lambda q: asyncio.sleep(0, result=["http://a", "http://b"]))
    monkeypatch.setattr('modules.search_module._fetch_page', lambda client, url: asyncio.sleep(0, result=f"text from {url}"))
    monkeypatch.setattr('modules.search_module.chat_with_providers', lambda model, msgs: {"message": {"content": " summary "}})
    monkeypatch.setattr('modules.search_module.remove_chain_of_thought', lambda x: x)
    result = asyncio.run(search_handler("test query"))
    assert "summary" in result


def test_search_handler_no_results(monkeypatch):
    # Simulate no results and run handler synchronously
    monkeypatch.setattr('modules.search_module._search_cache.get', lambda q, now: None)
    # patch play_beep to accept two args (name, blocking)
    monkeypatch.setattr('modules.search_module.play_beep', lambda name, block=False: None)
    # return a coroutine to await
    monkeypatch.setattr('modules.search_module._search_duckduckgo', lambda q: asyncio.sleep(0, result=[]))
    res = asyncio.run(search_handler("nothing"))
    assert "Nie znaleziono wyników" in res or "Nie udało się" in res


def test_search_handler_empty_param(monkeypatch):
    import modules.search_module as sm

    coro = sm.search_handler("", None)
    result = asyncio.get_event_loop().run_until_complete(coro)
    assert "Podaj zapytanie wyszukiwania" in result


@pytest.mark.asyncio
async def test_search_handler_no_results_async(monkeypatch):
    import modules.search_module as sm

    # monkeypatch duckduckgo search to return empty
    monkeypatch.setattr(sm, "_search_duckduckgo", lambda query: [])
    res = await sm.search_handler("query", None)
    assert res == "Nie znaleziono wyników."


@pytest.mark.asyncio
async def test_search_handler_fetch_and_summary(monkeypatch):
    import modules.search_module as sm

    # simulate duckduckgo returns list of urls
    monkeypatch.setattr(sm, "_search_duckduckgo", lambda q: ["url1"])

    # simulate httpx.AsyncClient context manager
    class DummyResp:
        def __init__(self, content):
            self.status_code = 200
            self.headers = {"content-type": "text/html"}
            self.content = content

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def get(self, url, headers, follow_redirects):
            return DummyResp(b"<html><body><p>Test content</p></body></html>")

    monkeypatch.setattr(sm.httpx, "AsyncClient", DummyClient)

    # disable beep
    monkeypatch.setattr(sm, "play_beep", lambda *args, **kwargs: None)

    # monkeypatch chat and removal
    monkeypatch.setattr(sm, "chat_with_providers", lambda *args, **kwargs: {"message": {"content": "summ"}})
    monkeypatch.setattr(sm, "remove_chain_of_thought", lambda s: s)
    res = await sm.search_handler("query", None)
    assert "summ" in res

import pytest
import asyncio
from modules.search_module import (
    normalize_query, is_similar, random_headers, extract_text,
    search_handler, _search_cache, USER_AGENTS
)
from bs4 import BeautifulSoup

@ pytest.mark.parametrize("input,expected", [
    ("Hello, World!", "hello world"),
    ("TEST? query.", "test query"),
])
def test_normalize_query(input, expected):
    assert normalize_query(input) == expected

def test_is_similar_true():
    q1 = "this is a test"
    q2 = "this is test"
    assert is_similar(q1, q2)

def test_is_similar_false():
    assert not is_similar("a b c", "x y z")

def test_random_headers_structure():
    hdr = random_headers()
    assert isinstance(hdr, dict)
    assert 'User-Agent' in hdr and 'Accept' in hdr
    assert hdr['User-Agent'] in USER_AGENTS

def test_extract_text():
    html = '<html><body><p>First</p><p>Second</p></body></html>'
    txt = extract_text(html)
    assert 'First' in txt and 'Second' in txt

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

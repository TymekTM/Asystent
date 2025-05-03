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

@ pytest.mark.asyncio
async def test_search_handler_cached(monkeypatch):
    # Preload cache
    key = normalize_query("cached test")
    _search_cache.put(key, (0, "cached test", "CACHED_RESULT"))
    res = await search_handler("cached test")
    assert res == "CACHED_RESULT"

@ pytest.mark.asyncio
async def test_search_handler_flow(monkeypatch):
    # Simulate no cache
    monkeypatch.setattr('modules.search_module._search_cache.get', lambda q, now: None)
    # patch play_beep to no-op
    monkeypatch.setattr('modules.search_module.play_beep', lambda t: None)
    # simulate DuckDuckGo URLs
    monkeypatch.setattr('modules.search_module._search_duckduckgo', lambda q: ["http://a", "http://b"] )
    # patch _fetch_page to return dummy text
    monkeypatch.setattr('modules.search_module._fetch_page', lambda client, url: asyncio.sleep(0, result=f"text from {url}"))
    # patch chat_with_providers
    monkeypatch.setattr('modules.search_module.chat_with_providers', lambda model, msgs: {"message": {"content": " summary "}})
    # ensure no remove markers
    monkeypatch.setattr('modules.search_module.remove_chain_of_thought', lambda x: x)
    result = await search_handler("test query")
    assert "summary" in result

@ pytest.mark.asyncio
async def test_search_handler_no_results(monkeypatch):
    monkeypatch.setattr('modules.search_module._search_cache.get', lambda q, now: None)
    monkeypatch.setattr('modules.search_module.play_beep', lambda t: None)
    monkeypatch.setattr('modules.search_module._search_duckduckgo', lambda q: [])
    res = await search_handler("nothing")
    assert "Nie znaleziono wyników" in res or "Nie udało się" in res

# pytest tests for open_web_module
import pytest
import webbrowser
from modules.open_web_module import open_web_handler, register


def test_open_web_no_url():
    """Empty or whitespace-only params should prompt for URL."""
    assert open_web_handler("") == "Podaj adres URL po komendzie !open"
    assert open_web_handler("   ") == "Podaj adres URL po komendzie !open"


def test_open_web_add_scheme_and_success(monkeypatch):
    """URL without scheme gets http:// added and open succeeds."""
    called = {}
    def fake_open(url):
        called['url'] = url
        return True
    monkeypatch.setattr(webbrowser, 'open', fake_open)
    res = open_web_handler("example.com/test")
    assert "Otwieram stronę: http://example.com/test" in res
    assert called['url'] == "http://example.com/test"


def test_open_web_with_scheme_and_failure(monkeypatch):
    """URL with scheme and open failure returns error message."""
    called = {}
    def fake_open(url):
        called['url'] = url
        return False
    monkeypatch.setattr(webbrowser, 'open', fake_open)
    res = open_web_handler("https://example.com")
    assert "Nie mogę otworzyć strony: https://example.com" in res
    assert called['url'] == "https://example.com"


def test_open_web_exception(monkeypatch):
    """Exceptions during open are caught and reported."""
    def fake_open(url):
        raise RuntimeError("fail open")
    monkeypatch.setattr(webbrowser, 'open', fake_open)
    res = open_web_handler("example.com")
    assert "Nie mogę otworzyć strony: fail open" in res


def test_open_web_dict_param(monkeypatch):
    """Handler supports dict params with 'url' key."""
    called = {}
    monkeypatch.setattr(webbrowser, 'open', lambda url: called.setdefault('url', url) or True)
    res = open_web_handler({"url": "mysite.com"})
    assert "Otwieram stronę: http://mysite.com" in res
    assert called['url'] == "http://mysite.com"
    
def test_register_structure():
    """Plugin registration returns proper structure."""
    reg = register()
    assert isinstance(reg, dict)
    assert reg.get('command') == 'open'
    assert 'handler' in reg and callable(reg['handler'])

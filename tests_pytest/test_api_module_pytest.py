import os
import json
import pytest
from modules.api_module import APIManager, handle_api_query_wrapper

@pytest.fixture
def config_file(tmp_path):
    config = tmp_path / "config.json"
    data = {
        "a": {"url_template": "http://example.com/a?loc={}", "priority": 10, "default_params": {"location": "X"}},
        "b": {"url_template": "http://example.com/b?loc={}", "priority": 5, "default_params": {"location": "Y"}}
    }
    config.write_text(json.dumps(data), encoding='utf-8')
    return str(config)

@pytest.fixture
def manager(config_file):
    return APIManager(config_path=config_file)

def test_load_config_success(manager):
    cfg = manager.load_config()
    assert "a" in cfg and "b" in cfg

def test_load_config_not_found(tmp_path):
    fake = tmp_path / "no.json"
    with pytest.raises(FileNotFoundError):
        APIManager(config_path=str(fake)).load_config()

def test_check_integration_success(monkeypatch, manager):
    class Resp:
        status_code = 200
    monkeypatch.setattr(
        'modules.api_module.requests.get',
        lambda url, timeout: Resp()
    )
    assert manager.check_integration("a") is True

def test_check_integration_fail(monkeypatch, manager):
    class Resp:
        status_code = 404
    monkeypatch.setattr(
        'modules.api_module.requests.get',
        lambda url, timeout: Resp()
    )
    assert manager.check_integration("a") is False

def test_get_best_integration_respects_priority(monkeypatch, manager):
    class Resp:
        status_code = 200
    monkeypatch.setattr(
        'modules.api_module.requests.get',
        lambda url, timeout: Resp()
    )
    best = manager.get_best_integration("any")
    assert best == "b"

def test_call_integration_success(monkeypatch, manager):
    class Resp:
        status_code = 200
        text = "OK"
    monkeypatch.setattr(
        'modules.api_module.requests.get',
        lambda url, timeout: Resp()
    )
    res = manager.call_integration("a", {"location": "Z"})
    assert res == "OK"

def test_call_integration_error_status(monkeypatch, manager):
    class Resp:
        status_code = 500
    monkeypatch.setattr(
        'modules.api_module.requests.get',
        lambda url, timeout: Resp()
    )
    res = manager.call_integration("a", {"location": "Z"})
    assert "API zwróciło błąd" in res

@pytest.mark.parametrize("name", ["notexist", None])
def test_call_integration_not_found(manager, name):
    res = manager.call_integration(name or "", {})
    assert "Nie znaleziono integracji" in res

def test_handle_api_query_success(monkeypatch, manager):
    class Resp:
        status_code = 200
        text = "OK"
    monkeypatch.setattr(
        'modules.api_module.requests.get',
        lambda url, timeout: Resp()
    )
    out = manager.handle_api_query("Q", {"location": "Z"})
    assert out == "OK"

def test_handle_api_query_none(monkeypatch, manager):
    class Resp:
        status_code = 404
    monkeypatch.setattr(
        'modules.api_module.requests.get',
        lambda url, timeout: Resp()
    )
    out = manager.handle_api_query("Q", {"location": "Z"})
    assert "Żadna integracja API" in out


def test_handle_api_query_wrapper_calls_manager(monkeypatch, manager):
    monkeypatch.setattr('modules.api_module.api_manager', manager)
    monkeypatch.setattr(manager, 'handle_api_query', lambda q, p: "RESULT")
    out = handle_api_query_wrapper("Z")
    assert out == "RESULT"

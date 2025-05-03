import pytest
from modules.deepseek_module import deep_reasoning_handler, register

@ pytest.fixture
def patch_deep(monkeypatch):
    # patch play_beep, chat_with_providers, remove_chain_of_thought
    calls = {}
    monkeypatch.setattr('modules.deepseek_module.play_beep', lambda t: calls.setdefault('beep', True))
    def fake_chat(model, messages):
        calls['chat'] = messages
        return {"message": {"content": "Result text"}}
    monkeypatch.setattr('modules.deepseek_module.chat_with_providers', fake_chat)
    monkeypatch.setattr('modules.deepseek_module.remove_chain_of_thought', lambda x: x)
    return calls

def test_deep_reasoning_success(patch_deep):
    calls = patch_deep
    out = deep_reasoning_handler("test params", conversation_history=[{'role':'user','content':'hi'}])
    assert out == "Result text"
    assert calls.get('beep')
    assert 'chat' in calls

def test_deep_reasoning_empty_param():
    out = deep_reasoning_handler("")
    assert "Podaj treść" in out

def test_deep_reasoning_exception(monkeypatch):
    monkeypatch.setattr('modules.deepseek_module.play_beep', lambda t: None)
    monkeypatch.setattr('modules.deepseek_module.chat_with_providers', lambda *args, **kwargs: (_ for _ in ()).throw(Exception("fail")))
    out = deep_reasoning_handler("params")
    assert "Błąd w deep reasoning" in out

def test_register_structure():
    reg = register()
    assert isinstance(reg, dict)
    assert 'command' in reg and 'handler' in reg and callable(reg['handler'])

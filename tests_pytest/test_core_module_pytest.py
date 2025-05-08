# pytest tests for core_module
import json
import os
import pytest
from datetime import datetime, timedelta

import modules.core_module as core_module

@pytest.fixture(autouse=True)
def storage_file(tmp_path, monkeypatch):
    """Redirect storage file to a temporary location and initialize it."""
    file = tmp_path / "core_storage.json"
    # Monkey-patch STORAGE_FILE path
    monkeypatch.setattr(core_module, "STORAGE_FILE", str(file))
    # Initialize storage
    if file.exists():
        file.unlink()
    core_module._init_storage()
    return file

def read_storage(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_set_timer_string_params(storage_file):
    msg = core_module.set_timer("10 lunch")
    assert 'Timer "lunch" ustawiony na 10 sekund.' in msg
    data = read_storage(storage_file)
    assert any(t['label'] == 'lunch' and isinstance(t['target'], str) for t in data['timers'])

def test_set_timer_dict_params(storage_file):
    msg = core_module.set_timer({'duration': 5, 'label': 'break', 'sound': 'bell'})
    assert 'Timer "break" ustawiony na 5 sekund.' in msg
    data = read_storage(storage_file)
    timers = data['timers']
    assert len(timers) == 1 and timers[0]['label'] == 'break'

@pytest.mark.parametrize("param", ["no_digit label", {}, {'action': 'set_timer'}])
def test_set_timer_invalid(storage_file, param):
    msg = core_module.set_timer(param)
    assert 'Podaj czas w sekundach' in msg

def test_view_timers_empty(storage_file):
    out = core_module.view_timers(None)
    assert out == 'Brak aktywnych timerów.'

def test_view_timers_nonempty(storage_file, monkeypatch):
    now = datetime.now()
    future = now + timedelta(seconds=30)
    data = {'timers': [{'label': 'test', 'target': future.isoformat(), 'sound': 'beep'}],
            'events': [], 'reminders': [], 'shopping_list': [], 'tasks': []}
    with open(storage_file, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    out = core_module.view_timers(None)
    assert 'test:' in out and 's pozostało' in out

def test_add_event_and_view_calendar(storage_file):
    assert core_module.view_calendar(None) == 'Brak wydarzeń.'
    when = '2025-12-31T23:59'
    msg = core_module.add_event(f"{when} NewYear")
    assert 'Dodano wydarzenie "NewYear"' in msg
    cal = core_module.view_calendar(None)
    assert '2025-12-31 23:59: NewYear' in cal

def test_add_event_invalid_format(storage_file):
    msg = core_module.add_event('invalid')
    assert 'Format: core add_event' in msg

def test_set_reminder_and_view(storage_file):
    assert core_module.view_reminders(None) == 'Brak nadchodzących przypomnień.'
    when = (datetime.now() + timedelta(days=1)).isoformat()
    msg = core_module.set_reminder(f"{when} ReminderNote")
    assert 'Ustawiono przypomnienie "ReminderNote"' in msg
    rem = core_module.view_reminders(None)
    assert 'ReminderNote' in rem

def test_set_reminder_invalid(storage_file):
    msg = core_module.set_reminder('wrongformat')
    assert 'Format: core set_reminder' in msg

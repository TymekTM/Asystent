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

# --- Shopping List Tests ---
def test_add_item_string_params(storage_file):
    assert core_module.view_list(None) == 'Lista zakupów jest pusta.'
    msg = core_module.add_item('milk')
    assert 'Dodano "milk" do listy zakupów.' in msg
    list_view = core_module.view_list(None)
    assert '- milk' in list_view

def test_add_item_dict_params(storage_file):
    msg = core_module.add_item({'item': 'bread'})
    assert 'Dodano "bread" do listy zakupów.' in msg
    data = read_storage(storage_file)
    assert 'bread' in data['shopping_list']

def test_add_item_various_dict_keys(storage_file):
    """Test different dict key names for add_item"""
    core_module.add_item({'name': 'eggs'})
    core_module.add_item({'add': 'butter'})
    core_module.add_item({'value': 'cheese'})
    data = read_storage(storage_file)
    assert 'eggs' in data['shopping_list']
    assert 'butter' in data['shopping_list']
    assert 'cheese' in data['shopping_list']

def test_add_item_empty_params(storage_file):
    msg = core_module.add_item('')
    assert 'Podaj nazwę przedmiotu do dodania.' in msg
    msg = core_module.add_item({})
    assert 'Podaj nazwę przedmiotu do dodania.' in msg

def test_remove_item_existing(storage_file):
    # Add item first
    core_module.add_item('tomato')
    msg = core_module.remove_item('tomato')
    assert 'Usunięto "tomato" z listy zakupów.' in msg
    data = read_storage(storage_file)
    assert 'tomato' not in data['shopping_list']

def test_remove_item_nonexistent(storage_file):
    msg = core_module.remove_item('nonexistent')
    assert 'Nie ma "nonexistent" na liście.' in msg

def test_remove_item_dict_params(storage_file):
    core_module.add_item('banana')
    msg = core_module.remove_item({'item': 'banana'})
    assert 'Usunięto "banana" z listy zakupów.' in msg

# --- Tasks/To-Do Tests ---
def test_add_task_string_params(storage_file):
    assert core_module.view_tasks(None) == 'Brak zadań na liście.'
    msg = core_module.add_task('finish project')
    assert 'Dodano zadanie: finish project' in msg
    tasks_view = core_module.view_tasks(None)
    assert 'finish project' in tasks_view
    assert '✗' in tasks_view  # Should show as not done

def test_add_task_dict_params(storage_file):
    msg = core_module.add_task({'task': 'call mom'})
    assert 'Dodano zadanie: call mom' in msg
    data = read_storage(storage_file)
    assert len(data['tasks']) == 1
    assert data['tasks'][0]['task'] == 'call mom'
    assert data['tasks'][0]['done'] is False

def test_add_task_various_dict_keys(storage_file):
    """Test different dict key names for add_task"""
    core_module.add_task({'add': 'buy groceries'})
    core_module.add_task({'name': 'exercise'})
    core_module.add_task({'value': 'read book'})
    data = read_storage(storage_file)
    tasks = [t['task'] for t in data['tasks']]
    assert 'buy groceries' in tasks
    assert 'exercise' in tasks
    assert 'read book' in tasks

def test_add_task_empty_params(storage_file):
    msg = core_module.add_task('')
    assert 'Podaj opis zadania.' in msg
    msg = core_module.add_task({})
    assert 'Podaj opis zadania.' in msg

def test_complete_task_valid(storage_file):
    # Add tasks first
    core_module.add_task('task one')
    core_module.add_task('task two')
    
    # Complete second task
    msg = core_module.complete_task('2')
    assert 'Oznaczono zadanie 2 jako wykonane.' in msg
    
    # Verify task is marked as done
    data = read_storage(storage_file)
    assert data['tasks'][0]['done'] is False  # first task still not done
    assert data['tasks'][1]['done'] is True   # second task is done
    
    # Check view shows correct status
    tasks_view = core_module.view_tasks(None)
    lines = tasks_view.split('\n')
    assert '✗' in lines[0]  # first task not done
    assert '✔' in lines[1]  # second task done

def test_complete_task_dict_params(storage_file):
    core_module.add_task('test task')
    msg = core_module.complete_task({'task_number': 1})
    assert 'Oznaczono zadanie 1 jako wykonane.' in msg
    
def test_complete_task_invalid_number(storage_file):
    msg = core_module.complete_task('5')  # No task #5
    assert 'Nie ma zadania o takim numerze.' in msg
    
    msg = core_module.complete_task('not_a_number')
    assert 'Podaj numer zadania' in msg

def test_remove_task_valid(storage_file):
    # Add tasks
    core_module.add_task('task to remove')
    core_module.add_task('task to keep')
    
    # Remove first task
    msg = core_module.remove_task('1')
    assert 'Usunięto zadanie: task to remove' in msg
    
    # Verify only second task remains
    data = read_storage(storage_file)
    assert len(data['tasks']) == 1
    assert data['tasks'][0]['task'] == 'task to keep'

def test_remove_task_dict_params(storage_file):
    core_module.add_task('remove me')
    msg = core_module.remove_task({'task_number': 1})
    assert 'Usunięto zadanie: remove me' in msg

def test_remove_task_invalid_number(storage_file):
    msg = core_module.remove_task('10')  # No task #10
    assert 'Nie ma zadania o takim numerze.' in msg
    
    msg = core_module.remove_task('invalid')
    assert 'Podaj numer zadania' in msg

# --- Handler Tests ---
def test_handler_with_action_dict(storage_file):
    """Test main handler with action dict format"""
    # Test timer via handler
    result = core_module.handler({'action': 'set_timer', 'duration': 30, 'label': 'test'})
    assert 'Timer "test" ustawiony na 30 sekund.' in result
    
    # Test add_item via handler
    result = core_module.handler({'action': 'add_item', 'item': 'handler_item'})
    assert 'Dodano "handler_item" do listy zakupów.' in result

def test_handler_with_single_key_dict(storage_file):
    """Test handler with single key dict (subcommand as key)"""
    # Test using alias
    result = core_module.handler({'timer': '10 test_timer'})
    assert 'Timer "test_timer" ustawiony na 10 sekund.' in result
    
    # Test using full command name
    result = core_module.handler({'add_task': 'handler task'})
    assert 'Dodano zadanie: handler task' in result

def test_handler_default_response(storage_file):
    """Test handler returns help text for unknown commands"""
    result = core_module.handler('unknown_command')
    assert 'Użyj sub-komend:' in result
    assert 'set_timer' in result
    assert 'add_task' in result

def test_handler_unknown_action(storage_file):
    """Test handler with unknown action in dict"""
    result = core_module.handler({'action': 'unknown_action'})
    assert 'Nieznana subkomenda: unknown_action' in result

# --- Integration Tests ---
def test_get_reminders_for_today(storage_file):
    """Test helper function for daily briefing"""
    today = datetime.now()
    today_str = today.replace(hour=10, minute=0).isoformat()
    tomorrow_str = (today + timedelta(days=1)).isoformat()
    
    # Add reminders for today and tomorrow
    core_module.set_reminder(f'{today_str} Today reminder')
    core_module.set_reminder(f'{tomorrow_str} Tomorrow reminder')
    
    # Get today's reminders
    today_reminders = core_module.get_reminders_for_today()
    
    assert len(today_reminders) == 1
    assert today_reminders[0]['title'] == 'Today reminder'
    assert today_reminders[0]['time'] == today_str

def test_storage_persistence_across_operations(storage_file):
    """Test that storage persists correctly across multiple operations"""
    # Add various items
    core_module.set_timer('60 persistent_timer')
    core_module.add_event('2025-12-25T10:00 Christmas')
    core_module.add_item('persistent_item')
    core_module.add_task('persistent_task')
    
    # Verify all items are stored
    data = read_storage(storage_file)
    assert len(data['timers']) == 1
    assert len(data['events']) == 1
    assert len(data['shopping_list']) == 1
    assert len(data['tasks']) == 1
    
    # Modify and verify persistence
    core_module.complete_task('1')
    core_module.remove_item('persistent_item')
    
    data = read_storage(storage_file)
    assert data['tasks'][0]['done'] is True
    assert len(data['shopping_list']) == 0

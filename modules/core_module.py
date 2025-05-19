import logging
import json
import os
import sys  # Added import for sys
import threading
from datetime import datetime, timedelta

from audio_modules.beep_sounds import play_beep

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Determine the appropriate directory for persistent application data
APP_NAME = "Asystent"
user_data_dir = ""

# Try to establish a user-specific data directory
try:
    if os.name == 'nt':  # Windows
        # Use APPDATA, fallback to user's home directory
        base_dir = os.getenv('APPDATA')
        if not base_dir:
            base_dir = os.path.expanduser("~")
        user_data_dir = os.path.join(base_dir, APP_NAME)
    else:  # macOS, Linux
        user_data_dir = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")

    # Create the directory if it doesn't exist
    os.makedirs(user_data_dir, exist_ok=True)
    logger.info(f"Application data will be stored in: {user_data_dir}")

except Exception as e:
    logger.error(f"Could not create/access user-specific data directory: {e}. Falling back.")
    # Fallback: try to create a data directory in the current working directory
    # This is not ideal, especially for bundled apps, but better than failing outright.
    fallback_dir_name = f"{APP_NAME}_data_fallback"
    try:
        # Try to use the directory where the script/executable is located if possible
        if getattr(sys, 'frozen', False):  # If application is frozen (e.g. PyInstaller bundle)
            # sys.executable is the path to the frozen executable
            app_run_dir = os.path.dirname(sys.executable) # Use executable's directory
        else:  # If running as a script
            # __file__ is the path to the script
            app_run_dir = os.path.dirname(os.path.abspath(__file__)) # Use script's directory

        user_data_dir = os.path.join(app_run_dir, fallback_dir_name)
        os.makedirs(user_data_dir, exist_ok=True)
        logger.warning(f"Using fallback data directory: {user_data_dir}")
    except Exception as e2:
        logger.critical(f"Failed to create even fallback data directory {user_data_dir}: {e2}. Data storage will likely fail.")
        # If even this fails, set user_data_dir to something to prevent crash on join, though writes will fail
        user_data_dir = "."

STORAGE_FILE = os.path.join(user_data_dir, 'core_storage.json')
logger.info(f"Using storage file: {STORAGE_FILE}")


# initialize storage
def _init_storage():
    if not os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'w') as f:
                json.dump({
                    'timers': [],
                    'events': [],
                    'reminders': [],
                    'shopping_list': [],
                    'tasks': []
                }, f)
            logger.info(f"Initialized new storage file at: {STORAGE_FILE}")
        except Exception as e:
            logger.error(f"Failed to create or write initial storage file at {STORAGE_FILE}: {e}")
            # This is a critical error; the application might not function correctly.
            # Consider raising an exception or implementing more specific error handling.


_init_storage()


# --- Background timer polling thread ---
def _timer_polling_loop():
    import time
    while True:
        try:
            data = _load_storage()
            now = datetime.now()
            changed = False
            remaining = []
            for t in data['timers']:
                target = datetime.fromisoformat(t['target'])
                if target <= now:
                    logger.info(f"Timer finished: {t['label']}")
                    try:
                        play_beep(t.get('sound', 'beep'))
                    except Exception as e:
                        logger.error(f"play_beep failed in polling: {e}")
                    changed = True
                else:
                    remaining.append(t)
            if changed:
                data['timers'] = remaining
                _save_storage(data)
        except Exception as e:
            logger.error(f"Timer polling error: {e}")
        time.sleep(1)


# Start polling thread once on import (after all functions are defined)
def _start_timer_polling_thread():
    t = threading.Thread(target=_timer_polling_loop, daemon=True)
    t.start()


def _load_storage():
    with open(STORAGE_FILE, 'r') as f:
        return json.load(f)


def _save_storage(data):
    with open(STORAGE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# --- Timer callback ---
def _timer_finished(label: str):
    logger.info(f"Timer finished: {label}")
    try:
        play_beep("beep")
    except Exception as e:
        logger.error(f"play_beep failed in _timer_finished: {e}")


# --- Timers ---
def set_timer(params) -> str:
    '''Set a timer asynchronously: core set_timer <seconds> <label?>'''
    # Normalize params if dict (AI sometimes passes {"action":..., "duration":..., "label":...})
    if isinstance(params, dict):
        seconds = None
        label = 'timer'
        # Try common keys
        if 'duration' in params:
            seconds = params['duration']
        elif 'seconds' in params:
            seconds = params['seconds']
        elif 'time' in params:
            seconds = params['time']
        if 'label' in params:
            label = str(params['label'])
        elif 'name' in params:
            label = str(params['name'])
        elif 'action' in params and isinstance(params['action'], str) and params['action'] != 'set_timer':
            label = params['action']
        if seconds is None:
            return 'Podaj czas w sekundach, np. "core set_timer 60 przerwa"'
        try:
            seconds = int(seconds)
        except Exception:
            return 'Podaj czas w sekundach, np. "core set_timer 60 przerwa"'
    elif isinstance(params, int):
        seconds = params
        label = 'timer'
    else:
        parts = str(params).split()
        if not parts or not parts[0].isdigit():
            return 'Podaj czas w sekundach, np. "core set_timer 60 przerwa"'
        seconds = int(parts[0])
        label = ' '.join(parts[1:]) if len(parts) > 1 else 'timer'
    # Allow user to specify sound type (default: beep)
    sound = None
    if isinstance(params, dict):
        sound = params.get('sound') or params.get('beep') or params.get('audio')
    if not sound:
        sound = 'beep'
    target = datetime.now() + timedelta(seconds=seconds)
    data = _load_storage()
    data['timers'].append({'label': label, 'target': target.isoformat(), 'sound': sound})
    _save_storage(data)
    logger.info(f'Set timer: {label} for {seconds} seconds (sound: {sound})')
    # Schedule immediate timer beep in background (fallback to polling)
    try:
        timer_thread = threading.Timer(seconds, _timer_finished, args=(label,))
        timer_thread.daemon = True
        timer_thread.start()
        logger.debug(f'Scheduled Timer thread for label: {label} in {seconds}s')
    except Exception as e:
        logger.error(f'Error scheduling timer thread: {e}', exc_info=True)
    return f'Timer "{label}" ustawiony na {seconds} sekund.'


def view_timers(params) -> str:
    data = _load_storage()
    now = datetime.now()
    active = []
    for t in data['timers']:
        target = datetime.fromisoformat(t['target'])
        if target > now:
            rem = int((target - now).total_seconds())
            active.append(f"{t['label']}: {rem}s pozostało")
    return '\n'.join(active) if active else 'Brak aktywnych timerów.'


# --- Calendar Events ---
def add_event(params: str) -> str:
    try:
        when_str, desc = params.split(' ', 1)
        when = datetime.fromisoformat(when_str)
    except Exception:
        return 'Format: core add_event 2025-05-10T14:00 Spotkanie'
    data = _load_storage()
    data['events'].append({'time': when.isoformat(), 'desc': desc})
    _save_storage(data)
    logger.info(f'Added event: {when} - {desc}')
    return f'Dodano wydarzenie "{desc}" na {when}.'


def view_calendar(params) -> str:
    data = _load_storage()
    if not data['events']:
        return 'Brak wydarzeń.'
    lines = []
    for e in sorted(data['events'], key=lambda x: x['time']):
        dt = datetime.fromisoformat(e['time'])
        lines.append(f"{dt.strftime('%Y-%m-%d %H:%M')}: {e['desc']}")
    return '\n'.join(lines)


# --- Reminders ---
def set_reminder(params: str, conversation_history=None) -> str:
    try:
        when_str, note = params.split(' ', 1)
        when = datetime.fromisoformat(when_str)
    except Exception:
        return 'Format: core set_reminder 2025-05-10T08:00 Kup_mleko'
    data = _load_storage()
    data['reminders'].append({'time': when.isoformat(), 'note': note})
    _save_storage(data)
    logger.info(f'Set reminder: {note} at {when}')
    return f'Ustawiono przypomnienie "{note}" na {when}.'


def view_reminders(params) -> str:
    data = _load_storage()
    now = datetime.now()
    upcoming = [r for r in data['reminders'] if datetime.fromisoformat(r['time']) > now]
    if not upcoming:
        return 'Brak nadchodzących przypomnień.'
    lines = []
    for r in sorted(upcoming, key=lambda x: x['time']):
        dt = datetime.fromisoformat(r['time'])
        lines.append(f"{dt.strftime('%Y-%m-%d %H:%M')}: {r['note']}")
    return '\n'.join(lines)


# --- Shopping List ---
def add_item(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        # Try common keys
        item = params.get('item') or params.get('name') or params.get('add') or params.get('value')
        if not item:
            # If only one key, use its value
            if len(params) == 1:
                item = list(params.values())[0]
        if not item:
            return 'Podaj nazwę przedmiotu do dodania.'
        item = str(item).strip()
    else:
        item = str(params).strip()
    if not item:
        return 'Podaj nazwę przedmiotu do dodania.'
    data = _load_storage()
    data['shopping_list'].append(item)
    _save_storage(data)
    logger.info(f'Added item to shopping list: {item}')
    return f'Dodano "{item}" do listy zakupów.'


def view_list(params) -> str:
    data = _load_storage()
    if not data['shopping_list']:
        return 'Lista zakupów jest pusta.'
    return '\n'.join(f"- {i}" for i in data['shopping_list'])


def remove_item(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        item = params.get('item') or params.get('name') or params.get('remove') or params.get('value')
        if not item:
            # If only one key, use its value
            if len(params) == 1:
                item = list(params.values())[0]
        if not item:
            return 'Podaj nazwę przedmiotu do usunięcia.'
        item = str(item).strip()
    else:
        item = str(params).strip()
    data = _load_storage()
    if item in data['shopping_list']:
        data['shopping_list'].remove(item)
        _save_storage(data)
        return f'Usunięto "{item}" z listy zakupów.'
    return f'Nie ma "{item}" na liście.'


# --- To-Do Tasks ---
def add_task(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        task = params.get('task') or params.get('add') or params.get('name') or params.get('value')
        if not task:
            if len(params) == 1:
                task = list(params.values())[0]
        if not task:
            return 'Podaj opis zadania.'
        task = str(task).strip()
    else:
        task = str(params).strip()
    if not task:
        return 'Podaj opis zadania.'
    data = _load_storage()
    data['tasks'].append({'task': task, 'done': False})
    _save_storage(data)
    logger.info(f'Added task: {task}')
    return f'Dodano zadanie: {task}'


def view_tasks(params) -> str:
    data = _load_storage()
    if not data['tasks']:
        return 'Brak zadań na liście.'
    lines = []
    for idx, t in enumerate(data['tasks'], 1):
        status = '✔' if t['done'] else '✗'
        lines.append(f"{idx}. [{status}] {t['task']}")
    return '\n'.join(lines)


def complete_task(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        idx = params.get('task_number') or params.get('index') or params.get('done') or params.get('id')
        if idx is None:
            if len(params) == 1:
                idx = list(params.values())[0]
        if idx is None:
            return 'Podaj numer zadania, np. core complete_task 2'
        try:
            idx = int(idx) - 1
        except Exception:
            return 'Podaj numer zadania, np. core complete_task 2'
    else:
        if not str(params).isdigit():
            return 'Podaj numer zadania, np. core complete_task 2'
        idx = int(params) - 1
    data = _load_storage()
    if idx < 0 or idx >= len(data['tasks']):
        return 'Nie ma zadania o takim numerze.'
    data['tasks'][idx]['done'] = True
    _save_storage(data)
    logger.info(f'Marked task as done: {data["tasks"][idx]["task"]}')
    return f'Oznaczono zadanie {idx+1} jako wykonane.'


def remove_task(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        idx = params.get('task_number') or params.get('index') or params.get('remove') or params.get('id')
        if idx is None:
            if len(params) == 1:
                idx = list(params.values())[0]
        if idx is None:
            return 'Podaj numer zadania, np. core remove_task 3'
        try:
            idx = int(idx) - 1
        except Exception:
            return 'Podaj numer zadania, np. core remove_task 3'
    else:
        if not str(params).isdigit():
            return 'Podaj numer zadania, np. core remove_task 3'
        idx = int(params) - 1
    data = _load_storage()
    if idx < 0 or idx >= len(data['tasks']):
        return 'Nie ma zadania o takim numerze.'
    removed = data['tasks'].pop(idx)
    _save_storage(data)
    logger.info(f'Removed task: {removed["task"]}')
    return f'Usunięto zadanie: {removed["task"]}'

# Main handler
def handler(params: str = '', conversation_history: list = None) -> str:
    reg = register()
    # 1. Obsługa: params jako dict z 'action' (oryginalna logika)
    if isinstance(params, dict) and 'action' in params:
        action = params['action']
        sub_params = dict(params)
        del sub_params['action']
        if len(sub_params) == 1:
            sub_params = list(sub_params.values())[0]
        sub = reg['sub_commands'].get(action)
        if not sub:
            for name, sc in reg['sub_commands'].items():
                if action in sc.get('aliases', []):
                    sub = sc
                    break
        if sub:
            return sub['function'](sub_params)
        else:
            return f'Nieznana subkomenda: {action}'

    # 2. Obsługa: params jako dict z jednym kluczem będącym subkomendą lub aliasem
    if isinstance(params, dict) and len(params) == 1:
        key = list(params.keys())[0]
        value = params[key]
        sub = reg['sub_commands'].get(key)
        if not sub:
            # Spróbuj aliasów
            for name, sc in reg['sub_commands'].items():
                if key in sc.get('aliases', []):
                    sub = sc
                    break
        if sub:
            return sub['function'](value)

    return ('Użyj sub-komend: set_timer, view_timers, add_event, view_calendar, '
            'set_reminder, view_reminders, add_item, view_list, remove_item, '
            'add_task, view_tasks, complete_task, remove_task')

# Registration
def register():
    """
    Register core plugin with sub-commands for timers, events, reminders,
    shopping list, and tasks. Expands aliases for sub-command lookup.
    """
    info = {
        'command': 'core',
        'description': 'Timers, calendar events, reminders, shopping list, to-do tasks',
        'handler': handler,
        'sub_commands': {
            'set_timer':     {'function': set_timer,       'description': 'Ustaw timer',                'aliases': ['timer'],     'params_desc': '<seconds>'},
            'view_timers':   {'function': view_timers,     'description': 'Pokaż aktywne timery',     'aliases': ['timers'],    'params_desc': ''},
            'add_event':     {'function': add_event,       'description': 'Dodaj wydarzenie',          'aliases': ['event'],     'params_desc': '<ISOdatetime> <desc>'},
            'view_calendar': {'function': view_calendar,   'description': 'Pokaż kalendarz',          'aliases': ['calendar'],  'params_desc': ''},
            'set_reminder':  {'function': set_reminder,    'description': 'Ustaw przypomnienie',       'aliases': ['reminder'],  'params_desc': '<ISOdatetime> <note>'},
            'view_reminders':{'function': view_reminders,  'description': 'Pokaż przypomnienia',       'aliases': ['reminders'], 'params_desc': ''},
            'add_item':      {'function': add_item,        'description': 'Dodaj do listy zakupów',    'aliases': ['item'],      'params_desc': '<item>'},
            'view_list':     {'function': view_list,       'description': 'Pokaż listę zakupów',       'aliases': ['list'],      'params_desc': ''},
            'remove_item':   {'function': remove_item,     'description': 'Usuń z listy zakupów',      'aliases': ['remove'],    'params_desc': '<item>'},
            'add_task':      {'function': add_task,        'description': 'Dodaj zadanie do to-do',    'aliases': ['task'],      'params_desc': '<task>'},
            'view_tasks':    {'function': view_tasks,      'description': 'Pokaż listę zadań',         'aliases': ['tasks'],     'params_desc': ''},
            'complete_task': {'function': complete_task,   'description': 'Oznacz zadanie jako wykonane','aliases': ['done'],     'params_desc': '<task_number>'},
            'remove_task':   {'function': remove_task,     'description': 'Usuń zadanie',             'aliases': ['rm_task'],   'params_desc': '<task_number>'}
        }
    }
    # Expand sub-command aliases for lookup
    subs = info['sub_commands']
    for name, sc in list(subs.items()):
        for alias in sc.get('aliases', []):
            # do not override if alias equals primary name
            if alias not in subs:
                subs[alias] = sc
    return info
    
# Start polling thread when module is loaded
_start_timer_polling_thread()

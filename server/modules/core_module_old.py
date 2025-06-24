import asyncio
import json
import logging
import os
import sys  # Added import for sys
from datetime import datetime, timedelta

# Use aiofiles for async file operations
try:
    import aiofiles
except ImportError:
    # Fallback for environments without aiofiles
    import aiofiles

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Determine the appropriate directory for persistent application data
APP_NAME = "Asystent_Server"
user_data_dir = ""

# Try to establish a user-specific data directory
try:
    if os.name == "nt":  # Windows
        # Use APPDATA, fallback to user's home directory
        base_dir = os.getenv("APPDATA")
        if not base_dir:
            base_dir = os.path.expanduser("~")
        user_data_dir = os.path.join(base_dir, APP_NAME)
    else:  # macOS, Linux
        user_data_dir = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")

    # Create the directory if it doesn't exist
    os.makedirs(user_data_dir, exist_ok=True)
    logger.info(f"Application data will be stored in: {user_data_dir}")

except Exception as e:
    logger.error(
        f"Could not create/access user-specific data directory: {e}. Falling back."
    )
    # Fallback: try to create a data directory in the current working directory
    # This is not ideal, especially for bundled apps, but better than failing outright.
    fallback_dir_name = f"{APP_NAME}_data_fallback"
    try:
        # Try to use the directory where the script/executable is located if possible
        if getattr(
            sys, "frozen", False
        ):  # If application is frozen (e.g. PyInstaller bundle)
            # sys.executable is the path to the frozen executable
            app_run_dir = os.path.dirname(sys.executable)  # Use executable's directory
        else:  # If running as a script
            # __file__ is the path to the script
            app_run_dir = os.path.dirname(
                os.path.abspath(__file__)
            )  # Use script's directory

        user_data_dir = os.path.join(app_run_dir, fallback_dir_name)
        os.makedirs(user_data_dir, exist_ok=True)
        logger.warning(f"Using fallback data directory: {user_data_dir}")
    except Exception as e2:
        logger.critical(
            f"Failed to create even fallback data directory {user_data_dir}: {e2}. Data storage will likely fail."
        )
        # If even this fails, set user_data_dir to something to prevent crash on join, though writes will fail
        user_data_dir = "."

STORAGE_FILE = os.path.join(user_data_dir, "core_storage.json")
logger.info(f"Using storage file: {STORAGE_FILE}")


# Initialize storage
async def _init_storage():
    """Initialize storage file with default structure if it doesn't exist."""
    if not os.path.exists(STORAGE_FILE):
        try:
            async with aiofiles.open(STORAGE_FILE, "w") as f:
                await f.write(
                    json.dumps(
                        {
                            "timers": [],
                            "events": [],
                            "reminders": [],
                            "shopping_list": [],
                            "tasks": [],
                            "lists": {},
                        },
                        indent=2,
                    )
                )
            logger.info(f"Initialized new storage file at: {STORAGE_FILE}")
        except Exception as e:
            logger.error(
                f"Failed to create or write initial storage file at {STORAGE_FILE}: {e}"
            )
            # This is a critical error; the application might not function correctly.
            raise


# Global storage for active timers (in-memory)
_active_timers = {}
_timer_polling_task = None


async def _ensure_storage_initialized():
    """Ensure storage is initialized before use."""
    if not os.path.exists(STORAGE_FILE):
        await _init_storage()


# --- Background timer polling with asyncio ---
async def _timer_polling_loop():
    """Async timer polling loop - replaces threading approach."""
    while True:
        try:
            data = await _load_storage()
            now = datetime.now()
            changed = False
            remaining = []
            for t in data["timers"]:
                target = datetime.fromisoformat(t["target"])
                if target <= now:
                    logger.info(f"Timer finished: {t['label']}")
                    # Server-side: Log timer completion instead of playing beep
                    # The client will be notified and can play the sound
                    try:
                        # TODO: Send notification to connected clients
                        logger.warning(
                            f"⏰ TIMER FINISHED: {t['label']} - Sound: {t.get('sound', 'beep')}"
                        )
                        await _timer_finished(t["label"])
                    except Exception as e:
                        logger.error(f"Timer notification failed: {e}")
                    changed = True
                else:
                    remaining.append(t)
            if changed:
                data["timers"] = remaining
                await _save_storage(data)
        except Exception as e:
            logger.error(f"Timer polling error: {e}")

        # Use async sleep instead of time.sleep
        await asyncio.sleep(1)


# Start polling task once on import (after all functions are defined)
def _start_timer_polling_task():
    """Start the async timer polling task."""
    global _timer_polling_task
    if _timer_polling_task is None:
        _timer_polling_task = asyncio.create_task(_timer_polling_loop())


async def _load_storage():
    """Load storage data from file asynchronously."""
    try:
        async with aiofiles.open(STORAGE_FILE, "r") as f:
            content = await f.read()
            return json.loads(content)
    except FileNotFoundError:
        # Initialize storage if file doesn't exist
        await _init_storage()
        return {
            "timers": [],
            "events": [],
            "reminders": [],
            "shopping_list": [],
            "tasks": [],
            "lists": {},
        }
    except Exception as e:
        logger.error(f"Error loading storage: {e}")
        raise


async def _save_storage(data):
    """Save storage data to file asynchronously."""
    try:
        async with aiofiles.open(STORAGE_FILE, "w") as f:
            await f.write(json.dumps(data, indent=2))
    except Exception as e:
        logger.error(f"Error saving storage: {e}")
        raise


# Timer callback
async def _timer_finished(label: str):
    """Async timer callback."""
    logger.info(f"Timer finished: {label}")
    # Server-side: Log completion instead of playing sound
    logger.warning(f"⏰ TIMER FINISHED: {label}")


# --- Timers ---
async def set_timer(params) -> str:
    """Set a timer asynchronously."""
    try:
        # Parse timer parameters
        seconds = 0
        label = "timer"

        if isinstance(params, dict):
            # Handle dict parameters
            duration = (
                params.get("duration") or params.get("seconds") or params.get("time")
            )
            label = params.get("label") or params.get("name") or "timer"

            if duration is None:
                return "Duration parameter is required"

            # Parse duration (support both numbers and strings like "5m", "30s")
            if isinstance(duration, str):
                if duration.endswith("s"):
                    seconds = int(duration[:-1])
                elif duration.endswith("m"):
                    seconds = int(duration[:-1]) * 60
                elif duration.endswith("h"):
                    seconds = int(duration[:-1]) * 3600
                else:
                    seconds = int(duration)
            else:
                seconds = int(duration)

        elif isinstance(params, str):
            # Handle string parameters
            parts = params.strip().split()
            if not parts:
                return 'Provide duration, e.g. "60" for 60 seconds'

            duration_str = parts[0]
            label = " ".join(parts[1:]) if len(parts) > 1 else "timer"

            # Parse duration
            if duration_str.endswith("s"):
                seconds = int(duration_str[:-1])
            elif duration_str.endswith("m"):
                seconds = int(duration_str[:-1]) * 60
            elif duration_str.endswith("h"):
                seconds = int(duration_str[:-1]) * 3600
            else:
                seconds = int(duration_str)
        else:
            return "Invalid parameters format"

        if seconds <= 0:
            return "Duration must be positive"

        # Create timer
        target = datetime.now() + timedelta(seconds=seconds)
        data = await _load_storage()

        timer_entry = {
            "label": str(label),
            "target": target.isoformat(),
            "sound": "beep",
            "created": datetime.now().isoformat(),
        }

        data["timers"].append(timer_entry)
        await _save_storage(data)

        logger.info(f"Set timer: {label} for {seconds} seconds")
        return f'Timer "{label}" set for {seconds} seconds.'

    except ValueError as e:
        return f"Invalid duration format: {e}"
    except Exception as e:
        logger.error(f"Error setting timer: {e}")
        return f"Error setting timer: {e}"


async def view_timers(params) -> str:
    """View active timers."""
    try:
        data = await _load_storage()
        now = datetime.now()
        active = []

        for t in data["timers"]:
            target = datetime.fromisoformat(t["target"])
            if target > now:
                remaining = target - now
                remaining_seconds = int(remaining.total_seconds())
                active.append(f"{t['label']}: {remaining_seconds}s remaining")

        return "\n".join(active) if active else "No active timers."

    except Exception as e:
        logger.error(f"Error viewing timers: {e}")
        return f"Error viewing timers: {e}"


# --- Calendar Events ---
async def add_event(params: str) -> str:
    """Add a calendar event."""
    try:
        if isinstance(params, dict):
            title = params.get("title", "")
            date = params.get("date", "")
            time = params.get("time", "")

            if not title or not date:
                return "Title and date parameters are required"

            # Combine date and time
            if time:
                when_str = f"{date}T{time}"
            else:
                when_str = f"{date}T12:00"  # Default to noon

            when = datetime.fromisoformat(when_str)
            desc = title

        else:
            # Parse string format: "2025-05-10T14:00 Meeting description"
            parts = str(params).split(" ", 1)
            if len(parts) < 2:
                return "Format: add_event 2025-05-10T14:00 Meeting description"

            when_str, desc = parts
            when = datetime.fromisoformat(when_str)

        data = await _load_storage()
        event_entry = {
            "time": when.isoformat(),
            "desc": desc,
            "created": datetime.now().isoformat(),
        }

        data["events"].append(event_entry)
        await _save_storage(data)

        logger.info(f"Added event: {desc} at {when_str}")
        return f'Event "{desc}" added for {when.strftime("%Y-%m-%d %H:%M")}'

    except ValueError as e:
        return f"Invalid date/time format: {e}"
    except Exception as e:
        logger.error(f"Error adding event: {e}")
        return f"Error adding event: {e}"
    _save_storage(data)
    logger.info(f"Added event: {when} - {desc}")
    return f'Dodano wydarzenie "{desc}" na {when}.'


def view_calendar(params) -> str:
    data = _load_storage()
    if not data["events"]:
        return "Brak wydarzeń."
    lines = []
    for e in sorted(data["events"], key=lambda x: x["time"]):
        dt = datetime.fromisoformat(e["time"])
        lines.append(f"{dt.strftime('%Y-%m-%d %H:%M')}: {e['desc']}")
    return "\n".join(lines)


# --- Reminders ---
def set_reminder(params: str, conversation_history=None) -> str:
    try:
        when_str, note = params.split(" ", 1)
        when = datetime.fromisoformat(when_str)
    except Exception:
        return "Format: core set_reminder 2025-05-10T08:00 Kup_mleko"
    data = _load_storage()
    data["reminders"].append({"time": when.isoformat(), "note": note})
    _save_storage(data)
    logger.info(f"Set reminder: {note} at {when}")
    return f'Ustawiono przypomnienie "{note}" na {when}.'


def view_reminders(params) -> str:
    data = _load_storage()
    now = datetime.now()
    upcoming = [r for r in data["reminders"] if datetime.fromisoformat(r["time"]) > now]
    if not upcoming:
        return "Brak nadchodzących przypomnień."
    lines = []
    for r in sorted(upcoming, key=lambda x: x["time"]):
        dt = datetime.fromisoformat(r["time"])
        lines.append(f"{dt.strftime('%Y-%m-%d %H:%M')}: {r['note']}")
    return "\n".join(lines)


# --- Shopping List ---
def add_item(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        # Try common keys
        item = (
            params.get("item")
            or params.get("name")
            or params.get("add")
            or params.get("value")
        )
        if not item:
            # If only one key, use its value
            if len(params) == 1:
                item = list(params.values())[0]
        if not item:
            return "Podaj nazwę przedmiotu do dodania."
        item = str(item).strip()
    else:
        item = str(params).strip()
    if not item:
        return "Podaj nazwę przedmiotu do dodania."
    data = _load_storage()
    data["shopping_list"].append(item)
    _save_storage(data)
    logger.info(f"Added item to shopping list: {item}")
    return f'Dodano "{item}" do listy zakupów.'


def view_list(params) -> str:
    data = _load_storage()
    if not data["shopping_list"]:
        return "Lista zakupów jest pusta."
    return "\n".join(f"- {i}" for i in data["shopping_list"])


def remove_item(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        item = (
            params.get("item")
            or params.get("name")
            or params.get("remove")
            or params.get("value")
        )
        if not item:
            # If only one key, use its value
            if len(params) == 1:
                item = list(params.values())[0]
        if not item:
            return "Podaj nazwę przedmiotu do usunięcia."
        item = str(item).strip()
    else:
        item = str(params).strip()
    data = _load_storage()
    if item in data["shopping_list"]:
        data["shopping_list"].remove(item)
        _save_storage(data)
        return f'Usunięto "{item}" z listy zakupów.'
    return f'Nie ma "{item}" na liście.'


# --- To-Do Tasks ---
def add_task(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        task = (
            params.get("task")
            or params.get("add")
            or params.get("name")
            or params.get("value")
        )
        if not task:
            if len(params) == 1:
                task = list(params.values())[0]
        if not task:
            return "Podaj opis zadania."
        task = str(task).strip()
    else:
        task = str(params).strip()
    if not task:
        return "Podaj opis zadania."
    data = _load_storage()
    data["tasks"].append({"task": task, "done": False})
    _save_storage(data)
    logger.info(f"Added task: {task}")
    return f"Dodano zadanie: {task}"


def view_tasks(params) -> str:
    data = _load_storage()
    if not data["tasks"]:
        return "Brak zadań na liście."
    lines = []
    for idx, t in enumerate(data["tasks"], 1):
        status = "✔" if t["done"] else "✗"
        lines.append(f"{idx}. [{status}] {t['task']}")
    return "\n".join(lines)


def complete_task(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        idx = (
            params.get("task_number")
            or params.get("index")
            or params.get("done")
            or params.get("id")
        )
        if idx is None:
            if len(params) == 1:
                idx = list(params.values())[0]
        if idx is None:
            return "Podaj numer zadania, np. core complete_task 2"
        try:
            idx = int(idx) - 1
        except Exception:
            return "Podaj numer zadania, np. core complete_task 2"
    else:
        if not str(params).isdigit():
            return "Podaj numer zadania, np. core complete_task 2"
        idx = int(params) - 1
    data = _load_storage()
    if idx < 0 or idx >= len(data["tasks"]):
        return "Nie ma zadania o takim numerze."
    data["tasks"][idx]["done"] = True
    _save_storage(data)
    logger.info(f'Marked task as done: {data["tasks"][idx]["task"]}')
    return f"Oznaczono zadanie {idx+1} jako wykonane."


def remove_task(params: str) -> str:
    # Accept dict or string
    if isinstance(params, dict):
        idx = (
            params.get("task_number")
            or params.get("index")
            or params.get("remove")
            or params.get("id")
        )
        if idx is None:
            if len(params) == 1:
                idx = list(params.values())[0]
        if idx is None:
            return "Podaj numer zadania, np. core remove_task 3"
        try:
            idx = int(idx) - 1
        except Exception:
            return "Podaj numer zadania, np. core remove_task 3"
    else:
        if not str(params).isdigit():
            return "Podaj numer zadania, np. core remove_task 3"
        idx = int(params) - 1
    data = _load_storage()
    if idx < 0 or idx >= len(data["tasks"]):
        return "Nie ma zadania o takim numerze."
    removed = data["tasks"].pop(idx)
    _save_storage(data)
    logger.info(f'Removed task: {removed["task"]}')
    return f'Usunięto zadanie: {removed["task"]}'


# Main handler
def handler(params: str = "", conversation_history: list = None) -> str:
    reg = register()
    # 1. Obsługa: params jako dict z 'action' (oryginalna logika)
    if isinstance(params, dict) and "action" in params:
        action = params["action"]
        sub_params = dict(params)
        del sub_params["action"]
        if len(sub_params) == 1:
            sub_params = list(sub_params.values())[0]
        sub = reg["sub_commands"].get(action)
        if not sub:
            for name, sc in reg["sub_commands"].items():
                if action in sc.get("aliases", []):
                    sub = sc
                    break
        if sub:
            return sub["function"](sub_params)
        else:
            return f"Nieznana subkomenda: {action}"

    # 2. Obsługa: params jako dict z jednym kluczem będącym subkomendą lub aliasem
    if isinstance(params, dict) and len(params) == 1:
        key = list(params.keys())[0]
        value = params[key]
        sub = reg["sub_commands"].get(key)
        if not sub:
            # Spróbuj aliasów
            for name, sc in reg["sub_commands"].items():
                if key in sc.get("aliases", []):
                    sub = sc
                    break
        if sub:
            return sub["function"](value)

    return (
        "Użyj sub-komend: set_timer, view_timers, add_event, view_calendar, "
        "set_reminder, view_reminders, add_item, view_list, remove_item, "
        "add_task, view_tasks, complete_task, remove_task"
    )


# Registration
def register():
    """Register core plugin with sub-commands for timers, events, reminders, shopping
    list, and tasks.

    Expands aliases for sub-command lookup.
    """
    info = {
        "command": "core",
        "description": "Timers, calendar events, reminders, shopping list, to-do tasks",
        "handler": handler,
        "sub_commands": {
            "set_timer": {
                "function": set_timer,
                "description": "Ustaw timer",
                "aliases": ["timer"],
                "params_desc": "<seconds>",
            },
            "view_timers": {
                "function": view_timers,
                "description": "Pokaż aktywne timery",
                "aliases": ["timers"],
                "params_desc": "",
            },
            "add_event": {
                "function": add_event,
                "description": "Dodaj wydarzenie",
                "aliases": ["event"],
                "params_desc": "<ISOdatetime> <desc>",
            },
            "view_calendar": {
                "function": view_calendar,
                "description": "Pokaż kalendarz",
                "aliases": ["calendar"],
                "params_desc": "",
            },
            "set_reminder": {
                "function": set_reminder,
                "description": "Ustaw przypomnienie",
                "aliases": ["reminder"],
                "params_desc": "<ISOdatetime> <note>",
            },
            "view_reminders": {
                "function": view_reminders,
                "description": "Pokaż przypomnienia",
                "aliases": ["reminders"],
                "params_desc": "",
            },
            "add_item": {
                "function": add_item,
                "description": "Dodaj do listy zakupów",
                "aliases": ["item"],
                "params_desc": "<item>",
            },
            "view_list": {
                "function": view_list,
                "description": "Pokaż listę zakupów",
                "aliases": ["list"],
                "params_desc": "",
            },
            "remove_item": {
                "function": remove_item,
                "description": "Usuń z listy zakupów",
                "aliases": ["remove"],
                "params_desc": "<item>",
            },
            "add_task": {
                "function": add_task,
                "description": "Dodaj zadanie do to-do",
                "aliases": ["task"],
                "params_desc": "<task>",
            },
            "view_tasks": {
                "function": view_tasks,
                "description": "Pokaż listę zadań",
                "aliases": ["tasks"],
                "params_desc": "",
            },
            "complete_task": {
                "function": complete_task,
                "description": "Oznacz zadanie jako wykonane",
                "aliases": ["done"],
                "params_desc": "<task_number>",
            },
            "remove_task": {
                "function": remove_task,
                "description": "Usuń zadanie",
                "aliases": ["rm_task"],
                "params_desc": "<task_number>",
            },
        },
    }
    # Expand sub-command aliases for lookup
    subs = info["sub_commands"]
    for name, sc in list(subs.items()):
        for alias in sc.get("aliases", []):
            # do not override if alias equals primary name
            if alias not in subs:
                subs[alias] = sc
    return info


# Start polling thread when module is loaded
_start_timer_polling_thread()


def get_reminders_for_today():
    """Get reminders for today only - helper function for daily briefing."""
    data = _load_storage()
    today = datetime.now().date()
    today_reminders = []

    for reminder in data["reminders"]:
        reminder_date = datetime.fromisoformat(reminder["time"]).date()
        if reminder_date == today:
            today_reminders.append(
                {"title": reminder["note"], "time": reminder["time"]}
            )

    return today_reminders


# Plugin metadata (required by plugin manager)
PLUGIN_NAME = "core_module"
PLUGIN_DESCRIPTION = (
    "Core functionality: timers, calendar, reminders, shopping list, to-do tasks"
)
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "GAJA Assistant"
PLUGIN_DEPENDENCIES = []


def get_current_time():
    """Get current date and time."""
    now = datetime.now()
    return f"Aktualna data i godzina: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def get_functions():
    """Return list of available functions for OpenAI function calling."""
    return [
        {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "set_timer",
            "description": "Set a timer for a specified duration",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "Duration in seconds",
                    },
                    "label": {"type": "string", "description": "Timer label/name"},
                },
                "required": ["seconds"],
            },
        },
        {
            "name": "view_timers",
            "description": "View all active timers",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "add_event",
            "description": "Add an event to the calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "datetime": {
                        "type": "string",
                        "description": "Event date and time in ISO format (YYYY-MM-DDTHH:MM)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description",
                    },
                },
                "required": ["datetime", "description"],
            },
        },
        {
            "name": "view_calendar",
            "description": "View all calendar events",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "set_reminder",
            "description": "Set a reminder for a specific date and time",
            "parameters": {
                "type": "object",
                "properties": {
                    "datetime": {
                        "type": "string",
                        "description": "Reminder date and time in ISO format (YYYY-MM-DDTHH:MM)",
                    },
                    "note": {"type": "string", "description": "Reminder note/message"},
                },
                "required": ["datetime", "note"],
            },
        },
        {
            "name": "view_reminders",
            "description": "View all upcoming reminders",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "add_item",
            "description": "Add an item to the shopping list",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "Item to add to shopping list",
                    }
                },
                "required": ["item"],
            },
        },
        {
            "name": "view_list",
            "description": "View the shopping list",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "remove_item",
            "description": "Remove an item from the shopping list",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "Item to remove from shopping list",
                    }
                },
                "required": ["item"],
            },
        },
        {
            "name": "add_task",
            "description": "Add a task to the to-do list",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description"}
                },
                "required": ["task"],
            },
        },
        {
            "name": "view_tasks",
            "description": "View all tasks in the to-do list",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "complete_task",
            "description": "Mark a task as completed",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_number": {
                        "type": "integer",
                        "description": "Task number to mark as completed",
                    }
                },
                "required": ["task_number"],
            },
        },
        {
            "name": "remove_task",
            "description": "Remove a task from the to-do list",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_number": {
                        "type": "integer",
                        "description": "Task number to remove",
                    }
                },
                "required": ["task_number"],
            },
        },
    ]


def execute_function(function_name: str, parameters: dict, user_id: int = None):
    """Execute a function by name with given parameters."""
    try:
        if function_name == "get_current_time":
            return get_current_time()
        elif function_name == "set_timer":
            return set_timer(parameters)
        elif function_name == "view_timers":
            return view_timers(parameters)
        elif function_name == "add_event":
            # Convert parameters to expected format
            datetime_str = parameters.get("datetime", "")
            description = parameters.get("description", "")
            param_str = f"{datetime_str} {description}"
            return add_event(param_str)
        elif function_name == "view_calendar":
            return view_calendar(parameters)
        elif function_name == "set_reminder":
            # Convert parameters to expected format
            datetime_str = parameters.get("datetime", "")
            note = parameters.get("note", "")
            param_str = f"{datetime_str} {note}"
            return set_reminder(param_str)
        elif function_name == "view_reminders":
            return view_reminders(parameters)
        elif function_name == "add_item":
            return add_item(parameters)
        elif function_name == "view_list":
            return view_list(parameters)
        elif function_name == "remove_item":
            return remove_item(parameters)
        elif function_name == "add_task":
            return add_task(parameters)
        elif function_name == "view_tasks":
            return view_tasks(parameters)
        elif function_name == "complete_task":
            return complete_task(parameters)
        elif function_name == "remove_task":
            return remove_task(parameters)
        else:
            return f"Function {function_name} not found in core_module"
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {e}")
        return f"Error executing function {function_name}: {str(e)}"

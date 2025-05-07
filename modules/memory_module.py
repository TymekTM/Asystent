"""
assistant_memory.py – obsługa długoterminowych wspomnień asystenta.

This module provides a typed, test‑friendly interface for adding,
retrieving and deleting memories stored in a persistent database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from database_models import (
    add_memory as add_memory_db,
    get_memories as get_memories_db,
    delete_memory as delete_memory_db,
)


logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Typy pomocnicze
# -----------------------------------------------------------------------------

@dataclass
class Memory:
    """Single memory entry returned from the database."""
    id: int
    user: str
    content: str

@dataclass
class Result:
    """Unified return type for all public functions."""
    success: bool
    message: str

# -----------------------------------------------------------------------------
# Walidacja / filtracja
# -----------------------------------------------------------------------------

_MIN_WORDS = 2

def _is_memorable(text: str) -> bool:
    """Return True if text should be saved as a memory."""
    tokens = text.strip().split()
    return len(tokens) >= _MIN_WORDS

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def add_memory(content: str, user: str = "assistant"):  # returns (message, success)
    """
    Save *content* to long‑term memory.

    Args:
        content: Raw text from the assistant or human.
        user:    Identifier of the author of the memory.
    """
    content = content.strip()
    if not content:
        return "Nie mogę zapisać pustej informacji.", False

    # Check for duplicates before minimal length requirement
    if get_memories_db(query=content, limit=1):  # duplicate memory
        return "Ta informacja już jest zapisana w pamięci.", False

    # content too short
    if not _is_memorable(content):
        return "Treść jest zbyt krótkiej, by ją zapamiętać.", False

    # Sprawdź duplikaty w DB – dużo szybciej niż pobieranie listy.
    if get_memories_db(query=content, limit=1):
        # duplicate memory
        return "Ta informacja już jest zapisana w pamięci.", False

    try:
        memory_id = add_memory_db(content=content, user=user)
        logger.info("Saved memory %s by user %s", memory_id, user)
        return f"Zapamiętałem: {content}", True
    except Exception as exc:
        logger.exception("DB insert failed: %s", exc)
        return "Wystąpił błąd przy zapisie do bazy.", False

def retrieve_memories(query: str = "", limit: int = None, user: Optional[str] = None, params: str = None):  # returns (message, success)
    """
    Retrieve memories. Empty *query* returns all memories.
    Returns a tuple: (message, success).
    """
    # Backwards compatibility: accept 'params' keyword for query
    if params is not None:
        query = params
    effective_limit = limit if limit is not None else 1000
    memories_list = get_memories_db(query=query or None, limit=effective_limit)
    # Filter by user if specified
    if user:
        filtered = []
        for m in memories_list:
            # support both dataclass instances and dicts
            user_val = getattr(m, 'user', None) if hasattr(m, 'user') else m.get('user', None) if isinstance(m, dict) else None
            if user_val == user:
                filtered.append(m)
        memories_list = filtered
    if not memories_list:
        return "Brak zapisanych wspomnień.", True
    # Extract content
    contents = []
    for m in memories_list:
        if hasattr(m, 'content'):
            contents.append(m.content)
        else:
            contents.append(m.get('content', ''))
    joined = "; ".join(contents)
    return f"Pamiętam: {joined}", True

def delete_memory(identifier: str, _) -> tuple:  # returns (message, success)
    """
    Delete memory by numeric *id* or substring match in *content*.

    If multiple memories match, the newest one is removed.
    If nothing matches, returns an informative message.
    """
    # Numeric ID?
    if identifier.isdigit():
        mem_id = int(identifier)
        if delete_memory_db(mem_id):
            return f"Zapomniałem wpis {mem_id}.", True
        return "Nie znaleziono wspomnienia o tym ID.", False

    # Delete by content match (newest first)
    matches = get_memories_db(query=identifier, limit=1)
    if not matches:
        # No matching memories
        return "Nie znalazłem takiej informacji.", False
    mem_id = matches[0]["id"]
    if delete_memory_db(mem_id):
        return f"Zapomniałem: {matches[0]['content']}", True
    return "Nie udało się usunąć wspomnienia.", False

# Wrappers to match plugin handler signature (params, conversation_history, user)
def _handle_add(params: str, conversation_history=None, user=None):
    """Wrapper for adding memory as plugin command"""
    return add_memory(content=params, user=user)

def _handle_get(params: str, conversation_history=None, user=None):
    """Wrapper for retrieving memories as plugin command"""
    return retrieve_memories(query=params, user=user)

def _handle_delete(params: str, conversation_history=None, user=None):
    """Wrapper for deleting memory as plugin command"""
    return delete_memory(params, None)

# --- Main handler to dispatch sub-commands ---
def handler(params=None, conversation_history=None, user=None):
    """
    Dispatch memory sub-commands: add, get, delete.
    Params can be dict with 'action' or single key for sub-command.
    """
    reg = register()
    subs = reg.get('sub_commands', {})
    # Case: dict with explicit action
    if isinstance(params, dict) and 'action' in params:
        action = params.get('action')
        sub_params = {k: v for k, v in params.items() if k != 'action'}
        if len(sub_params) == 1:
            sub_params = next(iter(sub_params.values()))
        sub = subs.get(action)
        if not sub:
            for name, sc in subs.items():
                if action in sc.get('aliases', []):
                    sub = sc
                    break
        if sub:
            return sub['function'](sub_params, conversation_history, user)
        return f"Nieznana subkomenda pamięci: {action}"
    # Case: dict with single key as sub-command
    if isinstance(params, dict) and len(params) == 1:
        key, value = next(iter(params.items()))
        sub = subs.get(key)
        if not sub:
            for name, sc in subs.items():
                if key in sc.get('aliases', []):
                    sub = sc
                    break
        if sub:
            return sub['function'](value, conversation_history, user)
    # Default: usage
    cmds = ', '.join([k for k in subs if k in subs and k == subs[k]['function'].__name__ or True])
    return f"Użyj sub-komend pamięci: add, get, delete"
    
# Plugin registration
def register():
    """Register memory plugin with main handler and sub-commands for add, get, and delete"""
    info = {
        "command": "memory",
        "aliases": ["memory", "pamięć", "pamiec"],
        "description": "Zarządza długoterminową pamięcią asystenta",
        "handler": handler,
        "sub_commands": {
            "add":    {"function": _handle_add,    "description": "Zapisuje nową informację do pamięci", "aliases": []},
            "get":    {"function": _handle_get,    "description": "Pobiera informacje z pamięci",      "aliases": []},
            "delete": {"function": _handle_delete, "description": "Usuwa informację z pamięci",      "aliases": []}
        }
    }
    # Expand aliases for sub_commands (if any)
    subs = info["sub_commands"]
    for name, sc in list(subs.items()):
        for alias in sc.get("aliases", []):
            subs.setdefault(alias, sc)
    return info

"""
assistant_memory.py – obsługa długoterminowych wspomnień asystenta.

This module provides a typed, test‑friendly interface for adding,
retrieving and deleting memories stored in a persistent database.

Extended with advanced memory management system (KT/ŚT/DT).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

from database_models import (
    add_memory as add_memory_db,
    get_memories as get_memories_db,
    delete_memory as delete_memory_db,
)

# Import advanced memory system
try:
    from advanced_memory_system import (
        get_memory_manager,
        add_memory_advanced,
        search_memories_advanced,
        MemoryType,
        ContextType,
        IMPORTANCE_THRESHOLDS
    )
    ADVANCED_MEMORY_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"Advanced memory system not available: {e}")
    ADVANCED_MEMORY_AVAILABLE = False

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

@dataclass
class MemoryStats:
    """Statistics about memory usage."""
    total_memories: int
    unique_users: int
    avg_memory_length: float
    oldest_memory: Optional[str] = None
    newest_memory: Optional[str] = None
    
    @classmethod
    def get_stats(cls) -> 'MemoryStats':
        """Calculate memory statistics from database."""
        try:
            memories = get_memories_db(query=None, limit=None)  # Get all memories
            
            if not memories:
                return cls(0, 0, 0.0)
            
            total_memories = len(memories)
            unique_users = len(set(m.get('user', '') for m in memories))
            
            content_lengths = [len(m.get('content', '')) for m in memories]
            avg_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0.0
            
            oldest = memories[-1].get('content', '') if memories else None
            newest = memories[0].get('content', '') if memories else None
            
            return cls(
                total_memories=total_memories,
                unique_users=unique_users,
                avg_memory_length=avg_length,
                oldest_memory=oldest,
                newest_memory=newest
            )
        except Exception as exc:
            logger.error("Failed to calculate memory stats: %s", exc)
            return cls(0, 0, 0.0)

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
    # Get both summary and full memory list for AI
    summary, success = retrieve_memories(query=params, user=user)
    # Always fetch all memories for AI context
    all_memories = get_memories_db(limit=10000)    # Convert to dicts for serialization if needed
    from dataclasses import asdict
    def mem_to_dict(m):
        if m is None:
            return {}
        if hasattr(m, '__dataclass_fields__'):
            return asdict(m)
        elif hasattr(m, '__dict__'):
            return dict(m.__dict__)
        return dict(m)
    all_memories_dicts = [mem_to_dict(m) for m in all_memories if m is not None]
    return {
        'summary': summary,
        'success': success,
        'all_memories': all_memories_dicts
    }

def _handle_delete(params: str, conversation_history=None, user=None):
    """Wrapper for deleting memory as plugin command"""
    return delete_memory(params, None)

# --- Main handler to dispatch sub-commands ---
def handler(params=None, conversation_history=None, user=None):
    """
    Dispatch memory sub-commands: add, get, delete.
    Params can be dict with 'action' or single key for sub-command.
    """
    # Load registered sub-commands
    subs = register().get('sub_commands', {})
    # Case: explicit 'action' key
    if isinstance(params, dict) and 'action' in params:
        raw_action = params.get('action')
        action = raw_action.lower().strip() if isinstance(raw_action, str) else str(raw_action).lower()
        # Extract remaining parameters
        sub_params = {k: v for k, v in params.items() if k != 'action'}
        if len(sub_params) == 1:
            sub_params = next(iter(sub_params.values()))
        if not sub_params:
            sub_params = ""
        # Find matching sub-command by name or alias
        sub = subs.get(action)
        if not sub:
            for sc in subs.values():
                if action in sc.get('aliases', []):
                    sub = sc
                    break
        if sub:
            return sub['function'](sub_params, conversation_history, user)
        return f"Nieznana subkomenda pamięci: {action}"
    # Case: shorthand dict {cmd: value}
    if isinstance(params, dict) and len(params) == 1:
        raw_key, value = next(iter(params.items()))
        key = raw_key.lower().strip() if isinstance(raw_key, str) else str(raw_key).lower()
        sub = subs.get(key)
        if not sub:
            for sc in subs.values():
                if key in sc.get('aliases', []):
                    sub = sc
                    break
        if sub:
            return sub['function'](value, conversation_history, user)
        return f"Nieznana subkomenda pamięci: {key}"
    # Default usage message
    base_cmds = sorted(set(cmd for cmd in subs if cmd in ['add', 'get', 'delete']))
    return f"Użyj sub-komend pamięci: {', '.join(base_cmds)}"
    
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
            "get":    {"function": _handle_get,    "description": "Pobiera informacje z pamięci",      "aliases": ["show", "check"]},
            "delete": {"function": _handle_delete, "description": "Usuwa informację z pamięci",      "aliases": []}
        }
    }
    # Expand aliases for sub_commands (if any)
    subs = info["sub_commands"]
    for name, sc in list(subs.items()):
        for alias in sc.get("aliases", []):
            subs.setdefault(alias, sc)
    return info

# -----------------------------------------------------------------------------
# Advanced Memory Functions (when available)
# -----------------------------------------------------------------------------

def add_memory_with_context(content: str, user: Optional[str] = None, 
                           memory_type: Optional[str] = None, 
                           context_type: Optional[str] = None) -> Tuple[str, bool]:
    """Add memory with advanced context information."""
    if not ADVANCED_MEMORY_AVAILABLE:
        return add_memory(content, user)
    
    try:
        memory_id = add_memory_advanced(
            content=content,
            user=user,
            memory_type=memory_type,
            context_type=context_type
        )
        logger.info("Added advanced memory %s by user %s", memory_id, user)
        return f"Zapamiętałem (zaawansowane): {content}", True
    except Exception as exc:
        logger.error("Failed to add advanced memory: %s", exc)
        # Fallback to legacy system
        return add_memory(content, user)


def search_memories_with_context(query: str, user: Optional[str] = None,
                                memory_type: Optional[str] = None,
                                limit: int = 10) -> Tuple[List[Dict], bool]:
    """Search memories with advanced context filtering."""
    if not ADVANCED_MEMORY_AVAILABLE:
        memories, success = retrieve_memories(query, limit)
        if success:
            return [{'content': m.content, 'user': m.user, 'id': m.id} for m in memories], True
        return [], False
    
    try:
        results = search_memories_advanced(
            query=query,
            user=user,
            memory_type=memory_type,
            limit=limit
        )
        
        # Convert to dictionary format for compatibility
        formatted_results = []
        for entry in results:
            formatted_results.append({
                'content': entry.content,
                'user': entry.user,
                'id': entry.id if hasattr(entry, 'id') else 0,
                'memory_type': entry.memory_type,
                'importance_score': entry.importance_score,
                'context_tags': entry.context_tags,
                'created_at': entry.created_at.isoformat() if entry.created_at else None
            })
        
        return formatted_results, True
    except Exception as exc:
        logger.error("Failed to search advanced memories: %s", exc)
        # Fallback to legacy system
        memories, success = retrieve_memories(query, limit)
        if success:
            return [{'content': m.content, 'user': m.user, 'id': m.id} for m in memories], True
        return [], False


def get_advanced_memory_stats() -> Dict[str, Any]:
    """Get advanced memory statistics."""
    if not ADVANCED_MEMORY_AVAILABLE:
        stats = MemoryStats.get_stats()
        return {
            'total_memories': stats.total_memories,
            'unique_users': stats.unique_users,
            'avg_memory_length': stats.avg_memory_length
        }
    
    try:
        manager = get_memory_manager()
        return manager.get_memory_statistics()
    except Exception as exc:
        logger.error("Failed to get advanced memory stats: %s", exc)
        # Fallback to basic stats
        stats = MemoryStats.get_stats()
        return {
            'total_memories': stats.total_memories,
            'unique_users': stats.unique_users,
            'avg_memory_length': stats.avg_memory_length
        }

# -----------------------------------------------------------------------------

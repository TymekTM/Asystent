"""
database_models.py – definicja schematu oraz CRUD dla users, memories i user_configs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional

from database_manager import get_connection

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Dataclasses – wygodne mapowanie wierszy → obiekty
# -----------------------------------------------------------------------------

@dataclass(slots=True)
class User:
    id: int
    username: str
    role: str
    display_name: str | None
    ai_persona: str | None
    personalization: str | None

@dataclass(slots=True)
class Memory:
    id: int
    content: str
    user: str
    timestamp: datetime

@dataclass(slots=True)
class UserConfig:
    user_id: int
    config: dict

# New Memory System Dataclasses
@dataclass(slots=True)
class ShortTermMemory:
    id: int
    content: str
    user: str
    importance_score: float
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    context_tags: str | None = None

@dataclass(slots=True)
class MidTermMemory:
    id: int
    content: str
    user: str
    importance_score: float
    created_at: datetime
    expires_at: datetime
    context_type: str
    access_count: int = 0
    context_tags: str | None = None

@dataclass(slots=True)
class LongTermMemory:
    id: int
    content: str
    user: str
    importance_score: float
    created_at: datetime
    is_important: bool
    memory_type: str
    context_tags: str | None = None
    access_count: int = 0

@dataclass(slots=True)
class MemoryAnalytics:
    id: int
    memory_id: int
    memory_type: str  # 'short', 'mid', 'long'
    action: str  # 'create', 'access', 'promote', 'expire'
    timestamp: datetime
    importance_change: float | None = None
    context_data: str | None = None

# -----------------------------------------------------------------------------
# Init schema
# -----------------------------------------------------------------------------

def init_schema(seed_dev: bool = True) -> None:
    """Create tables if they don't exist; optionally seed a 'dev' account."""
    with get_connection() as conn:
        # First create tables with IF NOT EXISTS
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password      TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'user',
                display_name  TEXT,
                ai_persona    TEXT,
                personalization TEXT
            );

            CREATE TABLE IF NOT EXISTS memories (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                content   TEXT NOT NULL,
                user      TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                importance_score REAL DEFAULT 0.0,
                is_important BOOLEAN DEFAULT FALSE,
                memory_type TEXT DEFAULT 'general',
                context_tags TEXT,
                access_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS user_configs (
                user_id INTEGER PRIMARY KEY,
                config  TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            
            -- Table to store chat history separate from long-term memories
            CREATE TABLE IF NOT EXISTS chat_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                role        TEXT NOT NULL,  -- 'user' or 'assistant'
                content     TEXT NOT NULL,
                user_id     INTEGER,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            -- Advanced Memory System Tables
            CREATE TABLE IF NOT EXISTS short_term_memory (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                content         TEXT NOT NULL,
                user            TEXT NOT NULL,
                importance_score REAL DEFAULT 0.0,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at      DATETIME NOT NULL,
                last_accessed   DATETIME DEFAULT CURRENT_TIMESTAMP,
                context_tags    TEXT
            );

            CREATE TABLE IF NOT EXISTS mid_term_memory (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                content         TEXT NOT NULL,
                user            TEXT NOT NULL,
                importance_score REAL DEFAULT 0.0,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at      DATETIME NOT NULL,
                context_type    TEXT NOT NULL,
                access_count    INTEGER DEFAULT 0,
                context_tags    TEXT
            );

            CREATE TABLE IF NOT EXISTS memory_analytics (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id       INTEGER NOT NULL,
                memory_type     TEXT NOT NULL, -- 'short', 'mid', 'long'
                action          TEXT NOT NULL, -- 'create', 'access', 'promote', 'expire'
                timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
                importance_change REAL,
                context_data    TEXT
            );

            -- Indices for performance
            CREATE INDEX IF NOT EXISTS idx_short_term_expires ON short_term_memory(expires_at);
            CREATE INDEX IF NOT EXISTS idx_mid_term_expires ON mid_term_memory(expires_at);
            CREATE INDEX IF NOT EXISTS idx_memory_importance ON memories(importance_score);
            CREATE INDEX IF NOT EXISTS idx_memory_tags ON memories(context_tags);
            CREATE INDEX IF NOT EXISTS idx_analytics_type_time ON memory_analytics(memory_type, timestamp);
            """        )
        
        # Perform migrations for existing databases
        _migrate_database(conn)

        if seed_dev:
            # Reset or ensure default dev account without wiping database
            default_username = "dev"
            default_password = "devpassword"
            default_role = "dev"
            # Try to add dev user; if exists, update credentials
            added = add_user_if_absent(
                username=default_username,
                password=default_password,
                role=default_role,
                display_name="Dev",
                ai_persona="Admin",
            )
            if not added:
                # Update existing dev account with default password and settings
                update_user(
                    default_username,
                    password=default_password,
                    role=default_role,                    display_name="Dev",
                    ai_persona="Admin",
                )

# -----------------------------------------------------------------------------
# Database Migration
# -----------------------------------------------------------------------------

def _migrate_database(conn):
    """Perform database migrations for existing databases."""
    try:
        # Check if memories table has new columns, add them if missing
        cursor = conn.cursor()
        
        # Get current column names for memories table
        cursor.execute("PRAGMA table_info(memories)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add missing columns to memories table
        if 'importance_score' not in columns:
            cursor.execute("ALTER TABLE memories ADD COLUMN importance_score REAL DEFAULT 0.0")
        
        if 'is_important' not in columns:
            cursor.execute("ALTER TABLE memories ADD COLUMN is_important BOOLEAN DEFAULT FALSE")
            
        if 'memory_type' not in columns:
            cursor.execute("ALTER TABLE memories ADD COLUMN memory_type TEXT DEFAULT 'general'")
            
        if 'context_tags' not in columns:
            cursor.execute("ALTER TABLE memories ADD COLUMN context_tags TEXT")
            
        if 'access_count' not in columns:
            cursor.execute("ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0")
        
        conn.commit()
        
    except Exception as e:
        logger.error("Migration failed: %s", e)
        # Don't fail initialization if migration fails
        pass


# -----------------------------------------------------------------------------
# Users
# -----------------------------------------------------------------------------

def _row_to_user(row) -> User:
    return User(**row)

def add_user_if_absent(
    username: str,
    password: str,
    role: str = "user",
    display_name: str | None = None,
    ai_persona: str | None = None,
    personalization: str | None = None,
) -> bool:
    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (username, password, role, display_name, ai_persona, personalization)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, password, role, display_name, ai_persona, personalization),
            )
            return True
        except Exception:  # likely UNIQUE
            return False
    
# Aliases for external imports (e.g., web_ui)
add_user = add_user_if_absent
initialize_database = init_schema

def get_user_by_username(username: str) -> User | None:
    with get_connection() as conn:
        # Select only the columns needed for the User dataclass
        row = conn.execute(
            "SELECT id, username, role, display_name, ai_persona, personalization FROM users WHERE username = ?", (username,)
        ).fetchone()
    return _row_to_user(row) if row else None


def get_user_password_hash(username: str) -> str | None:
    """Fetches only the password hash for a given username."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT password FROM users WHERE username = ?", (username,)
        ).fetchone()
    return row['password'] if row else None


def list_users() -> List[User]:
    with get_connection() as conn:
        # Select only the columns needed for the User dataclass
        rows = conn.execute("SELECT id, username, role, display_name, ai_persona, personalization FROM users").fetchall()
    return [_row_to_user(r) for r in rows]


def update_user(username: str, **fields) -> None:
    if not fields:
        return
    keys = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [username]
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {keys} WHERE username = ?", values)


def delete_user(username: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))


# -----------------------------------------------------------------------------
# Memories  (assistant‑level, nie user‑level)
# -----------------------------------------------------------------------------

def _row_to_memory(row) -> Memory:
    """Convert a database row to Memory, mapping 'user_id' if present to 'user'."""
    data = dict(row)
    # Map 'user_id' to 'user' for compatibility
    if 'user_id' in data:
        data['user'] = data.pop('user_id')
    
    # Convert timestamp string to datetime object
    if 'timestamp' in data and isinstance(data['timestamp'], str):
        try:
            # Attempt to parse common ISO formats, adjust if your format is different
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            try:
                # Fallback for other common formats, e.g., "YYYY-MM-DD HH:MM:SS"
                data['timestamp'] = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.error(f"Could not parse timestamp string: {data['timestamp']}")
                # Handle error appropriately, e.g., set to None or raise, or use current time
                data['timestamp'] = datetime.now() # Or None, depending on desired behavior

    return Memory(**data)

def add_memory(content: str, user: str = "assistant") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO memories (content, user) VALUES (?, ?)", (content, user)
        )
        return cur.lastrowid


def get_memories(limit: int = 100, query: str | None = None) -> List[Memory]:
    sql = "SELECT * FROM memories"
    params: list = []
    if query:
        sql += " WHERE content LIKE ?"
        params.append(f"%{query}%")
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_memory(r) for r in rows]


def delete_memory(memory_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return cur.rowcount > 0


# -----------------------------------------------------------------------------
# User configs (JSON blob)
# -----------------------------------------------------------------------------

def set_user_config(user_id: int, config: dict) -> None:
    config_json = json.dumps(config)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_configs (user_id, config)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET config=excluded.config
            """,
            (user_id, config_json),
        )


def get_user_config(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT config FROM user_configs WHERE user_id = ?", (user_id,)
        ).fetchone()
    return json.loads(row["config"]) if row else None


# -----------------------------------------------------------------------------
# Chat History Functions
# -----------------------------------------------------------------------------

def add_chat_message(role: str, content: str, user_id: Optional[int] = None) -> bool:
    """
    Add a new message to the chat history.
    
    Args:
        role: Either 'user' or 'assistant'
        content: The message content
        user_id: Optional user ID to associate with message
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (role, content, user_id, timestamp) VALUES (?, ?, ?, datetime('now'))",
                (role, content, user_id)
            )
            return True
    except Exception as e:
        logger.error(f"Error adding chat message to history: {e}")
        return False

def get_chat_history(limit: int = 50) -> List[dict]:
    """
    Get recent chat history entries.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List of chat history entries as dictionaries with role, content, timestamp
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, timestamp FROM chat_history ORDER BY timestamp DESC LIMIT ?", 
                (limit,)
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2]
                })
            return results
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return []

def clear_chat_history() -> bool:
    """
    Clear all chat history entries.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history")
            return True
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return False


# -----------------------------------------------------------------------------
# Advanced Memory System CRUD Functions
# -----------------------------------------------------------------------------

def _row_to_short_term_memory(row) -> ShortTermMemory:
    """Convert a database row to ShortTermMemory."""
    data = dict(row)
    # Convert timestamp strings to datetime objects
    for field in ['created_at', 'expires_at', 'last_accessed']:
        if field in data and isinstance(data[field], str):
            try:
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
            except ValueError:
                try:
                    data[field] = datetime.strptime(data[field], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    logger.error(f"Could not parse timestamp: {data[field]}")
                    data[field] = datetime.now()
    return ShortTermMemory(**data)

def _row_to_mid_term_memory(row) -> MidTermMemory:
    """Convert a database row to MidTermMemory."""
    data = dict(row)
    # Convert timestamp strings to datetime objects
    for field in ['created_at', 'expires_at']:
        if field in data and isinstance(data[field], str):
            try:
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
            except ValueError:
                try:
                    data[field] = datetime.strptime(data[field], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    logger.error(f"Could not parse timestamp: {data[field]}")
                    data[field] = datetime.now()
    return MidTermMemory(**data)

def _row_to_long_term_memory(row) -> LongTermMemory:
    """Convert a database row to LongTermMemory (extended memories table)."""
    data = dict(row)
    # Map old timestamp field to created_at
    if 'timestamp' in data:
        data['created_at'] = data.pop('timestamp')
    
    # Convert timestamp strings to datetime objects
    if 'created_at' in data and isinstance(data['created_at'], str):
        try:
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        except ValueError:
            try:
                data['created_at'] = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.error(f"Could not parse timestamp: {data['created_at']}")
                data['created_at'] = datetime.now()
    
    # Ensure all required fields exist with defaults
    data.setdefault('importance_score', 0.0)
    data.setdefault('is_important', False)
    data.setdefault('memory_type', 'general')
    data.setdefault('context_tags', None)
    data.setdefault('access_count', 0)
    
    return LongTermMemory(**data)

def _row_to_memory_analytics(row) -> MemoryAnalytics:
    """Convert a database row to MemoryAnalytics."""
    data = dict(row)
    if 'timestamp' in data and isinstance(data['timestamp'], str):
        try:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            try:
                data['timestamp'] = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.error(f"Could not parse timestamp: {data['timestamp']}")
                data['timestamp'] = datetime.now()
    return MemoryAnalytics(**data)

# Short Term Memory CRUD
def add_short_term_memory(content: str, user: str, importance_score: float = 0.0, 
                         expires_in_minutes: int = 20, context_tags: str = None) -> int:
    """Add a new short-term memory entry."""
    from datetime import timedelta
    expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
    
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO short_term_memory 
               (content, user, importance_score, expires_at, context_tags) 
               VALUES (?, ?, ?, ?, ?)""",
            (content, user, importance_score, expires_at, context_tags)
        )
        return cur.lastrowid

def get_short_term_memories(limit: int = 100, user: str = None, 
                           exclude_expired: bool = True) -> List[ShortTermMemory]:
    """Get short-term memories."""
    sql = "SELECT * FROM short_term_memory"
    params = []
    conditions = []
    
    if exclude_expired:
        conditions.append("expires_at > ?")
        params.append(datetime.now())
    
    if user:
        conditions.append("user = ?")
        params.append(user)
    
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    sql += " ORDER BY last_accessed DESC, importance_score DESC LIMIT ?"
    params.append(limit)
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_short_term_memory(r) for r in rows]

def update_short_term_memory_access(memory_id: int) -> bool:
    """Update last_accessed timestamp for a short-term memory."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE short_term_memory SET last_accessed = ? WHERE id = ?",
            (datetime.now(), memory_id)
        )
        return cur.rowcount > 0

def delete_expired_short_term_memories() -> int:
    """Delete expired short-term memories and return count deleted."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM short_term_memory WHERE expires_at <= ?",
            (datetime.now(),)
        )
        return cur.rowcount

# Mid Term Memory CRUD
def add_mid_term_memory(content: str, user: str, context_type: str,
                       importance_score: float = 0.0, context_tags: str = None) -> int:
    """Add a new mid-term memory entry (expires at end of day)."""
    from datetime import time, date, timedelta
    # Set expiry to end of current day
    today = date.today()
    expires_at = datetime.combine(today + timedelta(days=1), time(0, 0))
    
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO mid_term_memory 
               (content, user, importance_score, expires_at, context_type, context_tags) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (content, user, importance_score, expires_at, context_type, context_tags)
        )
        return cur.lastrowid

def get_mid_term_memories(limit: int = 100, user: str = None, context_type: str = None,
                         exclude_expired: bool = True) -> List[MidTermMemory]:
    """Get mid-term memories."""
    sql = "SELECT * FROM mid_term_memory"
    params = []
    conditions = []
    
    if exclude_expired:
        conditions.append("expires_at > ?")
        params.append(datetime.now())
    
    if user:
        conditions.append("user = ?")
        params.append(user)
        
    if context_type:
        conditions.append("context_type = ?")
        params.append(context_type)
    
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    sql += " ORDER BY access_count DESC, importance_score DESC LIMIT ?"
    params.append(limit)
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_mid_term_memory(r) for r in rows]

def increment_mid_term_memory_access(memory_id: int) -> bool:
    """Increment access count for a mid-term memory."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE mid_term_memory SET access_count = access_count + 1 WHERE id = ?",
            (memory_id,)
        )
        return cur.rowcount > 0

def delete_expired_mid_term_memories() -> int:
    """Delete expired mid-term memories and return count deleted."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM mid_term_memory WHERE expires_at <= ?",
            (datetime.now(),)
        )
        return cur.rowcount

# Enhanced Long Term Memory functions
def add_long_term_memory_enhanced(content: str, user: str = "assistant", 
                                 importance_score: float = 0.0, is_important: bool = False,
                                 memory_type: str = "general", context_tags: str = None) -> int:
    """Add enhanced long-term memory with new fields."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO memories 
               (content, user, importance_score, is_important, memory_type, context_tags) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (content, user, importance_score, is_important, memory_type, context_tags)
        )
        return cur.lastrowid

def get_long_term_memories_enhanced(limit: int = 100, query: str = None, user: str = None,
                                   min_importance: float = None, memory_type: str = None,
                                   is_important_only: bool = False) -> List[LongTermMemory]:
    """Get enhanced long-term memories with filtering options."""
    sql = "SELECT * FROM memories"
    params = []
    conditions = []
    
    if query:
        conditions.append("content LIKE ?")
        params.append(f"%{query}%")
    
    if user:
        conditions.append("user = ?")
        params.append(user)
        
    if min_importance is not None:
        conditions.append("importance_score >= ?")
        params.append(min_importance)
        
    if memory_type:
        conditions.append("memory_type = ?")
        params.append(memory_type)
        
    if is_important_only:
        conditions.append("is_important = 1")
    
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    sql += " ORDER BY importance_score DESC, timestamp DESC LIMIT ?"
    params.append(limit)
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_long_term_memory(r) for r in rows]

def update_long_term_memory_importance(memory_id: int, importance_score: float, 
                                     is_important: bool = None) -> bool:
    """Update importance score and flag for long-term memory."""
    if is_important is not None:
        sql = "UPDATE memories SET importance_score = ?, is_important = ?, access_count = access_count + 1 WHERE id = ?"
        params = (importance_score, is_important, memory_id)
    else:
        sql = "UPDATE memories SET importance_score = ?, access_count = access_count + 1 WHERE id = ?"
        params = (importance_score, memory_id)
    
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount > 0

# Memory Analytics CRUD
def add_memory_analytics_entry(memory_id: int, memory_type: str, action: str,
                              importance_change: float = None, context_data: str = None) -> int:
    """Add memory analytics entry."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO memory_analytics 
               (memory_id, memory_type, action, importance_change, context_data) 
               VALUES (?, ?, ?, ?, ?)""",
            (memory_id, memory_type, action, importance_change, context_data)
        )
        return cur.lastrowid

def get_memory_analytics(memory_id: int = None, memory_type: str = None, 
                        action: str = None, limit: int = 100) -> List[MemoryAnalytics]:
    """Get memory analytics entries."""
    sql = "SELECT * FROM memory_analytics"
    params = []
    conditions = []
    
    if memory_id is not None:
        conditions.append("memory_id = ?")
        params.append(memory_id)
    
    if memory_type:
        conditions.append("memory_type = ?")
        params.append(memory_type)
        
    if action:
        conditions.append("action = ?")
        params.append(action)
    
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_memory_analytics(r) for r in rows]

# -----------------------------------------------------------------------------
# Self‑test (manual run)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_schema()
    print("Current users:", list_users())
    print("Add sample memory:", add_memory("Hello world"))
    print("Memories:", get_memories())

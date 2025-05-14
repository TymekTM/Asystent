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

# -----------------------------------------------------------------------------
# Init schema
# -----------------------------------------------------------------------------

def init_schema(seed_dev: bool = True) -> None:
    """Create tables if they don’t exist; optionally seed a 'dev' account."""
    with get_connection() as conn:
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
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_configs (
                user_id INTEGER PRIMARY KEY,
                config  TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );            -- Table to store chat history separate from long-term memories
            CREATE TABLE IF NOT EXISTS chat_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                role        TEXT NOT NULL,  -- 'user' or 'assistant'
                content     TEXT NOT NULL,
                user_id     INTEGER,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )

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
                role=default_role,
                display_name="Dev",
                ai_persona="Admin",
            )
        logger.debug("✅ Dev account ensured or reset to default credentials")
   


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
# Self‑test (manual run)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_schema()
    print("Current users:", list_users())
    print("Add sample memory:", add_memory("Hello world"))
    print("Memories:", get_memories())

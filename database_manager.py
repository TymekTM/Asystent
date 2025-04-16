import sqlite3
import os
import logging
from datetime import datetime
from database_models import (
    get_user_by_username, add_user, delete_user, list_users, update_user,
    set_user_config, get_user_config, initialize_database
)

logger = logging.getLogger(__name__)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'assistant_memory.db')

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        logger.debug(f"Database connection established to {DATABASE_PATH}")
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database {DATABASE_PATH}: {e}")
    return conn

def initialize_database():
    """Initializes the database by creating the memories table if it doesn't exist."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    user TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("Database initialized successfully. 'memories' table ensured.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database table 'memories': {e}")
        finally:
            conn.close()
    else:
        logger.error("Failed to initialize database: No connection.")

def add_memory_db(content: str, user: str = "assistant") -> int | None:
    """Adds a new memory to the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO memories (content, user) VALUES (?, ?)", (content, user))
            conn.commit()
            memory_id = cursor.lastrowid
            logger.info(f"Memory added successfully (ID: {memory_id}, User: {user}): {content[:50]}...")
            return memory_id
        except sqlite3.Error as e:
            logger.error(f"Error adding memory (User: {user}): {e}")
            return None
        finally:
            conn.close()
    else:
        logger.error("Failed to add memory: No database connection.")
        return None

def get_memories_db(query: str = None, limit: int = 100) -> list[dict]:
    """Retrieves memories from the database, optionally filtering by content."""
    conn = get_db_connection()
    memories = []
    if conn:
        try:
            cursor = conn.cursor()
            sql = "SELECT id, content, user, timestamp FROM memories"
            params = []
            if query:
                sql += " WHERE content LIKE ?"
                params.append(f"%{query}%")
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            memories = [dict(row) for row in rows] # Convert rows to dictionaries
            logger.debug(f"Retrieved {len(memories)} memories (Query: {query}, Limit: {limit}).")
        except sqlite3.Error as e:
            logger.error(f"Error retrieving memories (Query: {query}): {e}")
        finally:
            conn.close()
    else:
        logger.error("Failed to retrieve memories: No database connection.")
    return memories

def delete_memory_db(memory_id: int) -> bool:
    """Deletes a specific memory by its ID."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            success = cursor.rowcount > 0
            if success:
                logger.info(f"Memory deleted successfully (ID: {memory_id}).")
            else:
                logger.warning(f"Attempted to delete memory ID {memory_id}, but it was not found.")
            return success
        except sqlite3.Error as e:
            logger.error(f"Error deleting memory (ID: {memory_id}): {e}")
            return False
        finally:
            conn.close()
    else:
        logger.error("Failed to delete memory: No database connection.")
        return False

def clear_all_memories_db() -> bool:
    """Deletes all memories from the database."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories")
            conn.commit()
            logger.warning(f"All memories deleted. Rows affected: {cursor.rowcount}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error clearing all memories: {e}")
            return False
        finally:
            conn.close()
    else:
        logger.error("Failed to clear memories: No database connection.")
        return False

# Initialize the database when the module is loaded
initialize_database()

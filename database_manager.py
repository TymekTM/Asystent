"""
database_manager.py – niskopoziomowa obsługa połączeń z SQLite.
Używaj funkcji get_connection() jako context managera:

    from database_manager import get_connection
    with get_connection() as conn:
        conn.execute(...)
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

DB_PATH: Path = Path(__file__).with_name("gaja_memory.db")

@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yields a SQLite connection that commits on success and rolls back on error."""
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("DB error: %s", exc)
        raise
    finally:
        if conn:
            conn.close()

# --- Back-compat exports -----------------------------------------------------
# Removed to avoid circular import with database_models
__all__ = [
    "get_connection",
    # Back-compatible alias
    "get_db_connection",
]
# Alias for backward compatibility
get_db_connection = get_connection

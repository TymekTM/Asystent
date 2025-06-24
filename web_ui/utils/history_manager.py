import os
import shutil
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.config import HISTORY_ARCHIVE_DIR, HISTORY_FILE, logger


def get_conversation_history(limit=50, buffer_multiplier=5):
    """Reads conversation history from the database.

    Returns up to 'limit' entries in chronological order.
    """
    logger.debug(f"Reading conversation history from database, limit: {limit}")
    try:
        # Use the new database function for retrieving history
        from database_models import get_chat_history

        history = get_chat_history(limit=limit)

        # Reverse to get chronological order (oldest first)
        history.reverse()

        logger.info(f"Retrieved {len(history)} history entries from database.")

        if not history:
            # No history in database, return empty list
            logger.info("No conversation history found in database.")
            return []

        return history

    except Exception as e:
        logger.error(f"Error reading history from database: {e}", exc_info=True)
        # On error, return empty history
        return []


def _read_history_from_logfile(limit=50):
    """Fallback function to read history from log file if database retrieval fails."""
    history = []
    logger.warning("Reading conversation history from log file as fallback")
    try:
        if os.path.exists(HISTORY_FILE):
            # Simplified log parsing as fallback
            with open(HISTORY_FILE, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-1000:]  # Read last 1000 lines max

            for line in lines:
                if "INFO - Refined query:" in line:
                    timestamp = line.split(" - ", 1)[0]
                    content = line.split("Refined query:", 1)[1].strip()
                    if content:
                        history.append(
                            {"role": "user", "content": content, "timestamp": timestamp}
                        )
                elif "INFO - TTS:" in line:
                    timestamp = line.split(" - ", 1)[0]
                    content = line.split("TTS:", 1)[1].strip()
                    if content:
                        history.append(
                            {
                                "role": "assistant",
                                "content": content,
                                "timestamp": timestamp,
                            }
                        )

            # Limit and sort
            history = sorted(history, key=lambda x: x.get("timestamp", ""))[-limit:]
            logger.info(
                f"Fallback: Retrieved {len(history)} history entries from log file."
            )

            # Try to add these entries to the database for future use
            try:
                from database_models import add_chat_message

                for entry in history:
                    add_chat_message(entry["role"], entry["content"])
                logger.info(f"Added {len(history)} log entries to history database")
            except Exception as db_err:
                logger.error(f"Could not migrate log entries to database: {db_err}")
    except Exception as fallback_error:
        logger.error(
            f"Fallback history retrieval failed: {fallback_error}", exc_info=True
        )

    # Filter out empty messages just before returning
    return [entry for entry in history if entry.get("content")]


def clear_conversation_history():
    """Clears the history from the database and archives the current log file."""
    logger.warning("Clear conversation history requested")

    try:
        # Clear history from database
        from database_models import clear_chat_history

        db_success = clear_chat_history()

        if not db_success:
            logger.error("Failed to clear history from database")
            return False

        logger.info("Cleared conversation history from database")

        # Also archive the log file for backup
        if os.path.exists(HISTORY_FILE):
            # Create archive directory if it doesn't exist
            os.makedirs(HISTORY_ARCHIVE_DIR, exist_ok=True)

            # Archive the current log file
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            archive_path = os.path.join(
                HISTORY_ARCHIVE_DIR, f"assistant_{timestamp}.log"
            )

            # Move the file
            shutil.move(HISTORY_FILE, archive_path)
            logger.info(f"Archived current history log file to: {archive_path}")

        return True
    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}", exc_info=True)
        return False


def load_ltm():
    """Load long-term memory from file."""
    from core.config import LTM_FILE

    if not os.path.exists(LTM_FILE):
        return []
    try:
        import json

        with open(LTM_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load LTM: {e}")
        return []


def save_ltm(data):
    """Save long-term memory to file."""
    from core.config import LTM_FILE

    try:
        import json

        with open(LTM_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save LTM: {e}")
        return False

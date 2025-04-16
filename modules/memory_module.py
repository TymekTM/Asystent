"""
Module providing functions for the assistant to interact with its long-term memory,
which is stored in a database via the database_manager.
"""
import logging
from database_manager import (
    add_memory_db,
    get_memories_db,
    delete_memory_db,
    # clear_all_memories_db # Keep this commented out for AI safety
)

logger = logging.getLogger(__name__)

# --- Functions intended for direct use by the assistant (or via tool mapping) ---

def add_memory(params: str, conversation_history: list = None, user: str = "assistant") -> str:
    """
    Adds a piece of information to the long-term memory database.
    Called via command like: !add_memory <content>
    """
    content = params.strip()
    if not content:
        logger.warning("Add memory command called with empty content.")
        return "Nie mogę zapisać pustej informacji. Podaj treść po komendzie.", False # Return False for failure

    # Determine the user - if called by AI, it's 'assistant', otherwise could be specified?
    # For now, assume AI calls always use 'assistant' unless logic changes
    calling_user = "assistant" # Hardcode for now, can be refined if needed

    logger.info(f"Attempting to add memory via command: '{content[:50]}...' by user '{calling_user}'")
    memory_id = add_memory_db(content=content, user=calling_user)

    if memory_id is not None:
        return f"Zapamiętałem: {content}", True # Return True for success
    else:
        return "Nie udało mi się zapisać informacji.", False

def retrieve_memories(params: str = "", conversation_history: list = None, user: str = None) -> str:
    """
    Retrieves memories from the database, optionally filtering by a query string.
    If no params are given, returns ALL memories for the user (or all if user is None).
    Returns only the content of memories, not DB metadata.
    """
    query = params.strip()
    logger.info(f"Retrieving memories via command with query: '{query}' user: '{user}'")
    # Pobierz wszystkie wspomnienia danego usera jeśli nie podano query
    if not query and user:
        memories = get_memories_db(query=None, limit=1000)
        memories = [m for m in memories if m.get('user') == user]
    else:
        memories = get_memories_db(query=query, limit=1000)
        if user:
            memories = [m for m in memories if m.get('user') == user]
    if not memories:
        result = "Nie znalazłem żadnych pasujących wspomnień." if query else "Brak zapisanych wspomnień."
        return result, True
    if len(memories) == 1:
        return f"Pamiętam: {memories[0]['content']}", True
    else:
        contents = [m['content'] for m in memories if m.get('content')]
        joined = "; ".join(contents)
        return f"Pamiętam: {joined}", True

def delete_memory(params: str, conversation_history: list = None) -> str:
    """
    Deletes a specific memory entry by its ID or by matching content.
    Called via command like: !delete_memory <id or content>
    """
    try:
        param = params.strip()
        found = []
        content = None
        if param.isdigit():
            memory_id = int(param)
            found = get_memories_db(query=None, limit=1000)
            content = next((m['content'] for m in found if m['id'] == memory_id), None)
        else:
            found = get_memories_db(query=param, limit=1)
            if found:
                memory_id = found[0]['id']
                content = found[0]['content']
            else:
                # Jeśli nie znaleziono, usuń ostatni wpis
                all_memories = get_memories_db(query=None, limit=1)
                if all_memories:
                    memory_id = all_memories[0]['id']
                    content = all_memories[0]['content']
                else:
                    return "Nie mam już nic do zapomnienia.", False
        logger.info(f"Attempting to delete memory via command with ID: {memory_id}")
        if delete_memory_db(memory_id):
            return f"Zapomniałem: {content}", True
        else:
            return f"Nie udało mi się zapomnieć tej informacji.", False
    except Exception as e:
        logger.error(f"Error during memory deletion command (ID: {params}): {e}")
        return "Wystąpił błąd podczas usuwania wspomnienia.", False

# --- Plugin Registration ---

def register():
    """Registers the memory commands for the assistant."""
    return {
        "command": "memory", # Main command group (optional, could register individually)
        "sub_commands": {
            "add": {
                "function": add_memory,
                "description": "Zapisuje ważną informację do długoterminowej pamięci. Użyj, gdy użytkownik powie coś istotnego do zapamiętania lub gdy wynik jakiegoś działania powinien zostać zachowany na przyszłość.",
                "aliases": ["zapamietaj", "zapisz"],
                "params_desc": "<treść informacji>"
            },
            "get": {
                "function": retrieve_memories,
                "description": "Pobiera zapisane wcześniej informacje z długoterminowej pamięci. Można podać słowa kluczowe, aby filtrować wyniki.",
                "aliases": ["przypomnij", "pokaz_pamiec"],
                 "params_desc": "[słowa kluczowe]" # Optional query
            },
            "del": {
                "function": delete_memory,
                "description": "Usuwa konkretny wpis z długoterminowej pamięci na podstawie jego unikalnego ID lub pasującej treści.",
                "aliases": ["usun_pamiec", "zapomnij"],
                "params_desc": "<ID wpisu lub treść>"
            }
            # 'clear_all' is intentionally omitted for safety when called by AI
        },
        "description": "Zarządza długoterminową pamięcią asystenta (dodawanie, pobieranie, usuwanie wpisów)."
        # No top-level handler needed if using sub_commands
    }

# Remove the old MEMORY_TOOLS dictionary and get_memory_tools_info function
# Remove the if __name__ == '__main__': block

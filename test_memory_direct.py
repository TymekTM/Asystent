#!/usr/bin/env python3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "server"))

from database_manager import DatabaseManager

def test_memory_save():
    """Test bezpośrednio funkcję save_memory_context."""
    db = DatabaseManager("server/server_data.db")
    
    # Sprawdź czy użytkownik istnieje
    user = db.get_user(username="default_user")
    if not user:
        print("❌ Brak użytkownika testowego!")
        return
    
    print(f"✅ Użytkownik istnieje: ID {user.id}")
    
    # Spróbuj zapisać pamięć bezpośrednio
    try:
        db.save_memory_context(
            user_id=user.id,
            context_type="test",
            key_name="test_key",
            value="test_value",
            metadata={}
        )
        print("✅ Memory save successful!")
        
        # Sprawdź czy zapisało się
        memories = db.get_memory_context(user.id, "test", "test_key")
        print(f"✅ Retrieved {len(memories)} memory entries")
        for memory in memories:
            print(f"  - {memory.key_name}: {memory.value}")
            
    except Exception as e:
        print(f"❌ Memory save failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_memory_save()

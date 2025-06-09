#!/usr/bin/env python3
"""
Debug memory module database issues
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server path
sys.path.insert(0, str(Path(__file__).parent / "server"))

async def debug_memory_issue():
    """Debug memory module database constraints."""
    print("🔍 Debugging Memory Module Database Issues")
    print("=" * 50)
    
    try:
        from database_manager import get_database_manager
        from modules.memory_module import MemoryModule
        
        # Get database manager
        db_manager = get_database_manager()
          # Check if user exists
        print("1. Checking if user exists...")
        users = await db_manager.get_all_users()
        print(f"   Found {len(users)} users in database")
        for user in users:
            print(f"   User ID: {user.id}, Username: {user.username}")
              # Check memory contexts table
        print("\n2. Checking memory_contexts table structure...")
        import sqlite3
        conn = sqlite3.connect("server_data.db")  # Use correct database path
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("PRAGMA table_info(memory_contexts)")
        columns = cursor.fetchall()
        print("   Columns in memory_contexts:")
        for col in columns:
            print(f"     {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
            
        # Check foreign key constraints
        cursor.execute("PRAGMA foreign_key_list(memory_contexts)")
        foreign_keys = cursor.fetchall()
        print("   Foreign keys:")
        for fk in foreign_keys:
            print(f"     {fk}")
            
        conn.close()
        
        # Try to save memory directly using database manager
        print("\n3. Testing direct database save...")
        try:
            db_manager.save_memory_context(
                user_id=1,
                context_type="test",
                key_name="debug_test",
                value="test value",
                metadata={}
            )
            print("   ✅ Direct database save successful")
        except Exception as e:
            print(f"   ❌ Direct database save failed: {e}")
            
        # Try memory module
        print("\n4. Testing MemoryModule...")
        memory_module = MemoryModule()
        try:
            success = memory_module.save_memory(
                user_id=1,
                memory_type="test",
                key="debug_test2",
                value="test value 2"
            )
            print(f"   Memory module save result: {success}")
        except Exception as e:
            print(f"   ❌ Memory module save failed: {e}")
            
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_memory_issue())

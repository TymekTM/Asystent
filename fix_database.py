#!/usr/bin/env python3
"""
Debug database path and initialize properly
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server path
sys.path.insert(0, str(Path(__file__).parent / "server"))

async def fix_database_issue():
    """Fix database path issue and ensure user exists."""
    print("🔧 Fixing Database Path Issues")
    print("=" * 50)
    
    try:
        from database_manager import get_database_manager
        
        # Initialize database manager properly
        print("1. Initializing database manager...")
        db_manager = get_database_manager()
        print(f"   Database path: {db_manager.db_path}")
          # Create a test user directly
        print("\n2. Creating test user...")
        try:
            user_id = db_manager.create_user(
                username="test_user",
                email="test@example.com"
            )
            print(f"   ✅ Created user: ID={user_id}")
        except Exception as e:
            print(f"   ⚠️ User creation failed (might already exist): {e}")
              # Check users again
        print("\n3. Checking users...")
        users = await db_manager.get_all_users()
        print(f"   Found {len(users)} users in database")
        for user in users:
            print(f"   User ID: {user['id']}, Username: {user['username']}")
              # Now test memory save
        print("\n4. Testing memory save...")
        if users:
            user_id = users[0]['id']
            try:
                db_manager.save_memory_context(
                    user_id=user_id,
                    context_type="test",
                    key_name="debug_test",
                    value="test value",
                    metadata={}
                )
                print("   ✅ Memory save successful!")
                
                # Test memory retrieval
                memories = db_manager.get_memory_context(
                    user_id=user_id,
                    context_type="test",
                    key_name="debug_test"
                )
                print(f"   ✅ Retrieved {len(memories)} memories")
                
            except Exception as e:
                print(f"   ❌ Memory operation failed: {e}")
        else:
            print("   ❌ No users found to test with")
            
    except Exception as e:
        print(f"❌ Error during fixing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_database_issue())

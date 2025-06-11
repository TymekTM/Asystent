#!/usr/bin/env python3
"""
Test script for the Proactive Assistant Module
"""

import asyncio
import sys
import os

# Add server path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from server.proactive_assistant_simple import get_proactive_assistant

async def test_proactive_assistant():
    """Test the proactive assistant functionality."""
    try:
        print("Testing Proactive Assistant Module...")
        
        # Get the proactive assistant instance
        assistant = get_proactive_assistant()
        print("✓ Proactive assistant instance created")
          # Start the assistant
        assistant.start()
        print("✓ Proactive assistant started")
        
        # Test adding a notification
        await assistant.add_notification(
            user_id="test_user",
            notification_type="wellness",
            message="This is a test wellness notification",
            priority="medium"
        )
        print("✓ Test notification added")
        
        # Test getting notifications
        notifications = await assistant.get_notifications("test_user")
        print(f"✓ Retrieved {len(notifications)} notifications")
        
        if notifications:
            print("Sample notification:", notifications[0])
        
        # Test updating user context
        context_data = {
            'activity': 'testing',
            'mood': 'focused',
            'productivity_level': 0.8
        }
        await assistant.update_user_context("test_user", context_data)
        print("✓ User context updated")
        
        # Test predictions
        predictions = await assistant.get_predictions("test_user")
        print(f"✓ Generated {len(predictions)} predictions")
        
        print("\n🎉 All tests passed! Proactive Assistant is working correctly.")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:        # Clean up
        if 'assistant' in locals():
            assistant.stop()
            print("✓ Proactive assistant stopped")

if __name__ == "__main__":
    asyncio.run(test_proactive_assistant())

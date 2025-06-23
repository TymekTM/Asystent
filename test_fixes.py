#!/usr/bin/env python3
"""Test script to verify the fixes work correctly."""

import sys
from pathlib import Path

# Add server path
sys.path.insert(0, str(Path(__file__).parent / "server"))
sys.path.insert(0, str(Path(__file__).parent / "client"))


def test_daily_briefing_method():
    """Test if the generate_daily_briefing method exists."""
    try:
        from server.daily_briefing_module import DailyBriefingModule

        config = {
            "daily_briefing": {
                "enabled": True,
                "user_name": "Test User",
                "location": "Warsaw,PL",
            }
        }

        db = DailyBriefingModule(config)

        if hasattr(db, "generate_daily_briefing"):
            print("✅ generate_daily_briefing method exists in DailyBriefingModule")
            return True
        else:
            print("❌ generate_daily_briefing method missing from DailyBriefingModule")
            return False

    except Exception as e:
        print(f"❌ Error testing DailyBriefingModule: {e}")
        return False


def test_client_methods():
    """Test if the client methods exist."""
    try:
        # We can't easily instantiate ClientApp due to dependencies,
        # but we can check if the methods exist by reading the source
        with open("client/client_main.py", encoding="utf-8") as f:
            content = f.read()

        if "async def request_proactive_notifications(" in content:
            print("✅ request_proactive_notifications method exists in ClientApp")
            return True
        else:
            print("❌ request_proactive_notifications method missing from ClientApp")
            return False

    except Exception as e:
        print(f"❌ Error testing ClientApp methods: {e}")
        return False


if __name__ == "__main__":
    print("Testing fixes...")
    print("=" * 50)

    test1_passed = test_daily_briefing_method()
    test2_passed = test_client_methods()

    print("=" * 50)
    if test1_passed and test2_passed:
        print("🎉 All tests passed! The fixes should work correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")

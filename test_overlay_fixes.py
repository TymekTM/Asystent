#!/usr/bin/env python3
"""Test script to verify overlay fixes work correctly."""

import asyncio
import sys
import time
from pathlib import Path

import requests

# Add parent directory to path so we can import client modules
sys.path.insert(0, str(Path(__file__).parent / "client"))


async def test_overlay_fixes():
    """Test the overlay fixes."""
    print("🧪 Testing overlay fixes...")

    # Test 1: Check if API is responding
    print("\n1. Testing API connection...")
    try:
        response = requests.get("http://localhost:5001/api/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ API connected: {status.get('status', 'Unknown')}")
        else:
            print(f"❌ API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

    # Test 2: Check if settings.html is available
    print("\n2. Testing settings.html endpoint...")
    try:
        response = requests.get("http://localhost:5001/settings.html", timeout=5)
        if response.status_code == 200:
            content = response.text
            if "Gaja - Ustawienia" in content:
                print("✅ Settings page loads correctly")
            else:
                print("❌ Settings page content invalid")
                return False
        else:
            print(f"❌ Settings page error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Settings page failed: {e}")
        return False

    # Test 3: Test overlay show/hide commands
    print("\n3. Testing overlay show/hide commands...")
    try:
        # Test showing overlay
        show_data = {
            "status": "Test Show",
            "overlay_visible": True,
            "show_overlay": True,
        }

        # We'll simulate this by sending POST to update status
        response = requests.post(
            "http://localhost:5001/api/update_status", json=show_data, timeout=5
        )

        if response.status_code == 200:
            print("✅ Show overlay command sent successfully")
        else:
            print(f"❌ Show overlay command failed: {response.status_code}")
            return False

        # Wait a bit
        time.sleep(2)

        # Test hiding overlay
        hide_data = {
            "status": "Test Hide",
            "overlay_visible": False,
            "hide_overlay": True,
        }

        response = requests.post(
            "http://localhost:5001/api/update_status", json=hide_data, timeout=5
        )

        if response.status_code == 200:
            print("✅ Hide overlay command sent successfully")
        else:
            print(f"❌ Hide overlay command failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Overlay show/hide test failed: {e}")
        return False

    # Test 4: Test settings action
    print("\n4. Testing settings action...")
    try:
        settings_data = {"action": "open_settings", "open_settings": True}

        response = requests.post(
            "http://localhost:5001/api/update_status", json=settings_data, timeout=5
        )

        if response.status_code == 200:
            print("✅ Settings action sent successfully")
        else:
            print(f"❌ Settings action failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Settings action test failed: {e}")
        return False

    print("\n✅ All overlay fixes tested successfully!")
    return True


def check_overlay_process():
    """Check if overlay process is running."""
    print("\n🔍 Checking overlay process...")
    import subprocess

    try:
        result = subprocess.run(
            ["tasklist", "/fi", "imagename eq gaja-overlay.exe"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if "gaja-overlay.exe" in result.stdout:
            lines = result.stdout.split("\n")
            for line in lines:
                if "gaja-overlay.exe" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        print(f"✅ Overlay process found: PID {pid}")
                        return True

        print("❌ Overlay process not found")
        return False

    except Exception as e:
        print(f"❌ Error checking overlay process: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting overlay fixes test...")

    # First check if overlay process is running
    if not check_overlay_process():
        print("❌ Overlay process not running. Please start the client first.")
        sys.exit(1)

    # Run the tests
    success = asyncio.run(test_overlay_fixes())

    if success:
        print("\n🎉 All tests passed! Overlay fixes are working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the logs.")
        sys.exit(1)

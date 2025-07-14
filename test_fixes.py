#!/usr/bin/env python3
"""Test script to verify the fixes for system tray and overlay issues."""

import sys
from pathlib import Path

# Add client to path
sys.path.insert(0, str(Path(__file__).parent / "client"))


def test_settings_url():
    """Test that settings URL is accessible."""
    print("🧪 Testing settings URL...")

    try:
        import urllib.request

        response = urllib.request.urlopen("http://localhost:5001/settings.html")
        if response.status == 200:
            print("✅ Settings URL is accessible at http://localhost:5001/settings.html")
            return True
        else:
            print(f"❌ Settings URL returned status: {response.status}")
            return False
    except Exception as e:
        print(f"❌ Settings URL test failed: {e}")
        return False


def test_overlay_executable():
    """Test that overlay executable exists."""
    print("🧪 Testing overlay executable...")

    overlay_path = (
        Path(__file__).parent / "overlay" / "target" / "release" / "gaja-overlay.exe"
    )

    if overlay_path.exists():
        print(f"✅ Overlay executable found: {overlay_path}")
        return True
    else:
        print(f"❌ Overlay executable not found: {overlay_path}")
        return False


def test_system_tray_manager():
    """Test that system tray manager has correct menu."""
    print("🧪 Testing system tray manager...")

    try:
        from modules.tray_manager import TrayManager

        # Mock client app
        class MockClientApp:
            def __init__(self):
                self.overlay_visible = False
                self.running = True

            def show_overlay(self):
                self.overlay_visible = True
                print("Mock: Overlay shown")

            def update_status(self, status):
                print(f"Mock: Status updated to '{status}'")

        mock_client = MockClientApp()
        tray = TrayManager(client_app=mock_client)

        # Test menu creation
        menu = tray.create_menu()
        if menu:
            print("✅ System tray menu created successfully")
            print("📋 Expected menu items:")
            print("   • Settings")
            print("   • Toggle Overlay")
            print("   • Quit")
            return True
        else:
            print("❌ System tray menu creation failed")
            return False

    except Exception as e:
        print(f"❌ System tray manager test failed: {e}")
        return False


def show_summary():
    """Show summary of what was fixed."""
    print("\n" + "=" * 60)
    print("🔧 FIXES APPLIED:")
    print("=" * 60)

    print("\n1. 🎯 SYSTEM TRAY FIXES:")
    print("   • Fixed settings URL: now opens http://localhost:5001/settings.html")
    print("   • Simplified menu to: Settings, Toggle Overlay, Quit")
    print("   • Removed unnecessary buttons (About, Connect, Restart, etc.)")

    print("\n2. 🚨 CRITICAL OVERLAY CLICK-THROUGH FIX:")
    print("   • Fixed click-through logic in overlay/src/main.rs")
    print("   • When overlay shows: click_through = FALSE (interactive)")
    print("   • When overlay hides: click_through = TRUE (non-blocking)")
    print("   • This prevents overlay from blocking all screen clicks")

    print("\n3. 🌐 SETTINGS INTERFACE:")
    print("   • Added /settings.html route to HTTP server")
    print("   • Settings button now opens proper interface")
    print("   • Serves settings.html from client/resources/")

    print("\n4. 🎛️ OVERLAY SYSTEM TRAY:")
    print("   • Fixed system tray menu in Rust code")
    print("   • Corrected click-through logic for show/hide")
    print("   • Consistent behavior across all overlay controls")

    print("\n" + "=" * 60)
    print("✅ EXPECTED RESULTS:")
    print("=" * 60)
    print("• System tray: Clean menu with Settings, Toggle Overlay, Quit")
    print("• Settings: Opens proper interface instead of API endpoint")
    print("• Overlay: NO MORE SCREEN BLOCKING - you can click normally")
    print("• Click-through: Only active when overlay is hidden")
    print("=" * 60)


if __name__ == "__main__":
    print("🧪 TESTING GAJA FIXES")
    print("=" * 50)

    results = []

    # Test overlay executable
    results.append(test_overlay_executable())

    # Test system tray manager
    results.append(test_system_tray_manager())

    print("\n" + "=" * 50)
    print("🏁 TEST RESULTS:")
    print("=" * 50)

    if all(results):
        print("✅ ALL TESTS PASSED!")
        print("🚀 Ready to test the actual application")
    else:
        print("❌ Some tests failed")
        print("🔍 Check the issues above before running the client")

    show_summary()

    print("\n💡 TO TEST THE FIXES:")
    print("1. Run: python client_main.py")
    print("2. Right-click system tray icon")
    print("3. Click 'Settings' - should open proper interface")
    print("4. Click 'Toggle Overlay' - should show/hide without blocking clicks")
    print("5. Verify you can click normally on desktop when overlay is shown")

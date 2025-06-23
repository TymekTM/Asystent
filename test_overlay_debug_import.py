#!/usr/bin/env python3
"""Quick test script for overlay debug tools."""

try:
    import overlay_debug_tools

    print("✅ SUCCESS: Overlay Debug Tools imports correctly")
    print(f"   Module file: {overlay_debug_tools.__file__}")

    # Test that main classes exist
    assert hasattr(overlay_debug_tools, "OverlayDebugToolsGUI")
    print("✅ SUCCESS: Main GUI class exists")

    print("\n🚀 Overlay Debug Tools is ready to use!")
    print("   To run: python overlay_debug_tools.py")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback

    traceback.print_exc()

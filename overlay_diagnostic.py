#!/usr/bin/env python3
"""Overlay Visibility Diagnostic Tool Diagnozuje problemy z widocznością overlay i
próbuje je naprawić."""

import asyncio

import aiohttp


async def diagnose_overlay():
    """Diagnozuje problemy z overlay."""
    print("🔍 GAJA Overlay Visibility Diagnostics")
    print("=" * 50)

    base_url = "http://localhost:5001"

    async with aiohttp.ClientSession() as session:
        # Test 1: Sprawdź podstawowe API
        print("1. Testing basic API connectivity...")
        try:
            async with session.get(f"{base_url}/api/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(
                        f"   ✅ API works - Client status: {data.get('status', 'unknown')}"
                    )
                    print(f"   📊 Is listening: {data.get('is_listening', False)}")
                    print(f"   📊 Is speaking: {data.get('is_speaking', False)}")
                    print(f"   📊 Overlay visible: {data.get('overlay_visible', False)}")
                else:
                    print(f"   ❌ API error: {response.status}")
                    return
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            return

        print()

        # Test 2: Sprawdź overlay status
        print("2. Checking overlay specific status...")
        try:
            async with session.get(f"{base_url}/api/overlay/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   📊 Overlay visible: {data.get('overlay_visible', False)}")
                    print(f"   📊 Current text: '{data.get('current_text', '')}'")
                    print(f"   📊 Status: {data.get('status', 'unknown')}")
                else:
                    print(f"   ❌ Overlay status error: {response.status}")
        except Exception as e:
            print(f"   ❌ Overlay status error: {e}")

        print()

        # Test 3: Wymuś pokazanie overlay
        print("3. Forcing overlay to show...")
        try:
            async with session.get(f"{base_url}/api/overlay/show") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Show command sent: {data}")
                    await asyncio.sleep(1)  # Wait for command to process
                else:
                    print(f"   ❌ Show command failed: {response.status}")
        except Exception as e:
            print(f"   ❌ Show command error: {e}")

        print()

        # Test 4: Wyślij wyraźny tekst
        print("4. Sending visible test content...")
        test_texts = [
            "🚨 OVERLAY TEST - SHOULD BE VISIBLE! 🚨",
            "HELLO FROM DIAGNOSTIC TOOL",
            "🔴🔴🔴 RED ALERT TEST 🔴🔴🔴",
        ]

        for i, text in enumerate(test_texts, 1):
            try:
                url = f"{base_url}/api/test/wakeword?query={text}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Test {i}: Sent '{text}'")
                        await asyncio.sleep(2)  # Wait between tests
                    else:
                        print(f"   ❌ Test {i} failed: {response.status}")
            except Exception as e:
                print(f"   ❌ Test {i} error: {e}")

        print()

        # Test 5: Sprawdź końcowy status
        print("5. Final status check...")
        try:
            async with session.get(f"{base_url}/api/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(
                        f"   📊 Final overlay visible: {data.get('overlay_visible', False)}"
                    )
                    print(f"   📊 Final text: '{data.get('text', '')}'")
                    print(f"   📊 Show overlay flag: {data.get('show_overlay', False)}")
        except Exception as e:
            print(f"   ❌ Final status error: {e}")

        print()
        print("🎯 DIAGNOSTIC RECOMMENDATIONS:")
        print("-" * 30)
        print("If overlay is still not visible, try:")
        print("1. Check if overlay process is running: Get-Process *gaja*")
        print("2. Look for overlay window in taskbar or Alt+Tab")
        print("3. Check Windows settings for transparency/focus")
        print("4. Try restarting overlay: kill gaja-overlay.exe and restart client")
        print("5. Check monitor configuration (overlay may be on wrong screen)")
        print("6. Verify overlay executable path in client logs")


def check_overlay_process():
    """Sprawdź czy proces overlay działa."""
    import subprocess

    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-Process | Where-Object { $_.ProcessName -like '*gaja-overlay*' } | Format-Table Id, ProcessName, MainWindowTitle -AutoSize",
            ],
            capture_output=True,
            text=True,
        )
        print("📋 Overlay Process Info:")
        print(result.stdout)
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error checking process: {e}")


if __name__ == "__main__":
    print("Starting overlay diagnostics...")
    print()

    # Sprawdź procesy
    check_overlay_process()
    print()

    # Uruchom async diagnostykę
    try:
        asyncio.run(diagnose_overlay())
    except KeyboardInterrupt:
        print("\nDiagnostics interrupted by user")
    except Exception as e:
        print(f"Diagnostics error: {e}")

    print("\n🏁 Diagnostics complete!")
    print("If overlay is still not visible, the issue may be:")
    print("- Window positioning (off-screen)")
    print("- Graphics driver issues")
    print("- Windows compositor problems")
    print("- DPI scaling issues")
    print("- Focus/z-order problems")

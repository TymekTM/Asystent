#!/usr/bin/env python3
"""Quick test for fixed client issues."""

import subprocess
import sys
from pathlib import Path

import requests

# Add client path to sys.path
sys.path.insert(0, str(Path(__file__).parent / "client"))

from loguru import logger


def test_settings_page():
    """Test settings page accessibility."""
    logger.info("🧪 Testing settings page...")

    ports = [5001, 5000]
    for port in ports:
        try:
            url = f"http://localhost:{port}/settings.html"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                logger.info(f"✅ Settings page accessible at {url}")
                logger.info(f"   Content length: {len(response.content)} bytes")
                return True
            else:
                logger.warning(
                    f"❌ Settings page returned {response.status_code} at {url}"
                )
        except requests.exceptions.ConnectionError:
            logger.warning(f"❌ Cannot connect to port {port}")
        except Exception as e:
            logger.error(f"❌ Error testing port {port}: {e}")

    return False


def test_api_endpoints():
    """Test API endpoints."""
    logger.info("🧪 Testing API endpoints...")

    endpoints = [
        "/api/status",
        "/api/audio_devices",
        "/api/test_microphone",
        "/api/test_tts",
        "/api/connection_status",
        "/api/current_settings",
    ]

    ports = [5001, 5000]
    working_port = None

    # Find working port
    for port in ports:
        try:
            url = f"http://localhost:{port}/api/status"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                working_port = port
                logger.info(f"✅ Found working HTTP server on port {port}")
                break
        except:
            continue

    if not working_port:
        logger.error("❌ No working HTTP server found")
        return False

    # Test each endpoint
    results = {}
    for endpoint in endpoints:
        try:
            url = f"http://localhost:{working_port}{endpoint}"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                results[endpoint] = "✅ PASS"
                logger.info(f"✅ {endpoint} - OK")
            else:
                results[endpoint] = f"❌ FAIL ({response.status_code})"
                logger.warning(f"❌ {endpoint} - {response.status_code}")
        except Exception as e:
            results[endpoint] = f"❌ ERROR ({str(e)})"
            logger.error(f"❌ {endpoint} - Error: {e}")

    return results


def test_overlay_process():
    """Test overlay process."""
    logger.info("🧪 Testing overlay process...")

    try:
        # Check if overlay process is running
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq gaja-overlay.exe"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if "gaja-overlay.exe" in result.stdout:
            logger.info("✅ Overlay process is running")
            return True
        else:
            logger.warning("❌ Overlay process not found")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking overlay process: {e}")
        return False


def test_tts_module():
    """Test TTS module directly."""
    logger.info("🧪 Testing TTS module...")

    try:
        from audio_modules.tts_module import TTSModule

        tts = TTSModule()
        logger.info("✅ TTS module created successfully")

        # Test if we can at least create the module
        if hasattr(tts, "speak"):
            logger.info("✅ TTS module has speak method")
        else:
            logger.warning("❌ TTS module missing speak method")

        return True
    except Exception as e:
        logger.error(f"❌ TTS module test failed: {e}")
        return False


def main():
    """Main test function."""
    logger.info("🧪 Quick Client Test")
    logger.info("=" * 50)

    results = {}

    # Test 1: Settings page
    results["settings_page"] = test_settings_page()

    # Test 2: API endpoints
    results["api_endpoints"] = test_api_endpoints()

    # Test 3: Overlay process
    results["overlay_process"] = test_overlay_process()

    # Test 4: TTS module
    results["tts_module"] = test_tts_module()

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("🧪 TEST SUMMARY")
    logger.info("=" * 50)

    passed = sum(1 for result in results.values() if result is True)
    total = len(results)

    logger.info(f"📊 Passed: {passed}/{total}")

    for test_name, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL"
        logger.info(f"  {status} {test_name}")

    # Instructions
    logger.info("\n📋 Manual Test Instructions:")
    logger.info("1. Start client: python client/client_main.py")
    logger.info("2. Open settings: http://localhost:5001/settings.html")
    logger.info("3. Test system tray -> Settings")
    logger.info("4. Test overlay behavior (should be click-through)")
    logger.info("5. Test daily briefing TTS")


if __name__ == "__main__":
    main()

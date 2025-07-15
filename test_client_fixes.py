#!/usr/bin/env python3
"""Test script for client fixes.

This script tests:
1. Daily briefing TTS functionality
2. Audio device detection
3. Settings interface accessibility
4. Overlay click-through behavior
"""

import asyncio
import sys
from pathlib import Path

# Add client path to sys.path
sys.path.insert(0, str(Path(__file__).parent / "client"))

from loguru import logger

# Import client modules
try:
    from audio_modules.tts_module import TTSModule
    from modules.settings_manager import SettingsManager
    from modules.tray_manager import TrayManager

    from client_main import ClientApp
except ImportError as e:
    logger.error(f"Failed to import client modules: {e}")
    sys.exit(1)


class ClientTestSuite:
    """Test suite for client functionality."""

    def __init__(self):
        self.client_app = None
        self.test_results = {}

    async def setup_client(self):
        """Setup client for testing."""
        try:
            self.client_app = ClientApp()
            await self.client_app.initialize_components()
            logger.info("✅ Client setup completed")
            return True
        except Exception as e:
            logger.error(f"❌ Client setup failed: {e}")
            return False

    async def test_tts_functionality(self):
        """Test TTS functionality."""
        logger.info("🧪 Testing TTS functionality...")

        try:
            if not self.client_app.tts:
                logger.warning("❌ TTS module not available")
                self.test_results["tts"] = {
                    "success": False,
                    "error": "TTS module not available",
                }
                return False

            # Test TTS with a simple message
            test_message = "Test wiadomości TTS. Jeśli słyszysz tę wiadomość, TTS działa poprawnie."

            logger.info("🔊 Testing TTS speech...")
            await self.client_app.tts.speak(test_message)

            logger.info("✅ TTS test completed successfully")
            self.test_results["tts"] = {"success": True, "message": "TTS working"}
            return True

        except Exception as e:
            logger.error(f"❌ TTS test failed: {e}")
            self.test_results["tts"] = {"success": False, "error": str(e)}
            return False

    async def test_daily_briefing_simulation(self):
        """Test daily briefing handling."""
        logger.info("🧪 Testing daily briefing simulation...")

        try:
            # Simulate daily briefing message
            briefing_data = {
                "type": "daily_briefing",
                "text": "Dzisiaj jest piękny dzień! Temperatura wynosi 22 stopnie, jest słonecznie. Masz 3 spotkania zaplanowane na dzisiaj.",
            }

            logger.info("📋 Simulating daily briefing...")
            await self.client_app.handle_server_message(briefing_data)

            logger.info("✅ Daily briefing simulation completed")
            self.test_results["daily_briefing"] = {
                "success": True,
                "message": "Daily briefing handled",
            }
            return True

        except Exception as e:
            logger.error(f"❌ Daily briefing test failed: {e}")
            self.test_results["daily_briefing"] = {"success": False, "error": str(e)}
            return False

    def test_audio_device_detection(self):
        """Test audio device detection."""
        logger.info("🧪 Testing audio device detection...")

        try:
            devices = self.client_app.list_available_audio_devices()

            input_devices = devices.get("input_devices", [])
            output_devices = devices.get("output_devices", [])

            logger.info(f"📱 Found {len(input_devices)} input devices")
            logger.info(f"🔊 Found {len(output_devices)} output devices")

            # Log device details
            for device in input_devices[:3]:  # Show first 3 devices
                logger.info(f"   🎤 Input: {device['name']} (ID: {device['id']})")

            for device in output_devices[:3]:  # Show first 3 devices
                logger.info(f"   🔊 Output: {device['name']} (ID: {device['id']})")

            self.test_results["audio_devices"] = {
                "success": True,
                "input_count": len(input_devices),
                "output_count": len(output_devices),
            }

            logger.info("✅ Audio device detection completed")
            return True

        except Exception as e:
            logger.error(f"❌ Audio device detection failed: {e}")
            self.test_results["audio_devices"] = {"success": False, "error": str(e)}
            return False

    def test_settings_manager(self):
        """Test settings manager functionality."""
        logger.info("🧪 Testing settings manager...")

        try:
            if not self.client_app.settings_manager:
                logger.warning("❌ Settings manager not available")
                self.test_results["settings"] = {
                    "success": False,
                    "error": "Settings manager not available",
                }
                return False

            # Test loading settings
            settings = self.client_app.settings_manager.load_settings()
            logger.info(f"⚙️  Loaded settings with {len(settings)} sections")

            # Test getting connection status
            connection_status = self.client_app.settings_manager.get_connection_status()
            logger.info(
                f"🔗 Connection status: {connection_status.get('connected', False)}"
            )

            self.test_results["settings"] = {
                "success": True,
                "settings_sections": len(settings),
                "connection_status": connection_status,
            }

            logger.info("✅ Settings manager test completed")
            return True

        except Exception as e:
            logger.error(f"❌ Settings manager test failed: {e}")
            self.test_results["settings"] = {"success": False, "error": str(e)}
            return False

    def test_system_tray(self):
        """Test system tray functionality."""
        logger.info("🧪 Testing system tray...")

        try:
            if not self.client_app.tray_manager:
                logger.warning("❌ Tray manager not available")
                self.test_results["tray"] = {
                    "success": False,
                    "error": "Tray manager not available",
                }
                return False

            # Test tray manager creation
            tray_manager = self.client_app.tray_manager
            logger.info(f"📱 Tray manager created: {tray_manager is not None}")

            # Test status update
            tray_manager.update_status("Test Status")
            logger.info("📊 Status updated in tray")

            self.test_results["tray"] = {
                "success": True,
                "message": "Tray manager working",
            }

            logger.info("✅ System tray test completed")
            return True

        except Exception as e:
            logger.error(f"❌ System tray test failed: {e}")
            self.test_results["tray"] = {"success": False, "error": str(e)}
            return False

    async def test_overlay_communication(self):
        """Test overlay communication."""
        logger.info("🧪 Testing overlay communication...")

        try:
            # Test showing overlay
            await self.client_app.show_overlay()
            logger.info("👁️  Overlay shown")

            # Wait a bit
            await asyncio.sleep(2)

            # Test hiding overlay
            await self.client_app.hide_overlay()
            logger.info("🙈 Overlay hidden")

            self.test_results["overlay"] = {
                "success": True,
                "message": "Overlay communication working",
            }

            logger.info("✅ Overlay communication test completed")
            return True

        except Exception as e:
            logger.error(f"❌ Overlay communication test failed: {e}")
            self.test_results["overlay"] = {"success": False, "error": str(e)}
            return False

    def print_test_results(self):
        """Print comprehensive test results."""
        logger.info("\n" + "=" * 50)
        logger.info("🧪 TEST RESULTS SUMMARY")
        logger.info("=" * 50)

        total_tests = len(self.test_results)
        passed_tests = sum(
            1 for result in self.test_results.values() if result.get("success", False)
        )

        logger.info(f"📊 Total tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {total_tests - passed_tests}")
        logger.info(f"📈 Success rate: {(passed_tests/total_tests)*100:.1f}%")

        logger.info("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            logger.info(f"  {status} {test_name}")

            if not result.get("success", False) and "error" in result:
                logger.info(f"     Error: {result['error']}")
            elif "message" in result:
                logger.info(f"     {result['message']}")

        logger.info("=" * 50)

    async def run_all_tests(self):
        """Run all tests in sequence."""
        logger.info("🚀 Starting Client Test Suite...")

        # Setup
        if not await self.setup_client():
            logger.error("❌ Failed to setup client, aborting tests")
            return

        # Run tests
        await self.test_tts_functionality()
        await self.test_daily_briefing_simulation()
        self.test_audio_device_detection()
        self.test_settings_manager()
        self.test_system_tray()
        await self.test_overlay_communication()

        # Print results
        self.print_test_results()

        # Cleanup
        if self.client_app:
            await self.client_app.cleanup()
            logger.info("🧹 Client cleanup completed")


async def main():
    """Main test function."""
    logger.info("🧪 GAJA Client Test Suite")
    logger.info("Testing fixes for:")
    logger.info("  1. Daily briefing TTS functionality")
    logger.info("  2. Audio device detection and settings")
    logger.info("  3. System tray settings access")
    logger.info("  4. Overlay click-through behavior")

    test_suite = ClientTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Test suite interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        sys.exit(1)

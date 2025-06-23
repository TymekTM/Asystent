#!/usr/bin/env python3
"""
GAJA Assistant - Overlay Input Fix Test Suite
Test suite to verify overlay input blocking fixes work correctly.

Following AGENTS.md guidelines:
- Async-first architecture
- Comprehensive test coverage
- Clear logging and error handling
- Modular design
"""

import asyncio
import json
import logging
import sys
from typing import Any

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OverlayInputFixTests:
    """Test suite for overlay input fix functionality."""

    def __init__(self):
        """Initialize test suite."""
        self.overlay_api_base = "http://localhost:5001"
        self.test_results: list[dict[str, Any]] = []

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all overlay input fix tests.

        Returns:
            Dict with test results
        """
        logger.info("Starting overlay input fix test suite...")

        test_methods = [
            self.test_overlay_module_import,
            self.test_overlay_window_detection,
            self.test_click_through_application,
            self.test_interactive_mode_switching,
            self.test_overlay_api_connectivity,
            self.test_window_properties_validation,
            self.test_fix_persistence,
            self.test_error_handling,
        ]

        total_tests = len(test_methods)
        passed_tests = 0

        for test_method in test_methods:
            try:
                test_name = test_method.__name__
                logger.info(f"Running test: {test_name}")

                result = await test_method()

                if result.get("passed", False):
                    passed_tests += 1
                    logger.info(f"✅ {test_name} - PASSED")
                else:
                    logger.error(
                        f"❌ {test_name} - FAILED: {result.get('error', 'Unknown error')}"
                    )

                self.test_results.append(
                    {
                        "test_name": test_name,
                        "passed": result.get("passed", False),
                        "details": result,
                    }
                )

            except Exception as e:
                logger.error(f"❌ {test_method.__name__} - EXCEPTION: {e}")
                self.test_results.append(
                    {
                        "test_name": test_method.__name__,
                        "passed": False,
                        "details": {"error": str(e), "exception": True},
                    }
                )

        # Generate summary
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests) * 100
            if total_tests > 0
            else 0,
            "test_results": self.test_results,
            "overall_status": "PASSED" if passed_tests == total_tests else "FAILED",
        }

        logger.info(
            f"Test suite completed: {passed_tests}/{total_tests} tests passed ({summary['success_rate']:.1f}%)"
        )
        return summary

    async def test_overlay_module_import(self) -> dict[str, Any]:
        """Test if overlay_input_fix module can be imported."""
        try:
            from overlay_input_fix import (
                OverlayInputManager,
                fix_overlay_input_blocking,
            )

            return {"passed": True, "message": "Module imported successfully"}
        except ImportError as e:
            return {"passed": False, "error": f"Module import failed: {e}"}

    async def test_overlay_window_detection(self) -> dict[str, Any]:
        """Test overlay window detection functionality."""
        try:
            from overlay_input_fix import OverlayInputManager

            manager = OverlayInputManager()
            hwnd = await manager._find_overlay_window()

            if hwnd:
                return {
                    "passed": True,
                    "message": f"Overlay window detected with handle: {hwnd}",
                }
            else:
                return {"passed": False, "error": "No overlay window found"}

        except Exception as e:
            return {"passed": False, "error": f"Window detection failed: {e}"}

    async def test_click_through_application(self) -> dict[str, Any]:
        """Test click-through fix application."""
        try:
            from overlay_input_fix import OverlayInputManager

            manager = OverlayInputManager()
            if await manager.initialize():
                # Test applying click-through
                await manager._apply_click_through_fix()

                # Verify window properties
                diagnostics = await manager.test_overlay_behavior()
                window_props = diagnostics.get("window_properties", {})

                await manager.cleanup()

                # Check if transparent flag is set
                has_transparent = window_props.get("has_transparent", False)
                has_layered = window_props.get("has_layered", False)

                if has_transparent and has_layered:
                    return {
                        "passed": True,
                        "message": "Click-through successfully applied",
                        "window_properties": window_props,
                    }
                else:
                    return {
                        "passed": False,
                        "error": f"Click-through not properly applied. Transparent: {has_transparent}, Layered: {has_layered}",
                        "window_properties": window_props,
                    }
            else:
                return {
                    "passed": False,
                    "error": "Failed to initialize overlay manager",
                }

        except Exception as e:
            return {"passed": False, "error": f"Click-through application failed: {e}"}

    async def test_interactive_mode_switching(self) -> dict[str, Any]:
        """Test switching between interactive and click-through modes."""
        try:
            from overlay_input_fix import OverlayInputManager

            manager = OverlayInputManager()
            if await manager.initialize():
                # Test switching to interactive mode
                await manager.set_interactive_mode(True)
                interactive_result = await manager.test_overlay_behavior()

                # Test switching back to click-through mode
                await manager.set_interactive_mode(False)
                clickthrough_result = await manager.test_overlay_behavior()

                await manager.cleanup()

                # Verify mode switching worked
                interactive_transparent = interactive_result.get(
                    "window_properties", {}
                ).get("has_transparent", True)
                clickthrough_transparent = clickthrough_result.get(
                    "window_properties", {}
                ).get("has_transparent", False)

                if not interactive_transparent and clickthrough_transparent:
                    return {
                        "passed": True,
                        "message": "Interactive mode switching works correctly",
                        "interactive_props": interactive_result.get(
                            "window_properties"
                        ),
                        "clickthrough_props": clickthrough_result.get(
                            "window_properties"
                        ),
                    }
                else:
                    return {
                        "passed": False,
                        "error": "Interactive mode switching failed",
                        "interactive_transparent": interactive_transparent,
                        "clickthrough_transparent": clickthrough_transparent,
                    }
            else:
                return {
                    "passed": False,
                    "error": "Failed to initialize overlay manager",
                }

        except Exception as e:
            return {
                "passed": False,
                "error": f"Interactive mode switching test failed: {e}",
            }

    async def test_overlay_api_connectivity(self) -> dict[str, Any]:
        """Test connectivity to overlay API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.overlay_api_base}/api/status"
                ) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        return {
                            "passed": True,
                            "message": "Overlay API is accessible",
                            "status_data": status_data,
                        }
                    else:
                        return {
                            "passed": False,
                            "error": f"Overlay API returned status {response.status}",
                        }
        except Exception as e:
            return {"passed": False, "error": f"API connectivity test failed: {e}"}

    async def test_window_properties_validation(self) -> dict[str, Any]:
        """Test window properties validation."""
        try:
            from overlay_input_fix import OverlayInputManager

            manager = OverlayInputManager()
            if await manager.initialize():
                diagnostics = await manager.test_overlay_behavior()
                window_props = diagnostics.get("window_properties", {})

                await manager.cleanup()

                # Validate expected properties
                expected_props = [
                    "has_transparent",
                    "has_layered",
                    "has_noactivate",
                    "raw_style",
                ]
                missing_props = [
                    prop for prop in expected_props if prop not in window_props
                ]

                if not missing_props:
                    return {
                        "passed": True,
                        "message": "All expected window properties present",
                        "window_properties": window_props,
                    }
                else:
                    return {
                        "passed": False,
                        "error": f"Missing window properties: {missing_props}",
                        "window_properties": window_props,
                    }
            else:
                return {
                    "passed": False,
                    "error": "Failed to initialize overlay manager",
                }

        except Exception as e:
            return {
                "passed": False,
                "error": f"Window properties validation failed: {e}",
            }

    async def test_fix_persistence(self) -> dict[str, Any]:
        """Test if fix persists across multiple applications."""
        try:
            from overlay_input_fix import fix_overlay_input_blocking

            # Apply fix multiple times
            results = []
            for i in range(3):
                result = await fix_overlay_input_blocking()
                results.append(result.get("success", False))
                await asyncio.sleep(0.5)  # Short delay between applications

            # Check if all applications succeeded
            if all(results):
                return {
                    "passed": True,
                    "message": "Fix persists across multiple applications",
                    "application_results": results,
                }
            else:
                return {
                    "passed": False,
                    "error": "Fix persistence test failed",
                    "application_results": results,
                }

        except Exception as e:
            return {"passed": False, "error": f"Fix persistence test failed: {e}"}

    async def test_error_handling(self) -> dict[str, Any]:
        """Test error handling in overlay input fix."""
        try:
            from overlay_input_fix import OverlayInputManager

            # Test with invalid window handle
            manager = OverlayInputManager()
            manager.overlay_hwnd = 0  # Invalid handle

            # This should handle the error gracefully
            await manager._apply_click_through_fix()

            # Test with missing session
            manager.client_session = None
            diagnostics = await manager.test_overlay_behavior()

            # Should return error info instead of crashing
            if (
                "overlay_api_error" in diagnostics
                or diagnostics.get("overlay_api_status") == "unknown"
            ):
                return {"passed": True, "message": "Error handling works correctly"}
            else:
                return {
                    "passed": False,
                    "error": "Error handling test did not behave as expected",
                }

        except Exception as e:
            # Unexpected exception means error handling failed
            return {
                "passed": False,
                "error": f"Error handling test failed with exception: {e}",
            }


async def run_manual_test() -> None:
    """Run manual test of overlay behavior."""
    logger.info("=== MANUAL OVERLAY TEST ===")
    logger.info("1. Starting overlay input fix test...")

    try:
        from overlay_input_fix import fix_overlay_input_blocking

        # Apply fix
        result = await fix_overlay_input_blocking()
        logger.info(f"Fix result: {json.dumps(result, indent=2, default=str)}")

        if result.get("success"):
            logger.info("✅ Fix applied successfully!")
            logger.info(
                "2. Please test clicking on desktop, taskbar, and YouTube video"
            )
            logger.info("3. You should be able to interact normally with the desktop")
            logger.info(
                "4. The overlay should only capture input when actively listening"
            )
        else:
            logger.error(f"❌ Fix failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"❌ Manual test failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        # Run manual test
        asyncio.run(run_manual_test())
    else:
        # Run automated test suite
        test_suite = OverlayInputFixTests()
        results = asyncio.run(test_suite.run_all_tests())

        # Print results
        print("\n" + "=" * 50)
        print("OVERLAY INPUT FIX TEST RESULTS")
        print("=" * 50)
        print(f"Total tests: {results['total_tests']}")
        print(f"Passed: {results['passed_tests']}")
        print(f"Failed: {results['failed_tests']}")
        print(f"Success rate: {results['success_rate']:.1f}%")
        print(f"Overall status: {results['overall_status']}")

        if results["failed_tests"] > 0:
            print("\nFailed tests:")
            for test in results["test_results"]:
                if not test["passed"]:
                    print(
                        f"  - {test['test_name']}: {test['details'].get('error', 'Unknown error')}"
                    )

        # Exit with appropriate code
        sys.exit(0 if results["overall_status"] == "PASSED" else 1)

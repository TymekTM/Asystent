#!/usr/bin/env python3
"""
GAJA Assistant - Overlay Rebuild with Taskbar Fix
Complete overlay rebuild to prevent Windows taskbar interference.

Following AGENTS.md guidelines:
- Async-first architecture
- Comprehensive testing
- Clear logging and error handling
- Modular design
"""

import asyncio
import ctypes
import json
import logging
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Any, Optional

import aiohttp
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Windows API constants for taskbar-friendly overlay
GWL_EXSTYLE = -20
GWL_STYLE = -16
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
LWA_ALPHA = 0x00000002
SW_HIDE = 0
SW_SHOWNA = 8
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOOWNERZORDER = 0x0200


class OverlayTaskbarFix:
    """Complete overlay rebuild to fix taskbar interference.

    This class rebuilds the overlay with proper Windows API settings to prevent taskbar
    stealing and ensure desktop compatibility.
    """

    def __init__(self):
        """Initialize the overlay taskbar fix manager."""
        self.overlay_hwnd: Optional[int] = None
        self.client_session: Optional[aiohttp.ClientSession] = None
        self.overlay_api_base = "http://localhost:5001"
        self.overlay_process: Optional[subprocess.Popen] = None

    async def initialize(self) -> bool:
        """Initialize the overlay taskbar fix manager.

        Returns:
            bool: True if initialization successful
        """
        try:
            # Create HTTP session
            self.client_session = aiohttp.ClientSession()

            logger.info("Overlay taskbar fix manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize overlay taskbar fix manager: {e}")
            return False

    async def _find_overlay_windows(self) -> list[int]:
        """Find all overlay window handles.

        Returns:
            List[int]: List of overlay window handles
        """

        def enum_windows_callback(hwnd, lParam):
            """Callback for enumerating windows."""
            window_text = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, window_text, 512)
            window_title = window_text.value.lower()

            class_name = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetClassNameW(hwnd, class_name, 512)
            class_name_str = class_name.value.lower()

            # Look for Gaja overlay windows
            if (
                any(
                    keyword in window_title
                    for keyword in ["gaja", "overlay", "asystent"]
                )
                or "tauri" in class_name_str
            ):
                windows.append(hwnd)
            return True

        windows = []
        enum_windows_proc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
        )
        ctypes.windll.user32.EnumWindows(enum_windows_proc(enum_windows_callback), 0)

        logger.info(f"Found {len(windows)} potential overlay windows")
        return windows

    async def _stop_overlay_processes(self) -> None:
        """Stop all overlay processes."""
        try:
            # Find overlay processes
            overlay_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    proc_info = proc.info
                    if proc_info["name"] and (
                        "gaja-overlay" in proc_info["name"].lower()
                        or "overlay" in proc_info["name"].lower()
                    ):
                        overlay_processes.append(proc.pid)
                    elif proc_info["cmdline"] and any(
                        "overlay" in str(cmd).lower() for cmd in proc_info["cmdline"]
                    ):
                        overlay_processes.append(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Stop processes
            for pid in overlay_processes:
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    logger.info(f"Terminated overlay process: {pid}")

                    # Wait for termination
                    try:
                        process.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        process.kill()
                        logger.info(f"Force killed overlay process: {pid}")

                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning(f"Could not stop process {pid}: {e}")

            # Wait a moment for cleanup
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error stopping overlay processes: {e}")

    async def _apply_taskbar_friendly_settings(self, hwnd: int) -> bool:
        """Apply taskbar-friendly window settings.

        Args:
            hwnd: Window handle

        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Applying taskbar-friendly settings to window {hwnd}")

            # Get current styles
            current_ex_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            current_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_STYLE)

            logger.info(
                f"Current styles - Regular: {hex(current_style)}, Extended: {hex(current_ex_style)}"
            )

            # Create taskbar-friendly extended style
            # Keep: WS_EX_LAYERED (transparency), WS_EX_TRANSPARENT (click-through)
            # Add: WS_EX_NOACTIVATE (no focus), WS_EX_TOOLWINDOW (taskbar exclusion)
            # Remove: Any styles that might interfere with taskbar
            new_ex_style = (
                WS_EX_LAYERED
                | WS_EX_TRANSPARENT
                | WS_EX_NOACTIVATE
                | WS_EX_TOOLWINDOW
                | WS_EX_TOPMOST
            )

            # Create compatible regular style
            # Use WS_POPUP for overlay-style window that doesn't interfere with taskbar
            new_style = WS_POPUP

            # Apply new styles
            ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_STYLE, new_style)
            ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_ex_style)

            # Set layered window attributes for visibility
            alpha_value = 180  # 70% opacity - visible but not intrusive
            result = ctypes.windll.user32.SetLayeredWindowAttributes(
                hwnd,
                0,  # No color key
                alpha_value,  # Alpha value
                LWA_ALPHA,  # Use alpha blending
            )

            if not result:
                logger.warning("Failed to set layered window attributes")

            # Position window carefully to avoid taskbar interference
            # Get screen dimensions
            screen_width = ctypes.windll.user32.GetSystemMetrics(0)
            screen_height = ctypes.windll.user32.GetSystemMetrics(1)

            # Get taskbar height (approximately)
            taskbar_height = 40  # Standard taskbar height
            overlay_height = screen_height - taskbar_height

            # Set window position and size to avoid taskbar
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,  # Position at top-left
                screen_width,
                overlay_height,  # Size excluding taskbar area
                SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_NOOWNERZORDER,
            )

            # Verify final styles
            final_ex_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            final_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_STYLE)

            logger.info(
                f"Final styles - Regular: {hex(final_style)}, Extended: {hex(final_ex_style)}"
            )
            logger.info(
                f"Window positioned: {screen_width}x{overlay_height} (excluding taskbar)"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to apply taskbar-friendly settings: {e}")
            return False

    async def rebuild_overlay(self) -> str:
        """Rebuild overlay with taskbar-friendly configuration.

        Returns:
            str: Result message
        """
        try:
            logger.info("Starting overlay rebuild process...")

            # Step 1: Stop existing overlay processes
            logger.info("Step 1: Stopping existing overlay processes...")
            await self._stop_overlay_processes()

            # Step 2: Find any remaining overlay windows and fix them
            logger.info("Step 2: Finding and fixing overlay windows...")
            overlay_windows = await self._find_overlay_windows()

            fixed_windows = 0
            for hwnd in overlay_windows:
                if await self._apply_taskbar_friendly_settings(hwnd):
                    fixed_windows += 1
                    self.overlay_hwnd = hwnd  # Keep reference to last fixed window

            if fixed_windows > 0:
                logger.info(f"Fixed {fixed_windows} overlay windows")

                # Step 3: Test taskbar functionality
                taskbar_test = await self._test_taskbar_functionality()

                return f"✅ Overlay rebuilt successfully - Fixed {fixed_windows} windows, Taskbar: {taskbar_test}"
            else:
                # Step 3: Try to restart overlay if no windows found
                logger.info(
                    "Step 3: No overlay windows found, attempting to restart..."
                )
                restart_result = await self._restart_overlay_process()

                if restart_result:
                    # Wait for new window and fix it
                    await asyncio.sleep(2)
                    new_windows = await self._find_overlay_windows()

                    for hwnd in new_windows:
                        if await self._apply_taskbar_friendly_settings(hwnd):
                            fixed_windows += 1
                            self.overlay_hwnd = hwnd

                    if fixed_windows > 0:
                        taskbar_test = await self._test_taskbar_functionality()
                        return f"✅ Overlay restarted and rebuilt - Fixed {fixed_windows} windows, Taskbar: {taskbar_test}"

                return (
                    "⚠️ Overlay rebuild completed but no overlay windows found to fix"
                )

        except Exception as e:
            logger.error(f"Overlay rebuild failed: {e}")
            return f"❌ Overlay rebuild failed: {e}"

    async def _restart_overlay_process(self) -> bool:
        """Restart the overlay process.

        Returns:
            bool: True if successful
        """
        try:
            # Look for overlay executable
            overlay_paths = [
                Path("overlay/target/release/gaja-overlay.exe"),
                Path("client/overlay/target/release/gaja-overlay.exe"),
                Path("gaja_client/overlay/target/release/gaja-overlay.exe"),
            ]

            overlay_exe = None
            for path in overlay_paths:
                if path.exists():
                    overlay_exe = path.absolute()
                    break

            if not overlay_exe:
                logger.error("Overlay executable not found")
                return False

            logger.info(f"Starting overlay from: {overlay_exe}")

            # Start overlay process
            self.overlay_process = subprocess.Popen(
                [str(overlay_exe)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            logger.info(f"Overlay process started with PID: {self.overlay_process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to restart overlay process: {e}")
            return False

    async def _test_taskbar_functionality(self) -> str:
        """Test if taskbar functionality is preserved.

        Returns:
            str: Test result
        """
        try:
            # Find taskbar window
            taskbar_hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)

            if taskbar_hwnd:
                # Check if taskbar is visible
                is_visible = bool(ctypes.windll.user32.IsWindowVisible(taskbar_hwnd))

                # Get taskbar position
                rect = wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(taskbar_hwnd, ctypes.byref(rect)):
                    taskbar_height = rect.bottom - rect.top
                    taskbar_width = rect.right - rect.left

                    if is_visible and taskbar_height > 0 and taskbar_width > 0:
                        return f"OK (visible, {taskbar_width}x{taskbar_height})"
                    elif is_visible:
                        return "Visible but may have size issues"
                    else:
                        return "Hidden/Not visible"
                else:
                    return "Visible but position unknown"
            else:
                return "Taskbar not found"

        except Exception as e:
            return f"Test error: {e}"

    async def test_overlay_configuration(self) -> dict[str, Any]:
        """Test current overlay configuration for taskbar compatibility.

        Returns:
            Dict with test results
        """
        results = {
            "overlay_windows": [],
            "taskbar_status": "unknown",
            "recommendations": [],
        }

        try:
            # Find overlay windows
            overlay_windows = await self._find_overlay_windows()

            for hwnd in overlay_windows:
                window_info = {
                    "handle": hwnd,
                    "visible": bool(ctypes.windll.user32.IsWindowVisible(hwnd)),
                    "styles": {},
                    "position": {},
                    "taskbar_friendly": False,
                }

                # Get window styles
                ex_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
                style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_STYLE)

                window_info["styles"] = {
                    "extended": hex(ex_style),
                    "regular": hex(style),
                    "has_toolwindow": bool(ex_style & WS_EX_TOOLWINDOW),
                    "has_transparent": bool(ex_style & WS_EX_TRANSPARENT),
                    "has_layered": bool(ex_style & WS_EX_LAYERED),
                    "has_noactivate": bool(ex_style & WS_EX_NOACTIVATE),
                    "is_popup": bool(style & WS_POPUP),
                }

                # Get window position
                rect = wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    window_info["position"] = {
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                        "width": rect.right - rect.left,
                        "height": rect.bottom - rect.top,
                    }

                    # Check if window covers taskbar area
                    screen_height = ctypes.windll.user32.GetSystemMetrics(1)
                    if rect.bottom >= screen_height - 10:  # Within 10 pixels of bottom
                        results["recommendations"].append(
                            f"Window {hwnd} may be covering taskbar area"
                        )

                # Determine if configuration is taskbar-friendly
                if (
                    window_info["styles"]["has_toolwindow"]
                    and window_info["styles"]["has_noactivate"]
                    and window_info["styles"]["is_popup"]
                ):
                    window_info["taskbar_friendly"] = True

                results["overlay_windows"].append(window_info)

            # Test taskbar status
            results["taskbar_status"] = await self._test_taskbar_functionality()

            # Generate recommendations
            if not any(w["taskbar_friendly"] for w in results["overlay_windows"]):
                results["recommendations"].append(
                    "No taskbar-friendly overlay windows found"
                )

            if "OK" not in results["taskbar_status"]:
                results["recommendations"].append(
                    "Taskbar functionality may be compromised"
                )

        except Exception as e:
            results["error"] = str(e)

        return results

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.overlay_process:
            try:
                self.overlay_process.terminate()
            except:
                pass

        if self.client_session:
            await self.client_session.close()
        logger.info("Overlay taskbar fix manager cleaned up")


async def rebuild_overlay_for_taskbar() -> dict[str, Any]:
    """Main function to rebuild overlay with taskbar compatibility.

    Returns:
        Dict with rebuild results
    """
    manager = OverlayTaskbarFix()

    try:
        # Initialize manager
        if not await manager.initialize():
            return {
                "success": False,
                "error": "Failed to initialize overlay taskbar fix manager",
            }

        # Test current configuration
        pre_test = await manager.test_overlay_configuration()

        # Rebuild overlay
        rebuild_result = await manager.rebuild_overlay()

        # Test after rebuild
        post_test = await manager.test_overlay_configuration()

        return {
            "success": "✅" in rebuild_result,
            "rebuild_result": rebuild_result,
            "pre_test": pre_test,
            "post_test": post_test,
            "message": "Overlay rebuild for taskbar compatibility completed",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run configuration test only
        async def test_only():
            manager = OverlayTaskbarFix()
            if await manager.initialize():
                result = await manager.test_overlay_configuration()
                await manager.cleanup()
                return result
            return {"error": "Failed to initialize"}

        result = asyncio.run(test_only())
        print(json.dumps(result, indent=2, default=str))
    else:
        # Rebuild overlay
        result = asyncio.run(rebuild_overlay_for_taskbar())
        print(json.dumps(result, indent=2, default=str))

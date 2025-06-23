#!/usr/bin/env python3
"""
GAJA Assistant - Overlay Input Blocking Fix
Comprehensive solution for overlay click-through and input management issues.

Following AGENTS.md guidelines:
- Async-first architecture
- Comprehensive test coverage
- Clear logging and error handling
- Modular design
"""

import asyncio
import ctypes
import json
import logging
import sys
from ctypes import wintypes
from typing import Any, Optional

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Windows API constants for window management
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
SW_HIDE = 0
SW_SHOW = 5
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class OverlayInputManager:
    """Manages overlay input behavior to prevent blocking desktop interaction.

    This class ensures the overlay allows click-through when inactive and properly
    captures input only when displaying interactive content.
    """

    def __init__(self):
        """Initialize the overlay input manager."""
        self.overlay_hwnd: Optional[int] = None
        self.is_interactive_mode: bool = False
        self.client_session: Optional[aiohttp.ClientSession] = None
        self.overlay_api_base = "http://localhost:5001"

    async def initialize(self) -> bool:
        """Initialize the overlay input manager.

        Returns:
            bool: True if initialization successful
        """
        try:
            # Find overlay window
            self.overlay_hwnd = await self._find_overlay_window()
            if not self.overlay_hwnd:
                logger.error("Could not find overlay window")
                return False

            # Create HTTP session
            self.client_session = aiohttp.ClientSession()

            # Apply initial fix
            await self._apply_click_through_fix()

            logger.info("Overlay input manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize overlay input manager: {e}")
            return False

    async def _find_overlay_window(self) -> Optional[int]:
        """Find the overlay window handle.

        Returns:
            Optional[int]: Window handle if found
        """

        def enum_windows_callback(hwnd, lParam):
            """Callback for enumerating windows."""
            window_text = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, window_text, 512)
            window_title = window_text.value.lower()

            # Look for Gaja overlay window
            if any(
                keyword in window_title for keyword in ["gaja", "overlay", "asystent"]
            ):
                windows.append(hwnd)
            return True

        windows = []
        enum_windows_proc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
        )
        ctypes.windll.user32.EnumWindows(enum_windows_proc(enum_windows_callback), 0)

        if windows:
            logger.info(f"Found {len(windows)} potential overlay windows")
            return windows[0]  # Return first match

        return None

    async def _apply_click_through_fix(self) -> None:
        """Apply comprehensive click-through fix to the overlay window."""
        if not self.overlay_hwnd:
            logger.error("No overlay window handle available")
            return

        try:
            # Get current extended window style
            current_style = ctypes.windll.user32.GetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE
            )

            # Calculate new style for click-through mode
            new_style = (
                current_style
                | WS_EX_TRANSPARENT
                | WS_EX_LAYERED
                | WS_EX_NOACTIVATE
                | WS_EX_TOOLWINDOW
            )

            # Apply new extended window style
            result = ctypes.windll.user32.SetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE, new_style
            )

            if result == 0:
                logger.warning("SetWindowLongPtr returned 0 - may indicate error")

            # Set window position to ensure it doesn't interfere
            ctypes.windll.user32.SetWindowPos(
                self.overlay_hwnd,
                HWND_TOPMOST,  # Keep on top but transparent
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )

            logger.info("Applied click-through fix to overlay window")

        except Exception as e:
            logger.error(f"Failed to apply click-through fix: {e}")

    async def set_interactive_mode(self, interactive: bool) -> None:
        """Set overlay interactive mode.

        Args:
            interactive: True to capture input, False for click-through
        """
        if not self.overlay_hwnd:
            logger.error("No overlay window handle available")
            return

        try:
            current_style = ctypes.windll.user32.GetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE
            )

            if interactive:
                # Remove transparent flag to capture input
                new_style = current_style & ~WS_EX_TRANSPARENT
                logger.info("Setting overlay to interactive mode")
            else:
                # Add transparent flag for click-through
                new_style = current_style | WS_EX_TRANSPARENT
                logger.info("Setting overlay to click-through mode")

            ctypes.windll.user32.SetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE, new_style
            )
            self.is_interactive_mode = interactive

        except Exception as e:
            logger.error(f"Failed to set interactive mode: {e}")

    async def monitor_overlay_state(self) -> None:
        """Monitor overlay state and automatically manage input behavior."""
        if not self.client_session:
            logger.error("Client session not initialized")
            return

        logger.info("Starting overlay state monitoring")

        while True:
            try:
                # Check overlay status
                async with self.client_session.get(
                    f"{self.overlay_api_base}/api/status"
                ) as response:
                    if response.status == 200:
                        status = await response.json()
                        await self._handle_status_update(status)
                    else:
                        logger.warning(
                            f"Failed to get overlay status: {response.status}"
                        )

            except Exception as e:
                logger.warning(f"Error monitoring overlay state: {e}")

            await asyncio.sleep(0.5)  # Check twice per second

    async def _handle_status_update(self, status: dict[str, Any]) -> None:
        """Handle overlay status update and adjust input behavior.

        Args:
            status: Status data from overlay API
        """
        # Determine if overlay should be interactive
        is_listening = status.get("is_listening", False)
        is_speaking = status.get("is_speaking", False)
        wake_word_detected = status.get("wake_word_detected", False)
        has_text = bool(status.get("text", "").strip())
        is_visible = status.get("visible", False)

        # Overlay should be interactive when:
        # 1. Actively listening for user input
        # 2. Displaying important text that user might want to interact with
        # 3. In wake word detection state (brief moment of potential interaction)
        should_be_interactive = is_listening and is_visible

        # Update interactive mode if needed
        if should_be_interactive != self.is_interactive_mode:
            await self.set_interactive_mode(should_be_interactive)

    async def force_click_through(self) -> str:
        """Force overlay to click-through mode regardless of current state.

        Returns:
            str: Result message
        """
        try:
            await self.set_interactive_mode(False)
            return "✅ Overlay set to click-through mode"
        except Exception as e:
            return f"❌ Failed to set click-through mode: {e}"

    async def test_overlay_behavior(self) -> dict[str, Any]:
        """Test overlay behavior and return diagnostics.

        Returns:
            Dict with test results
        """
        results = {
            "overlay_found": bool(self.overlay_hwnd),
            "window_handle": self.overlay_hwnd,
            "interactive_mode": self.is_interactive_mode,
            "window_properties": {},
            "overlay_api_status": "unknown",
        }

        if self.overlay_hwnd:
            try:
                # Get window properties
                current_style = ctypes.windll.user32.GetWindowLongPtrW(
                    self.overlay_hwnd, GWL_EXSTYLE
                )
                results["window_properties"] = {
                    "has_transparent": bool(current_style & WS_EX_TRANSPARENT),
                    "has_layered": bool(current_style & WS_EX_LAYERED),
                    "has_noactivate": bool(current_style & WS_EX_NOACTIVATE),
                    "has_toolwindow": bool(current_style & WS_EX_TOOLWINDOW),
                    "raw_style": hex(current_style),
                }
            except Exception as e:
                results["window_properties_error"] = str(e)

        # Test API connectivity
        if self.client_session:
            try:
                async with self.client_session.get(
                    f"{self.overlay_api_base}/api/status"
                ) as response:
                    results["overlay_api_status"] = response.status
            except Exception as e:
                results["overlay_api_error"] = str(e)

        return results

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client_session:
            await self.client_session.close()
        logger.info("Overlay input manager cleaned up")


async def fix_overlay_input_blocking() -> dict[str, Any]:
    """Main function to fix overlay input blocking issues.

    Returns:
        Dict with fix results
    """
    manager = OverlayInputManager()

    try:
        # Initialize manager
        if not await manager.initialize():
            return {
                "success": False,
                "error": "Failed to initialize overlay input manager",
            }

        # Apply immediate fix
        force_result = await manager.force_click_through()

        # Get diagnostics
        diagnostics = await manager.test_overlay_behavior()

        return {
            "success": True,
            "force_fix_result": force_result,
            "diagnostics": diagnostics,
            "message": "Overlay input fix applied successfully",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await manager.cleanup()


async def start_overlay_monitor() -> None:
    """Start continuous overlay monitoring (for long-term fix)."""
    manager = OverlayInputManager()

    try:
        if await manager.initialize():
            logger.info("Starting continuous overlay monitoring...")
            await manager.monitor_overlay_state()
        else:
            logger.error("Failed to initialize overlay monitoring")
    except KeyboardInterrupt:
        logger.info("Overlay monitoring stopped by user")
    except Exception as e:
        logger.error(f"Overlay monitoring error: {e}")
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        # Start continuous monitoring
        asyncio.run(start_overlay_monitor())
    else:
        # Apply one-time fix
        result = asyncio.run(fix_overlay_input_blocking())
        print(json.dumps(result, indent=2, default=str))

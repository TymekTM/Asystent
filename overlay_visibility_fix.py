#!/usr/bin/env python3
"""
GAJA Assistant - Overlay Visibility Fix
Comprehensive solution for overlay visibility issues after click-through fix.

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

# Windows API constants
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
LWA_ALPHA = 0x00000002
LWA_COLORKEY = 0x00000001
SW_HIDE = 0
SW_SHOW = 5
SW_SHOWNA = 8
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class OverlayVisibilityManager:
    """Manages overlay visibility while maintaining proper click-through behavior.

    This class ensures the overlay is visible when needed while maintaining the click-
    through functionality that prevents input blocking.
    """

    def __init__(self):
        """Initialize the overlay visibility manager."""
        self.overlay_hwnd: Optional[int] = None
        self.client_session: Optional[aiohttp.ClientSession] = None
        self.overlay_api_base = "http://localhost:5001"
        self.current_alpha = 255  # Track current alpha value

    async def initialize(self) -> bool:
        """Initialize the overlay visibility manager.

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

            logger.info("Overlay visibility manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize overlay visibility manager: {e}")
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

    async def fix_overlay_visibility(self) -> str:
        """Fix overlay visibility issues while maintaining click-through.

        Returns:
            str: Result message
        """
        if not self.overlay_hwnd:
            return "❌ No overlay window handle available"

        try:
            # Get current window properties
            current_style = ctypes.windll.user32.GetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE
            )
            is_visible = bool(ctypes.windll.user32.IsWindowVisible(self.overlay_hwnd))

            logger.info(
                f"Current window state - Visible: {is_visible}, Style: {hex(current_style)}"
            )

            # Apply optimal visibility settings
            # Keep WS_EX_LAYERED for transparency control
            # Keep WS_EX_TRANSPARENT for click-through
            # Remove WS_EX_NOACTIVATE temporarily to allow visibility
            new_style = current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            new_style = new_style & ~WS_EX_NOACTIVATE  # Remove no-activate temporarily

            # Apply new style
            ctypes.windll.user32.SetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE, new_style
            )

            # Set optimal alpha for visibility (semi-transparent but visible)
            alpha_value = 200  # 78% opacity - visible but not fully opaque
            result = ctypes.windll.user32.SetLayeredWindowAttributes(
                self.overlay_hwnd,
                0,  # No color key
                alpha_value,  # Alpha value
                LWA_ALPHA,  # Use alpha blending
            )

            if result:
                self.current_alpha = alpha_value
                logger.info(f"Set alpha to {alpha_value}")
            else:
                logger.warning("Failed to set alpha value")

            # Ensure window is shown
            ctypes.windll.user32.ShowWindow(
                self.overlay_hwnd, SW_SHOWNA
            )  # Show without activating

            # Set proper z-order
            ctypes.windll.user32.SetWindowPos(
                self.overlay_hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )

            # Re-apply WS_EX_NOACTIVATE for click-through
            final_style = new_style | WS_EX_NOACTIVATE
            ctypes.windll.user32.SetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE, final_style
            )

            # Verify final state
            final_visible = bool(
                ctypes.windll.user32.IsWindowVisible(self.overlay_hwnd)
            )
            final_style_check = ctypes.windll.user32.GetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE
            )

            logger.info(
                f"Final state - Visible: {final_visible}, Style: {hex(final_style_check)}, Alpha: {alpha_value}"
            )

            return f"✅ Overlay visibility fixed - Alpha: {alpha_value}, Visible: {final_visible}"

        except Exception as e:
            logger.error(f"Failed to fix overlay visibility: {e}")
            return f"❌ Failed to fix visibility: {e}"

    async def adjust_opacity(self, opacity_percent: int) -> str:
        """Adjust overlay opacity while maintaining visibility.

        Args:
            opacity_percent: Opacity from 1-100

        Returns:
            str: Result message
        """
        if not self.overlay_hwnd:
            return "❌ No overlay window handle available"

        try:
            # Convert percentage to alpha value (0-255)
            alpha_value = max(1, min(255, int(opacity_percent * 2.55)))

            result = ctypes.windll.user32.SetLayeredWindowAttributes(
                self.overlay_hwnd,
                0,  # No color key
                alpha_value,  # Alpha value
                LWA_ALPHA,  # Use alpha blending
            )

            if result:
                self.current_alpha = alpha_value
                logger.info(
                    f"Opacity adjusted to {opacity_percent}% (alpha: {alpha_value})"
                )
                return f"✅ Opacity set to {opacity_percent}%"
            else:
                return f"❌ Failed to set opacity to {opacity_percent}%"

        except Exception as e:
            return f"❌ Error adjusting opacity: {e}"

    async def force_show_overlay(self) -> str:
        """Force show overlay with maximum visibility.

        Returns:
            str: Result message
        """
        if not self.overlay_hwnd:
            return "❌ No overlay window handle available"

        try:
            # Get current style
            current_style = ctypes.windll.user32.GetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE
            )

            # Create style for maximum visibility while keeping click-through
            # Keep: WS_EX_LAYERED (for alpha), WS_EX_TRANSPARENT (for click-through)
            # Remove: WS_EX_TOOLWINDOW (might hide from display)
            visible_style = (current_style | WS_EX_LAYERED) & ~WS_EX_TOOLWINDOW

            # Apply style
            ctypes.windll.user32.SetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE, visible_style
            )

            # Set high opacity for visibility
            alpha_value = 220  # 86% opacity
            ctypes.windll.user32.SetLayeredWindowAttributes(
                self.overlay_hwnd,
                0,  # No color key
                alpha_value,  # Alpha value
                LWA_ALPHA,  # Use alpha blending
            )

            # Force show window
            ctypes.windll.user32.ShowWindow(self.overlay_hwnd, SW_SHOW)

            # Bring to front
            ctypes.windll.user32.SetWindowPos(
                self.overlay_hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
            )

            # Restore click-through style
            final_style = visible_style | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            ctypes.windll.user32.SetWindowLongPtrW(
                self.overlay_hwnd, GWL_EXSTYLE, final_style
            )

            self.current_alpha = alpha_value

            # Also tell the overlay API to show
            if self.client_session:
                try:
                    async with self.client_session.post(
                        f"{self.overlay_api_base}/show"
                    ) as response:
                        if response.status == 200:
                            logger.info("Overlay API show command sent")
                        else:
                            logger.warning(f"Overlay API returned {response.status}")
                except Exception as api_error:
                    logger.warning(f"Could not send API show command: {api_error}")

            logger.info(f"Force show completed - Alpha: {alpha_value}")
            return f"✅ Overlay forced to show with {int(alpha_value/2.55)}% opacity"

        except Exception as e:
            logger.error(f"Failed to force show overlay: {e}")
            return f"❌ Failed to force show: {e}"

    async def test_overlay_visibility(self) -> dict[str, Any]:
        """Test overlay visibility and return detailed diagnostics.

        Returns:
            Dict with visibility test results
        """
        results = {
            "overlay_found": bool(self.overlay_hwnd),
            "window_handle": self.overlay_hwnd,
            "current_alpha": self.current_alpha,
            "visibility_tests": {},
            "api_status": "unknown",
        }

        if self.overlay_hwnd:
            try:
                # Test basic visibility
                is_visible = bool(
                    ctypes.windll.user32.IsWindowVisible(self.overlay_hwnd)
                )
                results["visibility_tests"]["is_visible"] = is_visible

                # Get window style
                current_style = ctypes.windll.user32.GetWindowLongPtrW(
                    self.overlay_hwnd, GWL_EXSTYLE
                )
                results["visibility_tests"]["current_style"] = hex(current_style)
                results["visibility_tests"]["has_layered"] = bool(
                    current_style & WS_EX_LAYERED
                )
                results["visibility_tests"]["has_transparent"] = bool(
                    current_style & WS_EX_TRANSPARENT
                )
                results["visibility_tests"]["has_noactivate"] = bool(
                    current_style & WS_EX_NOACTIVATE
                )
                results["visibility_tests"]["has_toolwindow"] = bool(
                    current_style & WS_EX_TOOLWINDOW
                )

                # Get window rectangle
                rect = wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(
                    self.overlay_hwnd, ctypes.byref(rect)
                ):
                    results["visibility_tests"]["window_rect"] = {
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                        "width": rect.right - rect.left,
                        "height": rect.bottom - rect.top,
                    }

            except Exception as e:
                results["visibility_tests"]["error"] = str(e)

        # Test API connectivity
        if self.client_session:
            try:
                async with self.client_session.get(
                    f"{self.overlay_api_base}/api/status", timeout=2
                ) as response:
                    results["api_status"] = response.status
                    if response.status == 200:
                        api_data = await response.json()
                        results["api_data"] = api_data
            except Exception as e:
                results["api_error"] = str(e)

        return results

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client_session:
            await self.client_session.close()
        logger.info("Overlay visibility manager cleaned up")


async def fix_overlay_visibility() -> dict[str, Any]:
    """Main function to fix overlay visibility issues.

    Returns:
        Dict with fix results
    """
    manager = OverlayVisibilityManager()

    try:
        # Initialize manager
        if not await manager.initialize():
            return {
                "success": False,
                "error": "Failed to initialize overlay visibility manager",
            }

        # Apply visibility fix
        visibility_result = await manager.fix_overlay_visibility()

        # Force show for immediate visibility
        force_show_result = await manager.force_show_overlay()

        # Get diagnostics
        diagnostics = await manager.test_overlay_visibility()

        return {
            "success": True,
            "visibility_fix_result": visibility_result,
            "force_show_result": force_show_result,
            "diagnostics": diagnostics,
            "message": "Overlay visibility fix applied successfully",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await manager.cleanup()


async def adjust_overlay_opacity(opacity_percent: int) -> dict[str, Any]:
    """Adjust overlay opacity to specified percentage.

    Args:
        opacity_percent: Opacity from 1-100

    Returns:
        Dict with adjustment results
    """
    manager = OverlayVisibilityManager()

    try:
        if await manager.initialize():
            result = await manager.adjust_opacity(opacity_percent)
            diagnostics = await manager.test_overlay_visibility()

            return {
                "success": "set to" in result.lower(),
                "result": result,
                "diagnostics": diagnostics,
            }
        else:
            return {"success": False, "error": "Failed to initialize manager"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "opacity" and len(sys.argv) > 2:
            # Adjust opacity
            try:
                opacity = int(sys.argv[2])
                result = asyncio.run(adjust_overlay_opacity(opacity))
                print(json.dumps(result, indent=2, default=str))
            except ValueError:
                print("Error: Opacity must be a number between 1-100")
        elif sys.argv[1] == "test":
            # Run visibility test only
            async def test_only():
                manager = OverlayVisibilityManager()
                if await manager.initialize():
                    result = await manager.test_overlay_visibility()
                    await manager.cleanup()
                    return result
                return {"error": "Failed to initialize"}

            result = asyncio.run(test_only())
            print(json.dumps(result, indent=2, default=str))
    else:
        # Apply visibility fix
        result = asyncio.run(fix_overlay_visibility())
        print(json.dumps(result, indent=2, default=str))

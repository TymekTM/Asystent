#!/usr/bin/env python3
"""
GAJA Assistant - Targeted Taskbar Protection Fix
Specific fix to prevent overlay windows from covering the Windows taskbar.

Following AGENTS.md guidelines:
- Async-first architecture
- Targeted solution
- Clear logging
"""

import asyncio
import ctypes
import json
import logging
from ctypes import wintypes
from typing import Any

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
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010


async def fix_taskbar_coverage() -> dict[str, Any]:
    """Fix overlay windows that are covering the Windows taskbar.

    Returns:
        Dict with fix results
    """
    try:
        logger.info("Starting targeted taskbar coverage fix...")

        # Get screen dimensions
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        # Get taskbar info
        taskbar_hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        taskbar_height = 48  # Standard taskbar height

        if taskbar_hwnd:
            taskbar_rect = wintypes.RECT()
            if ctypes.windll.user32.GetWindowRect(
                taskbar_hwnd, ctypes.byref(taskbar_rect)
            ):
                taskbar_height = taskbar_rect.bottom - taskbar_rect.top
                logger.info(f"Detected taskbar height: {taskbar_height}")

        # Calculate safe overlay area (exclude taskbar)
        safe_height = screen_height - taskbar_height

        # Find overlay windows
        def enum_windows_callback(hwnd, lParam):
            window_text = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, window_text, 512)
            window_title = window_text.value.lower()

            class_name = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetClassNameW(hwnd, class_name, 512)
            class_name_str = class_name.value.lower()

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

        fixed_windows = 0
        results = []

        for hwnd in windows:
            try:
                # Check if window is covering taskbar
                rect = wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    window_width = rect.right - rect.left
                    window_height = rect.bottom - rect.top

                    # Check if window extends into taskbar area
                    if (
                        rect.bottom >= screen_height - 10
                    ):  # Within 10 pixels of screen bottom
                        logger.info(
                            f"Window {hwnd} is covering taskbar area (bottom: {rect.bottom})"
                        )

                        # Get current style
                        current_ex_style = ctypes.windll.user32.GetWindowLongPtrW(
                            hwnd, GWL_EXSTYLE
                        )

                        # Apply taskbar-safe settings
                        new_ex_style = (
                            current_ex_style
                            | WS_EX_LAYERED
                            | WS_EX_TRANSPARENT
                            | WS_EX_NOACTIVATE
                            | WS_EX_TOOLWINDOW
                        )

                        # Update window style
                        ctypes.windll.user32.SetWindowLongPtrW(
                            hwnd, GWL_EXSTYLE, new_ex_style
                        )

                        # Resize window to avoid taskbar
                        new_height = safe_height

                        result = ctypes.windll.user32.SetWindowPos(
                            hwnd,
                            HWND_TOPMOST,
                            0,
                            0,  # Position at top-left
                            screen_width,
                            new_height,  # New size
                            SWP_NOACTIVATE,
                        )

                        if result:
                            fixed_windows += 1
                            logger.info(
                                f"Fixed window {hwnd}: resized to {screen_width}x{new_height}"
                            )
                            results.append(
                                {
                                    "handle": hwnd,
                                    "action": "resized",
                                    "old_size": f"{window_width}x{window_height}",
                                    "new_size": f"{screen_width}x{new_height}",
                                }
                            )
                        else:
                            logger.warning(f"Failed to resize window {hwnd}")
                            results.append(
                                {
                                    "handle": hwnd,
                                    "action": "failed",
                                    "error": "SetWindowPos failed",
                                }
                            )
                    else:
                        logger.info(
                            f"Window {hwnd} is not covering taskbar (bottom: {rect.bottom})"
                        )
                        results.append(
                            {
                                "handle": hwnd,
                                "action": "no_change",
                                "reason": "not covering taskbar",
                            }
                        )

            except Exception as e:
                logger.error(f"Error processing window {hwnd}: {e}")
                results.append({"handle": hwnd, "action": "error", "error": str(e)})

        # Test taskbar after fix
        taskbar_test = "unknown"
        if taskbar_hwnd:
            is_visible = bool(ctypes.windll.user32.IsWindowVisible(taskbar_hwnd))
            if is_visible:
                taskbar_test = "visible"
            else:
                taskbar_test = "hidden"

        return {
            "success": fixed_windows > 0,
            "fixed_windows": fixed_windows,
            "total_windows": len(windows),
            "taskbar_test": taskbar_test,
            "screen_info": {
                "width": screen_width,
                "height": screen_height,
                "taskbar_height": taskbar_height,
                "safe_height": safe_height,
            },
            "window_results": results,
            "message": f"Fixed {fixed_windows} overlay windows covering taskbar",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = asyncio.run(fix_taskbar_coverage())
    print(json.dumps(result, indent=2, default=str))

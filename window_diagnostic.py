#!/usr/bin/env python3
"""Overlay Window Position & Visibility Diagnostics Sprawdza pozycjonowanie i
właściwości okna overlay."""

import ctypes
import ctypes.wintypes as wintypes
from ctypes import wintypes

# Windows API constants
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


def find_gaja_window():
    """Znajdź okno Gaja Overlay."""

    def enum_windows_callback(hwnd, lParam):
        window_text = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(hwnd, window_text, 512)
        window_title = window_text.value

        if "gaja" in window_title.lower() or "overlay" in window_title.lower():
            windows.append((hwnd, window_title))
        return True

    windows = []
    enum_windows_proc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
    )
    ctypes.windll.user32.EnumWindows(enum_windows_proc(enum_windows_callback), 0)
    return windows


def get_window_info(hwnd):
    """Pobierz informacje o oknie."""
    # Get window rect
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))

    # Get window styles
    style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -16)  # GWL_STYLE
    ex_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -20)  # GWL_EXSTYLE

    # Check visibility
    is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
    is_iconic = ctypes.windll.user32.IsIconic(hwnd)  # minimized
    is_zoomed = ctypes.windll.user32.IsZoomed(hwnd)  # maximized

    # Get window opacity (alpha)
    alpha = ctypes.c_ubyte()
    layered = ctypes.windll.user32.GetLayeredWindowAttributes(
        hwnd, None, ctypes.byref(alpha), None
    )

    return {
        "rect": (rect.left, rect.top, rect.right, rect.bottom),
        "width": rect.right - rect.left,
        "height": rect.bottom - rect.top,
        "visible": bool(is_visible),
        "minimized": bool(is_iconic),
        "maximized": bool(is_zoomed),
        "style": hex(style),
        "ex_style": hex(ex_style),
        "has_layered": bool(layered),
        "alpha": alpha.value if layered else None,
    }


def make_window_visible(hwnd):
    """Spróbuj uczynić okno widocznym."""
    print(f"Próbuję uczynić okno {hwnd} widocznym...")

    # Show window
    ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW

    # Bring to front
    ctypes.windll.user32.BringWindowToTop(hwnd)

    # Set topmost
    ctypes.windll.user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
    )

    # Set alpha to full opacity if layered
    try:
        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, 2)  # LWA_ALPHA
        print("   ✅ Ustawiono nieprzezroczystość na 100%")
    except:
        print("   ⚠️  Nie udało się ustawić przezroczystości")

    # Force update
    ctypes.windll.user32.UpdateWindow(hwnd)

    print("   ✅ Komendy wykonane")


def main():
    print("🔍 GAJA Overlay Window Diagnostics")
    print("=" * 50)

    # Find windows
    windows = find_gaja_window()

    if not windows:
        print("❌ Nie znaleziono okien Gaja/Overlay")
        return

    print(f"✅ Znaleziono {len(windows)} okien:")

    for hwnd, title in windows:
        print(f"\n📋 Okno: {title} (HWND: {hwnd})")
        print("-" * 40)

        info = get_window_info(hwnd)

        print(f"   📍 Pozycja: ({info['rect'][0]}, {info['rect'][1]})")
        print(f"   📏 Rozmiar: {info['width']} x {info['height']}")
        print(f"   👁️  Widoczne: {info['visible']}")
        print(f"   📦 Zminimalizowane: {info['minimized']}")
        print(f"   📈 Zmaksymalizowane: {info['maximized']}")
        print(f"   🎨 Ma warstwy: {info['has_layered']}")
        if info["alpha"] is not None:
            print(
                f"   🌫️  Przezroczystość: {info['alpha']}/255 ({info['alpha']/255*100:.1f}%)"
            )
        print(f"   🏷️  Style: {info['style']}")
        print(f"   🏷️  Ex Style: {info['ex_style']}")

        # Try to make visible
        if not info["visible"] or info["alpha"] == 0:
            print("\n🛠️  Próbuję naprawić widoczność...")
            make_window_visible(hwnd)

            # Recheck
            new_info = get_window_info(hwnd)
            print(f"   📊 Nowa widoczność: {new_info['visible']}")
            if new_info["alpha"] is not None:
                print(f"   📊 Nowa przezroczystość: {new_info['alpha']}/255")


if __name__ == "__main__":
    main()

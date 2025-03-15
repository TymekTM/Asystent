# modules/screenshot_module.py

import os
import datetime
import logging

logger = logging.getLogger(__name__)

try:
    import pyautogui
except ImportError:
    pyautogui = None

if pyautogui is None:
    try:
        from PIL import ImageGrab
    except ImportError:
        ImageGrab = None
    else:
        logger.info("Używam PIL ImageGrab jako alternatywy dla pyautogui.")

def capture_screen(params: str = "") -> str:
    if pyautogui is None and ImageGrab is None:
        logger.error("Nie znaleziono ani pyautogui, ani PIL ImageGrab.")
        return "Nie można wykonać zrzutu ekranu - brak odpowiedniej biblioteki."
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        folder = "screenshots"
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        if pyautogui is not None:
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
        else:
            screenshot = ImageGrab.grab()
            screenshot.save(filepath, "PNG")
        logger.info("Zrzut ekranu zapisany do: %s", filepath)
        return filepath
    except Exception as e:
        logger.error("Błąd przy tworzeniu zrzutu ekranu: %s", e)
        return "Błąd przy wykonywaniu zrzutu ekranu."

def register():
    return {
        "command": "!screenshot",
        "description": "Pozwala zrobić zrzut ekranu. Pierwszy prompt potwierdza wykonanie, drugi zawiera ścieżkę do pliku.",
        "handler": capture_screen
    }

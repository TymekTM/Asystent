# see_screen_module.py
import base64
import os
import datetime
import logging
import ollama

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
        logging.info("Używam PIL ImageGrab jako alternatywy dla pyautogui.")

from config import MAIN_MODEL  # <-- importujemy

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def capture_screen(params: str = "") -> str:
    if pyautogui is None and ImageGrab is None:
        logging.error("Nie znaleziono ani pyautogui, ani PIL ImageGrab.")
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

        abs_path = os.path.abspath(filepath)
        logging.info("Zrzut ekranu zapisany do: %s", filepath)

        # Konwersja obrazu do base64
        image_base64 = encode_image_to_base64(abs_path)

        # Wstępny prompt
        prompt_text = (
            f"Na podstawie tego zrzutu ekranu odpowiedz na pytanie: {params}"
            if params.strip()
            else "Co znajduje się na tym zrzucie ekranu?"
        )

        # Wywołanie modelu (gamma3:4B)
        response = ollama.generate(
            model=MAIN_MODEL,
            prompt=prompt_text,
            images=[image_base64]
        )

        # Zwracamy finalną odpowiedź
        answer = response["response"].strip()
        return answer

    except Exception as e:
        logging.error("Błąd przy tworzeniu zrzutu ekranu: %s", e)
        return "Błąd przy wykonywaniu zrzutu ekranu."

def register():
    return {
        "command": "!screenshot",
        "aliases": ["screenshot", "screen"],
        "description": "Pozwala zobaczyć, co znajduje się na ekranie użytkownika, analizując zrzut ekranu.",
        "handler": capture_screen
    }

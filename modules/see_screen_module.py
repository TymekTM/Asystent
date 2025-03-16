# see_screen_module.py
import base64
import os
import datetime
import logging
import subprocess

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

def play_screenshot_beep():
    beep_file = "screenshot_beep.mp3"
    if os.path.exists(beep_file):
        try:
            subprocess.Popen(["ffplay", "-nodisp", "-loglevel", "quiet", "-autoexit", beep_file])
        except Exception as e:
            logging.error("Błąd odtwarzania dźwięku screenshot: %s", e)
    else:
        logging.warning("Plik screenshot_beep.mp3 nie został znaleziony.")


def capture_screen(params: str = "") -> str:
    if pyautogui is None and ImageGrab is None:
        logging.error("Nie znaleziono ani pyautogui, ani PIL ImageGrab.")
        return "Nie można wykonać zrzutu ekranu - brak odpowiedniej biblioteki."
    try:
        play_screenshot_beep()  # odtwarzamy dźwięk przed wykonaniem zrzutu
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

        image_base64 = encode_image_to_base64(abs_path)
        prompt_text = (
            f"Na podstawie tego zrzutu ekranu odpowiedz na pytanie: {params}"
            if params.strip()
            else "Co znajduje się na tym zrzucie ekranu?"
        )

        response = ollama.generate(
            model=MAIN_MODEL,
            prompt=prompt_text,
            images=[image_base64]
        )
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

import base64, os, datetime, logging, subprocess, ollama
import numpy as np
from audio_modules.beep_sounds import play_beep

try:
    import dxcam  # Najszybsza biblioteka do przechwytywania ekranu dla Windows
except ImportError:
    dxcam = None
    # Fallback do istniejących metod
    try:
        import pyautogui
    except ImportError:
        pyautogui = None
        try:
            from PIL import ImageGrab
        except ImportError:
            ImageGrab = None

from config import MAIN_MODEL

# Inicjalizacja kamery DXcam jako zmiennej globalnej dla lepszej wydajności
dxcam_device = None
if dxcam is not None:
    try:
        dxcam_device = dxcam.create()
        logging.info("DXcam zainicjalizowany pomyślnie.")
    except Exception as e:
        logging.error("Nie udało się zainicjalizować DXcam: %s", e)
        dxcam_device = None


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def capture_screen(params: str = "") -> str:
    global dxcam_device

    try:
        play_beep("screenshot")  # Zachowujemy dźwięk
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        folder = "screenshots"
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)

        # Próba użycia DXcam jako najszybszej metody
        if dxcam_device is not None:
            screenshot = dxcam_device.grab()  # Znacznie szybsza metoda przechwytywania
            if screenshot is not None:
                import cv2
                cv2.imwrite(filepath, screenshot)
                logging.info("Zrzut ekranu wykonany z DXcam")
            else:
                raise Exception("DXcam zwrócił None")
        # Fallback do innych metod
        elif pyautogui is not None:
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
        elif ImageGrab is not None:
            screenshot = ImageGrab.grab()
            screenshot.save(filepath, "PNG")
        else:
            return "Nie można wykonać zrzutu ekranu - brak odpowiedniej biblioteki."

        abs_path = os.path.abspath(filepath)
        image_base64 = encode_image_to_base64(abs_path)

        prompt_text = f"Na podstawie tego zrzutu ekranu odpowiedz na pytanie: {params}" if params.strip() else "Co znajduje się na tym zrzucie ekranu?"

        response = ollama.generate(
            model=MAIN_MODEL,
            prompt=prompt_text,
            images=[image_base64]
        )

        return response["response"].strip()
    except Exception as e:
        logging.error("Błąd przy wykonywaniu zrzutu ekranu: %s", e)
        return f"Błąd przy wykonywaniu zrzutu ekranu: {str(e)}"


def register():
    return {
        "command": "screenshot",
        "aliases": ["screenshot", "screen"],
        "description": "Wykonuje zrzut ekranu i analizuje go.",
        "handler": capture_screen
    }

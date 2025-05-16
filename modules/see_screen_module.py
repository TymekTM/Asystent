import base64, os, datetime, logging, subprocess, ollama
import numpy as np

from ai_module import chat_with_providers, remove_chain_of_thought
from audio_modules.beep_sounds import play_beep
# Import prompt and ensure cv2 is a module attribute for use in capture_screen (can be monkeypatched)
# Import screen prompt
from prompts import SEE_SCREEN_PROMPT
# Optional OpenCV for writing images; tests may monkeypatch module cv2
try:
    import cv2 as _cv2
    cv2 = _cv2
except ImportError:
    cv2 = None

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

# config import
from config import MAIN_MODEL


# Inicjalizacja kamery DXcam jako zmiennej globalnej dla lepszej wydajności
dxcam_device = None
if dxcam is not None:
    try:
        dxcam_device = dxcam.create()
        logging.info("DXcam zainicjalizowany pomyślnie.")
    except Exception as e:
        logging.error("Nie udało się zainicjować DXcam: %s", e)
        dxcam_device = None


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def capture_screen(params: str = "", conversation_history: list = None) -> str:
    global dxcam_device

    try:
        play_beep("screenshot")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        folder = "screenshots"
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)

        if dxcam_device is not None:
            screenshot = dxcam_device.grab()
            if screenshot is not None:
                # write using module-level cv2 (can be monkeypatched in tests)
                if cv2:
                    cv2.imwrite(filepath, screenshot)
                    logging.info("Zrzut ekranu wykonany z DXcam")
                else:
                    raise Exception("cv2 nie jest dostępne do zapisu zrzutu ekranu")
            else:
                raise Exception("DXcam zwrócił None")
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
        # Clean up the saved screenshot file if no conversation history (fallback/test mode)
        if conversation_history is None:
            try:
                os.remove(abs_path)
            except Exception:
                pass
            return image_base64

        prompt_text = f"Na podstawie tego zrzutu ekranu odpowiedz na pytanie: {params}" if params.strip() else "Co znajduje się na tym zrzucie ekranu?"

        # Jeśli dostępny jest kontekst rozmowy, dołączamy go
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.extend([
            {"role": "system", "content": SEE_SCREEN_PROMPT},
            {"role": "user", "content": prompt_text}
        ])

        response = chat_with_providers(
            model=MAIN_MODEL,
            messages=messages,
            images=[image_base64]
        )

        result_text = remove_chain_of_thought(response["message"]["content"].strip())
        return result_text

    except Exception as e:
        logging.error("Błąd przy wykonywaniu zrzutu ekranu: %s", e, exc_info=True)
        return f"Błąd przy wykonywaniu zrzutu ekranu: {str(e)}"


def register():
    return {
        "command": "screenshot",
        "aliases": ["screenshot", "screen"],
        "description": "Wykonuje zrzut ekranu i analizuje go.",
        "handler": capture_screen,
        "prompt": SEE_SCREEN_PROMPT
    }

import base64, os, datetime, logging, subprocess, ollama
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
        logging.info("Using PIL ImageGrab as alternative to pyautogui.")
from config import MAIN_MODEL

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def play_screenshot_beep():
    beep_file = "screenshot_beep.mp3"
    if os.path.exists(beep_file):
        try:
            subprocess.Popen(["ffplay", "-nodisp", "-loglevel", "quiet", "-autoexit", beep_file])
        except Exception as e:
            logging.error("Error playing screenshot beep: %s", e)
    else:
        logging.warning("screenshot_beep.mp3 not found.")

def capture_screen(params: str = "") -> str:
    if pyautogui is None and (('ImageGrab' not in globals()) or ImageGrab is None):
        logging.error("No library for screen capture available.")
        return "Nie można wykonać zrzutu ekranu - brak odpowiedniej biblioteki."
    try:
        play_screenshot_beep()
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
        logging.info("Screenshot saved: %s", filepath)
        image_base64 = encode_image_to_base64(abs_path)
        prompt_text = f"Na podstawie tego zrzutu ekranu odpowiedz na pytanie: {params}" if params.strip() else "Co znajduje się na tym zrzucie ekranu?"
        response = ollama.generate(
            model=MAIN_MODEL,
            prompt=prompt_text,
            images=[image_base64]
        )
        return response["response"].strip()
    except Exception as e:
        logging.error("Error capturing screen: %s", e)
        return "Błąd przy wykonywaniu zrzutu ekranu."

def register():
    return {
        "command": "screenshot",
        "aliases": ["screenshot", "screen"],
        "description": "Wykonuje zrzut ekranu i analizuje go.",
        "handler": capture_screen
    }

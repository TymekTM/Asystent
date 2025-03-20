import logging, subprocess, os, ollama
from config import DEEP_MODEL
from prompts import DEEPTHINK_PROMPT

logger = logging.getLogger(__name__)

def play_deepthink_beep():
    beep_file = "deepthink_beep.mp3"
    if os.path.exists(beep_file):
        try:
            subprocess.Popen(["ffplay", "-nodisp", "-loglevel", "quiet", "-autoexit", beep_file])
        except Exception as e:
            logger.error("Error playing deepthink beep: %s", e)
    else:
        logger.warning("deepthink_beep.mp3 not found.")

def deep_reasoning_handler(params: str = "") -> str:
    if not params.strip():
        return "Podaj treść do głębokiego rozumowania po komendzie !deep"
    try:
        play_deepthink_beep()
        response = ollama.chat(
            model=DEEP_MODEL,
            messages=[
                {"role": "system", "content": DEEPTHINK_PROMPT},
                {"role": "user", "content": params}
            ]
        )
        return response["message"]["content"].strip()
    except Exception as e:
        logger.error("Error in deep reasoning: %s", e)
        return f"Błąd w deep reasoning: {e}"

def register():
    return {
        "command": "deep",
        "aliases": ["deep", "wgłęb"],
        "description": "Wykonuje głębokie rozumowanie",
        "handler": deep_reasoning_handler
    }

import logging, subprocess, os, ollama
from config import DEEP_MODEL
from prompts import DEEPTHINK_PROMPT
from audio_modules.beep_sounds import play_beep

logger = logging.getLogger(__name__)

def deep_reasoning_handler(params: str = "") -> str:
    if not params.strip():
        return "Podaj treść do głębokiego rozumowania po komendzie !deep"
    try:
        play_beep("deep")
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

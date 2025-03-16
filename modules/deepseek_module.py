# modules/deepseek_module.py

import logging
import ollama
import subprocess
import os

from config import DEEP_MODEL
from prompts import DEEPTHINK_PROMPT

logger = logging.getLogger(__name__)

def play_deepthink_beep():
    beep_file = "deepthink_beep.mp3"
    if os.path.exists(beep_file):
        try:
            subprocess.Popen(["ffplay", "-nodisp", "-loglevel", "quiet", "-autoexit", beep_file])
        except Exception as e:
            logger.error("Błąd odtwarzania dźwięku deepthink: %s", e)
    else:
        logger.warning("Plik deepthink_beep.mp3 nie został znaleziony.")

def deep_reasoning_handler(params: str = "") -> str:
    if not params.strip():
        return "Podaj treść do głębokiego rozumowania po komendzie !deep"
    try:
        play_deepthink_beep()  # odtwarzamy dźwięk
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
        "command": "!deep",
        "aliases": ["deep", "wgłęb"],
        "description": "Wykonuje głębokie rozumowanie, zastanawia się nad podanym hasłem lub celem",
        "handler": deep_reasoning_handler
    }

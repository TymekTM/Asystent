# modules/deepseek_module.py

import logging
import ollama

from config import DEEP_MODEL
from prompts import DEEPTHINK_PROMPT

logger = logging.getLogger(__name__)

def deep_reasoning_handler(params: str = "") -> str:
    """
    Wywołuje model deepseek-r1:7B, żeby przeprowadzić 'głębokie rozumowanie'.
    """
    if not params.strip():
        return "Podaj treść do głębokiego rozumowania po komendzie !deep"
    try:
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

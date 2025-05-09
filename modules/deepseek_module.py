import logging, subprocess, os, ollama
from config import DEEP_MODEL
from prompts import DEEPTHINK_PROMPT
from audio_modules.beep_sounds import play_beep
from ai_module import chat_with_providers, remove_chain_of_thought

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Modify handler to accept conversation_history (and potentially system_prompt, though unused here)
def deep_reasoning_handler(params: str = "", conversation_history: list = None) -> str:
    if not params.strip():
        return "Podaj treść do głębokiego rozumowania po komendzie !deep"
    try:
        play_beep("deep")
        # Prepare messages for the deep reasoning model
        messages = [
            {"role": "system", "content": DEEPTHINK_PROMPT}, # Use specific prompt
            # Optionally add recent conversation history for context
            # if conversation_history:
            #    messages = conversation_history[-4:] + messages # Example: last 4 turns
            {"role": "user", "content": params}
        ]

        response = chat_with_providers(
            model=DEEP_MODEL,
            messages=messages
        )
        # Make sure to remove CoT markers
        result_text = remove_chain_of_thought(response["message"]["content"].strip())
        return result_text
    except Exception as e:
        logger.error("Error in deep reasoning: %s", e, exc_info=True) # Add exc_info
        return f"Błąd w deep reasoning: {e}"

def register():
    return {
        "command": "deep",
        "aliases": ["deep", "wgłęb"],
        "description": "Wykonuje głębokie rozumowanie",
        "handler": deep_reasoning_handler,
        "prompt": DEEPTHINK_PROMPT # Add tool-specific prompt
    }

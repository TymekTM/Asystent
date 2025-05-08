# Custom handler for memory_get to always return all memories for AI
def _memory_get_with_full_memory(text, **kwargs):
    handler = _get_handler_from_module_register(register_memory_command, 'get')
    result = handler(text, **kwargs)
    if isinstance(result, dict) and 'all_memories' in result:
        return result
    return {'summary': result, 'success': True, 'all_memories': []}
"""
Intent system for the assistant.
Uses trained model from intent_pipeline_multilang to classify user text and dispatch to handlers.
All handler functions are stubs and should be implemented according to business logic.
"""

import joblib
import asyncio  # Added for async operations
from typing import Tuple, Any, Dict, Callable, Awaitable, Union  # Added Awaitable, Union, Callable

from performance_monitor import measure_performance
# Import actual handler and register function from search_module
from modules.search_module import search_handler as actual_module_search_handler
from modules.search_module import register as register_search_module_command

# TODO: Import register functions from other modules as they are created

from modules.api_module import register as register_api_command
from modules.see_screen_module import register as register_screenshot_command
from modules.memory_module import register as register_memory_command
from modules.deepseek_module import register as register_deepseek_command
from modules.core_module import register as register_core_command
from modules.open_web_module import register as register_open_web_command
from modules.weather_module import register as register_weather_command


# Paths to the trained model artifacts
VEC_FILE = "resources/Intent_AI/vectorizer.pkl"
MODEL_FILE = "resources/Intent_AI/intent_model.pkl"
THRESHOLD = 0.5  # confidence threshold

# List of supported intents
INTENTS = [
    "general",
    "weather_query",
    "about_assistant",
    "screenshot",
    "search",
    "memory_add",
    "memory_get",
    "memory_delete",
    "deep_reasoning",
    "timer_set",
    "timer_view",
    "event_add",
    "event_view",
    "reminder_set",
    "reminder_view",
    "shopping_add",
    "shopping_view",
    "shopping_remove",
    "task_add",
    "task_view",
    "task_complete",
    "task_remove",
]

# Optional: supported languages (if needed elsewhere)
LANGUAGES = ["Polish", "English"]

#------------------------------------------------------------------------------
# Command Registration Mapping
#------------------------------------------------------------------------------

# Maps intent names to their respective command registration functions.
# Each register function should return a dictionary with command metadata (e.g., name, description).
COMMAND_REGISTRATION_FUNCTIONS: Dict[str, Callable[[], Dict[str, Any]]] = {
    'search': register_search_module_command,
    'weather_query': register_weather_command,  
    'screenshot': register_screenshot_command,
    'memory_add': register_memory_command,
    'memory_get': register_memory_command,
    'memory_delete': register_memory_command,
    'deep_reasoning': register_deepseek_command,
    # All core-related intents use register_core_command
    'timer_set': register_core_command,
    'timer_view': register_core_command,
    'event_add': register_core_command,
    'event_view': register_core_command,
    'reminder_set': register_core_command,
    'reminder_view': register_core_command,
    'shopping_add': register_core_command,
    'shopping_view': register_core_command,
    'shopping_remove': register_core_command,
    'task_add': register_core_command,
    'task_view': register_core_command,
    'task_complete': register_core_command,
    'task_remove': register_core_command,
    # Intents like 'general', 'about_assistant' might not have specific commands to register,
    # unless they trigger a specific module action that should be described.
}

#------------------------------------------------------------------------------
# Model loading and inference
#------------------------------------------------------------------------------

def load_intent_model(
    vec_path: str = VEC_FILE,
    model_path: str = MODEL_FILE
) -> Tuple[Any, Any]:
    """
    Load the vectorizer and classification model from disk.
    Returns (vectorizer, classifier).
    """
    vec = joblib.load(vec_path)
    clf = joblib.load(model_path)
    return vec, clf

@measure_performance
def classify_intent(text: str) -> Tuple[str, float]:
    """
    Classify the user input text into an intent label and confidence score.
    Returns (intent, confidence).
    If confidence below THRESHOLD, intent is set to 'none'.
    """
    vec, clf = load_intent_model()
    # Transform and predict probabilities
    probs = clf.predict_proba(vec.transform([text]))[0]
    idx = probs.argmax()
    label = clf.classes_[idx]
    confidence = float(probs[idx])
    # Strip language suffix if present (label is '<intent>:<language>')
    intent = label.split(':', 1)[0] if confidence >= THRESHOLD else 'none'
    return intent, confidence

#------------------------------------------------------------------------------

# --- Unified intent handler mapping using module registrations ---
def _get_handler_from_module_register(register_func, subcommand=None):
    info = register_func()
    if subcommand and 'sub_commands' in info:
        return info['sub_commands'][subcommand]['function']
    return info['handler']



# Map intent names to handler functions (async if needed)
HANDLERS: Dict[str, Callable[..., Union[Any, Awaitable[Any]]]] = {
    'general': lambda text, **kwargs: "Nie obsługuję jeszcze tej intencji.",
    'about_assistant': lambda text, **kwargs: "Jestem asystentem AI. Zapytaj mnie o coś!",
    'weather_query': _get_handler_from_module_register(register_weather_command),
    'screenshot': _get_handler_from_module_register(register_screenshot_command),
    'search': _get_handler_from_module_register(register_search_module_command),
    'memory_add': _get_handler_from_module_register(register_memory_command, 'add'),
    # Custom handler for memory_get to always return all memories for AI
    'memory_get': _memory_get_with_full_memory,
}

# Custom handler for memory_get to always return all memories for AI
def _memory_get_with_full_memory(text, **kwargs):
    handler = _get_handler_from_module_register(register_memory_command, 'get')
    result = handler(text, **kwargs)
    if isinstance(result, dict) and 'all_memories' in result:
        return result
    return {'summary': result, 'success': True, 'all_memories': []}

HANDLERS.update({
    'memory_delete': _get_handler_from_module_register(register_memory_command, 'delete'),
    'deep_reasoning': _get_handler_from_module_register(register_deepseek_command),
    'timer_set': _get_handler_from_module_register(register_core_command, 'set_timer'),
    'timer_view': _get_handler_from_module_register(register_core_command, 'view_timers'),
    'event_add': _get_handler_from_module_register(register_core_command, 'add_event'),
    'event_view': _get_handler_from_module_register(register_core_command, 'view_calendar'),
    'reminder_set': _get_handler_from_module_register(register_core_command, 'set_reminder'),
    'reminder_view': _get_handler_from_module_register(register_core_command, 'view_reminders'),
    'shopping_add': _get_handler_from_module_register(register_core_command, 'add_item'),
    'shopping_view': _get_handler_from_module_register(register_core_command, 'view_list'),
    'shopping_remove': _get_handler_from_module_register(register_core_command, 'remove_item'),
    'task_add': _get_handler_from_module_register(register_core_command, 'add_task'),
    'task_view': _get_handler_from_module_register(register_core_command, 'view_tasks'),
    'task_complete': _get_handler_from_module_register(register_core_command, 'complete_task'),
    'task_remove': _get_handler_from_module_register(register_core_command, 'remove_task'),
    'none': lambda text, **kwargs: None,
})

#------------------------------------------------------------------------------
# Dispatcher
#------------------------------------------------------------------------------

# Map intent names to handler functions (async if needed)
# (moved above, unified with module-based approach)


async def handle_intent(text: str, **kwargs) -> Any: # Made async
    """
    Classify the input text and dispatch to the appropriate handler.
    If the intent corresponds to a registered command, it fetches command metadata.
    Returns whatever the handler returns.
    """
    intent, confidence = classify_intent(text)
    
    # Prepare kwargs for the specific handler, including original kwargs and confidence
    specific_handler_kwargs = {**kwargs, 'confidence': confidence}

    # Fetch command metadata if a registration function exists for the intent
    if intent in COMMAND_REGISTRATION_FUNCTIONS:
        register_func = COMMAND_REGISTRATION_FUNCTIONS[intent]
        if register_func: # Ensure the function is not None (e.g. if placeholder was not removed)
            try:
                command_info = register_func()
                specific_handler_kwargs['command_metadata'] = command_info
            except Exception as e:
                # Log error if metadata fetching fails, but continue
                print(f"Error fetching command metadata for intent '{intent}': {e}")


    handler_func = HANDLERS.get(intent, HANDLERS['none'])
    
    # Call the handler, awaiting if it's an async function
    if asyncio.iscoroutinefunction(handler_func):
        return await handler_func(text=text, **specific_handler_kwargs)
    else:
        return handler_func(text=text, **specific_handler_kwargs)

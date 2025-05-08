"""
Intent system for the assistant.
Uses trained model from intent_pipeline_multilang to classify user text and dispatch to handlers.
All handler functions are stubs and should be implemented according to business logic.
"""

import joblib
from typing import Tuple, Any, Dict
from performance_monitor import measure_performance


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
# Handler stubs for each intent
#------------------------------------------------------------------------------

def handle_general(text: str, **kwargs) -> Any:
    # TODO: Implement handling for general chit-chat intent
    pass


def handle_weather_query(text: str, **kwargs) -> Any:
    # TODO: Implement weather query logic
    pass


def handle_about_assistant(text: str, **kwargs) -> Any:
    # TODO: Implement information about assistant
    pass


def handle_screenshot(text: str, **kwargs) -> Any:
    # TODO: Implement screenshot capture
    pass


def handle_search(text: str, **kwargs) -> Any:
    # TODO: Implement web or local search
    pass


def handle_memory_add(text: str, **kwargs) -> Any:
    # TODO: Add entry to memory
    pass


def handle_memory_get(text: str, **kwargs) -> Any:
    # TODO: Retrieve entry from memory
    pass


def handle_memory_delete(text: str, **kwargs) -> Any:
    # TODO: Delete entry from memory
    pass


def handle_deep_reasoning(text: str, **kwargs) -> Any:
    # TODO: Implement deep reasoning logic
    pass


def handle_timer_set(text: str, **kwargs) -> Any:
    # TODO: Set a timer
    pass


def handle_timer_view(text: str, **kwargs) -> Any:
    # TODO: View existing timers
    pass


def handle_event_add(text: str, **kwargs) -> Any:
    # TODO: Add calendar event
    pass


def handle_event_view(text: str, **kwargs) -> Any:
    # TODO: View events
    pass


def handle_reminder_set(text: str, **kwargs) -> Any:
    # TODO: Set a reminder
    pass


def handle_reminder_view(text: str, **kwargs) -> Any:
    # TODO: View reminders
    pass


def handle_shopping_add(text: str, **kwargs) -> Any:
    # TODO: Add item to shopping list
    pass


def handle_shopping_view(text: str, **kwargs) -> Any:
    # TODO: View shopping list items
    pass


def handle_shopping_remove(text: str, **kwargs) -> Any:
    # TODO: Remove item from shopping list
    pass


def handle_task_add(text: str, **kwargs) -> Any:
    # TODO: Add task to to-do list
    pass


def handle_task_view(text: str, **kwargs) -> Any:
    # TODO: View tasks
    pass


def handle_task_complete(text: str, **kwargs) -> Any:
    # TODO: Mark task as complete
    pass


def handle_task_remove(text: str, **kwargs) -> Any:
    # TODO: Remove task from list
    pass

#------------------------------------------------------------------------------
# Dispatcher
#------------------------------------------------------------------------------

# Map intent names to handler functions
HANDLERS: Dict[str, Any] = {
    'general': handle_general,
    'weather_query': handle_weather_query,
    'about_assistant': handle_about_assistant,
    'screenshot': handle_screenshot,
    'search': handle_search,
    'memory_add': handle_memory_add,
    'memory_get': handle_memory_get,
    'memory_delete': handle_memory_delete,
    'deep_reasoning': handle_deep_reasoning,
    'timer_set': handle_timer_set,
    'timer_view': handle_timer_view,
    'event_add': handle_event_add,
    'event_view': handle_event_view,
    'reminder_set': handle_reminder_set,
    'reminder_view': handle_reminder_view,
    'shopping_add': handle_shopping_add,
    'shopping_view': handle_shopping_view,
    'shopping_remove': handle_shopping_remove,
    'task_add': handle_task_add,
    'task_view': handle_task_view,
    'task_complete': handle_task_complete,
    'task_remove': handle_task_remove,
    'none': lambda text, **kwargs: None,
}


def handle_intent(text: str, **kwargs) -> Any:
    """
    Classify the input text and dispatch to the appropriate handler.
    Returns whatever the handler returns.
    """
    intent, confidence = classify_intent(text)
    handler = HANDLERS.get(intent, HANDLERS['none'])
    # Pass text, confidence and other context to handler
    return handler(text=text, confidence=confidence, **kwargs)

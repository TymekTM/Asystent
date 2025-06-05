import json
import os
import tempfile
import time
import logging

logger = logging.getLogger(__name__)

STATE_FILE_NAME = 'assistant_state.json'

def get_state_file_path():
    """Get the path to the shared state file."""
    return os.path.join(tempfile.gettempdir(), STATE_FILE_NAME)

def save_assistant_state(is_listening=False, is_speaking=False, wake_word_detected=False, last_tts_text="", is_processing=False):
    """Save assistant state to shared file for cross-process communication."""
    try:
        state = {
            'is_listening': is_listening,
            'is_speaking': is_speaking,
            'is_processing': is_processing,
            'wake_word_detected': wake_word_detected,
            'last_tts_text': last_tts_text,
            'timestamp': time.time()        }
        
        state_file_path = get_state_file_path()
        with open(state_file_path, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        
        logger.info(f"Saved assistant state to {state_file_path}: {state}")
        
    except Exception as e:
        logger.error(f"Failed to save assistant state: {e}")

def load_assistant_state():
    """Load assistant state from shared file."""
    try:
        state_file_path = get_state_file_path()
        logger.debug(f"Trying to load state from: {state_file_path}")
        
        if not os.path.exists(state_file_path):
            logger.debug(f"State file does not exist: {state_file_path}")
            return None
            
        with open(state_file_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
            
        logger.debug(f"Raw loaded state: {state}")
            
        # Check if state is not too old (more than 10 seconds)
        current_time = time.time()
        state_time = state.get('timestamp', 0)
        
        logger.debug(f"Current time: {current_time}, State time: {state_time}, Diff: {current_time - state_time}")
        
        if current_time - state_time > 10:
            logger.debug("State file is too old, ignoring")
            return None
            
        logger.debug(f"Returning valid state: {state}")
        return state
        
    except Exception as e:
        logger.debug(f"Failed to load assistant state: {e}")
        return None

def update_wake_word_state(detected=False):
    """Update wake word detection state."""
    logger.info(f"Updating wake word state: detected={detected}")
    current_state = load_assistant_state() or {}
    current_state.update({
        'wake_word_detected': detected,
        'timestamp': time.time()
    })
    save_assistant_state(**{k: v for k, v in current_state.items() if k != 'timestamp'})

def update_listening_state(listening=False):
    """Update listening state."""
    logger.info(f"Updating listening state: listening={listening}")
    current_state = load_assistant_state() or {}
    current_state.update({
        'is_listening': listening,
        'timestamp': time.time()
    })
    save_assistant_state(**{k: v for k, v in current_state.items() if k != 'timestamp'})

def update_speaking_state(speaking=False):
    """Update speaking state."""
    current_state = load_assistant_state() or {}
    current_state.update({
        'is_speaking': speaking,
        'timestamp': time.time()
    })
    save_assistant_state(**{k: v for k, v in current_state.items() if k != 'timestamp'})

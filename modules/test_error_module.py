"""
Test module that simulates various error conditions to demonstrate
the AI fallback retry functionality.
"""

import random
import time

def handle_test_error_module(params: str = "", conversation_history=None, user_lang: str = "pl", assistant=None):
    """
    Test module that intentionally returns various error messages to test the AI fallback system.
    """
    error_types = [
        "Błąd połączenia z API testowym",
        "Przepraszam, wystąpił timeout podczas operacji",
        "Error: Failed to process test request",
        "API error: Invalid test response received",
        "Nie udało się wykonać operacji testowej",
        "Exception: Test module connection failed"
    ]
    
    # Randomly select an error type
    error_message = random.choice(error_types)
    
    # Add some realistic delay to simulate actual module processing
    time.sleep(0.5)
    
    return error_message

def handle_test_success_module(params: str = "", conversation_history=None, user_lang: str = "pl", assistant=None):
    """
    Test module that returns successful responses to contrast with error module.
    """
    success_responses = [
        "Test wykonany pomyślnie!",
        "Successfully completed test operation",
        "Operacja testowa zakończona powodzeniem",
        "Test results: All systems operational"
    ]
    
    return random.choice(success_responses)

def handle_test_exception_module(params: str = "", conversation_history=None, user_lang: str = "pl", assistant=None):
    """
    Test module that throws an actual exception to test exception handling.
    """
    # Simulate different types of exceptions
    exception_types = [
        ValueError("Invalid test parameter provided"),
        ConnectionError("Cannot connect to test service"),
        TimeoutError("Test operation timed out"),
        RuntimeError("Test module runtime error")
    ]
    
    raise random.choice(exception_types)


def get_manifest() -> dict:
    """Return plugin registration info for the assistant."""
    return {
        "test_error": {
            "handler": handle_test_error_module,
            "description": "Test module that returns error messages",
        },
        "test_success": {
            "handler": handle_test_success_module,
            "description": "Test module that returns success messages",
        },
        "test_exception": {
            "handler": handle_test_exception_module,
            "description": "Test module that throws exceptions",
        },
    }

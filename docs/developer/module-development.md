# Module Development Guide

This guide explains how to create custom modules for the Asystent system.

## Module System Overview

Asystent features a modular architecture that allows extending the assistant's functionality. Modules are Python files loaded dynamically from the `modules/` directory and can be toggled on/off via the web interface.

## Basic Module Structure

Create a new Python file named `<your_module>_module.py` in the `modules/` directory with the following structure.
The filename suffix `_module.py` is required for automatic module loading.

```python
import logging
import asyncio
from audio_modules.beep_sounds import play_beep
from collections import deque
from performance_monitor import measure_performance

logger = logging.getLogger(__name__)

# Main handler; can also accept 'user_lang' or other context params
@measure_performance
def handler(params: str = "", conversation_history: deque = None, user_lang: str = None, **kwargs) -> str:
    """
    Main function that processes requests to this module.
    
    Args:
        params: String containing user input after the command
        conversation_history: Optional deque of conversation messages
        user_lang: Detected language code
        **kwargs: Additional context parameters
        
    Returns:
        String response to be sent back to the user
    """
    try:
        # Optional: play a 'action' sound to signal execution
        play_beep("action")
        # Your module logic here
        result = process_input(params)
        return result
    except Exception as e:
        logger.error(f"Error in module: {e}", exc_info=True)
        return f"Error occurred: {e}"

def register():
    """
    Required function that returns module metadata.
    """
    return {
        "name": "my_module",          # Module name for internal reference
        "description": "What this module does (shown in module list)",
        "handler": handler,            # Main entry point function
        "aliases": ["module", "mm"],   # Commands that trigger this module
        # Optional elements below:
        # "prompt": "OPTIONAL_SYSTEM_PROMPT", # Custom system prompt for LLM
    }
```

## Module Components

### Required Elements

- **register() function**: Defines the module's metadata and integration points
- **handler function**: Processes requests to the module

### Optional Elements

- **Specialized prompts**: Custom instructions for the LLM when using this module
- **Sub-commands**: Nested functionality within your module
- **Helper functions**: Internal functionality not exposed directly
- **Async handlers**: For non-blocking operations

## Advanced Module Example

Here's an example of a more complex module with sub-commands:

```python
@measure_performance
def add_data(params: str, conversation_history: deque = None, **kwargs) -> str:
    """Add data to storage"""
    # Implementation...
    return f"Added: {params}"

@measure_performance
async def retrieve_data(params: str, conversation_history: deque = None, **kwargs) -> str:
    """Retrieve data from storage asynchronously"""
    # Async implementation... 
    result = await some_async_operation(params)
    return f"Found: {result}"

@measure_performance
def delete_data(params: str, conversation_history: deque = None, **kwargs) -> str:
    """Delete data from storage"""
    # Implementation...
    return f"Deleted: {params}"

def register():
    return {
        "name": "data_module",
        "description": "Manages data in the system",
        "aliases": ["data", "d"],
        "sub_commands": {
            "add": {
                "function": add_data,
                "description": "Add new data",
                "aliases": ["create", "insert"],
                "params_desc": "<content to add>"
            },
            "get": {
                "function": retrieve_data,
                "description": "Retrieve stored data",
                "aliases": ["retrieve", "find"],
                "params_desc": "[query]"
            },
            "delete": {
                "function": delete_data,
                "description": "Remove data",
                "aliases": ["remove"],
                "params_desc": "<identifier>"
            }
        }
    }
```

## Module Integration Points

### Conversation History Access

Your module receives the conversation history, allowing contextual operations:

```python
def context_aware_handler(params: str, conversation_history: deque = None, **kwargs) -> str:
    if conversation_history:
        recent_messages = list(conversation_history)[-3:]  # Get last 3 messages
        # Use context in processing...
    # Continue with module logic...
```

### Language Awareness

Modules receive the detected language for multilingual support:

```python
def language_aware_handler(params: str, user_lang: str = "en", **kwargs) -> str:
    responses = {
        "en": "The result is...",
        "pl": "Wynik to...",
    }
    return responses.get(user_lang, responses["en"])
```

### Sound Notifications

You can use the sound system to indicate operations:

```python
from audio_modules.beep_sounds import play_beep

def handler_with_sounds(params: str, **kwargs) -> str:
    play_beep("action")  # Types: "beep", "action", "success", "error", etc.
    # Module logic...
    return result
```

### LLM Integration

Access the language model directly for specialized processing:

```python
from ai_module import chat_with_providers, remove_chain_of_thought
from config import config

def llm_integrated_handler(params: str, **kwargs) -> str:
    messages = [
        {"role": "system", "content": "Specific instructions for this task"},
        {"role": "user", "content": params}
    ]
    
    response = chat_with_providers(
        model=config["AI"]["MAIN_MODEL"],
        messages=messages
    )
    
    result_text = remove_chain_of_thought(response["message"]["content"].strip())
    return result_text
```

### Performance Monitoring

Use the performance monitoring system to track function execution:

```python
from performance_monitor import measure_performance

@measure_performance
def my_function(params: str, **kwargs) -> str:
    # Implementation...
    return result
```

## Module State and Configuration

Modules are enabled or disabled via configuration in the database. The web interface allows toggling modules and reloading them without restarting the entire system.

The file watching system automatically detects changes to modules and reloads them in real-time during development.

## Asynchronous Support

For non-blocking operations, modules can define async handlers:

```python
async def async_handler(params: str, **kwargs) -> str:
    # Start a long-running operation
    result = await some_async_operation()
    return result
```

The module system automatically handles both synchronous and asynchronous functions.

## Active Window Context

Modules can access information about the currently active window for context-aware assistance:

```python
def window_aware_handler(params: str, active_window: dict = None, **kwargs) -> str:
    if active_window:
        app_name = active_window.get("app_name")
        window_title = active_window.get("window_title")
        # Use window context in processing...
    # Continue with module logic...
```

## Best Practices

1. **Error Handling**: Always wrap your main logic in try/except and provide meaningful error messages
2. **Logging**: Use the logger to record operations and errors
3. **Resource Management**: Close connections and free resources in a finally block
4. **Input Validation**: Verify parameters before processing
5. **Help Text**: Provide clear descriptions and parameter documentation
6. **Performance**: Use async for I/O-bound operations to avoid blocking
7. **Measurement**: Use the performance monitoring system to identify bottlenecks
8. **Language Handling**: Support multiple languages where possible
9. **User Experience**: Provide clear, helpful responses in a consistent format

## Example Modules

Study these existing modules for reference:

- **search_module.py**: Web search functionality
- **memory_module.py**: Long-term storage operations
- **deepseek_module.py**: Advanced reasoning capabilities
- **see_screen_module.py**: Screen capture and analysis
- **active_window_module.py**: Window context tracking

## Testing Your Module

1. Create a test file in `tests_unit/` (e.g., `test_my_module.py`)
2. Test the core functionality in isolation:

```python
import pytest
from modules.my_module_module import handler, process_input

def test_process_input():
    result = process_input("test input")
    assert "expected output" in result

def test_handler():
    response = handler("test command")
    assert response is not None
    assert isinstance(response, str)
    
def test_error_handling():
    # Test that the handler properly catches exceptions
    # and returns a user-friendly error message
    response = handler(None)  # Should trigger an exception
    assert "Error" in response
```

3. Run your tests using pytest:

```bash
pytest tests_unit/test_my_module.py -v
```

4. Consider adding integration tests that test how your module interacts with other system components in `tests_integration/`.

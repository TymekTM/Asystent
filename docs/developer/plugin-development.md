# Module Development Guide

This guide explains how to create custom modules for the Gaja system.

## Module System Overview

Gaja features a modular architecture that allows extending the AI assistant's functionality. Modules are Python files loaded dynamically from the `modules/` directory and can be toggled on/off via the web interface. The system now supports OpenAI Function Calling format for more precise command interpretation and parameter handling.

## Basic Module Structure

Create a new Python file named `<your_module>_module.py` in the `modules/` directory with the following structure.
The filename suffix `_module.py` is required for automatic module loading.

```python
import logging
from audio_modules.beep_sounds import play_beep
from collections import deque
from performance_monitor import measure_performance

logger = logging.getLogger(__name__)

# Main handler; can also accept 'user_lang' or other context params
@measure_performance
def handler(params: str = "", conversation_history: deque = None, user_lang: str = None, **kwargs) -> str:
    """
    Main function that processes requests to this plugin.
    
    Args:
        params: String containing user input after the command
        conversation_history: Optional list of conversation messages
        
    Returns:
        String response to be sent back to the user
    """
    try:
        # Optional: play a 'action' sound to signal execution
        play_beep("action")
        # Your plugin logic here
        result = process_input(params)
        return result
    except Exception as e:
        logger.error(f"Error in plugin: {e}", exc_info=True)
        return f"Error occurred: {e}"

def register():
    """
    Required function that returns module metadata.
    """
    return {
        "command": "my_module",       # Primary command name
        "aliases": ["module", "mm"],  # Optional alternative names
        "description": "What this module does (shown in tools list)",
        "handler": handler,           # Main entry point for this module
        # "prompt": "OPTIONAL_SYSTEM_PROMPT", # Optional: custom system prompt for LLM
        # "function_definition": {...}, # Optional: function calling specification
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
- **Function definitions**: Structured schema for function calling system

## Advanced Module Example

Here's an example of a more complex module with sub-commands. You can either define a top-level `handler` that accepts `{action: params}` dict, or list individual functions under `sub_commands` for automatic dispatch.

```python
@measure_performance
def add_data(params: str, conversation_history: deque = None, **kwargs) -> str:
    """Add data to storage"""
    # Implementation...
    return f"Added: {params}"

@measure_performance
async def retrieve_data(params: str, conversation_history: deque = None, **kwargs) -> str:
    """Retrieve data from storage asynchronously"""
    # Implementation... 
    return f"Found: {result}"

@measure_performance
def delete_data(params: str, conversation_history: deque = None, **kwargs) -> str:
    """Delete data from storage"""
    # Implementation...
    return f"Deleted: {params}"

def register():
    return {
        "command": "data_manager",
        "aliases": ["data", "dm"],
        "description": "Manages data in the system",
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

## Plugin Integration Points

### Conversation History Access

Your plugin receives the conversation history as a parameter, allowing contextual operations:

```python
def context_aware_handler(params: str, conversation_history: list = None) -> str:
    if conversation_history:
        recent_messages = conversation_history[-3:]  # Get last 3 messages
        # Use context in processing...
    # Continue with plugin logic...
```

### Sound Notifications

You can use the sound system to indicate operations:

```python
from audio_modules.beep_sounds import play_beep

def handler_with_sounds(params: str, conversation_history: list = None) -> str:
    play_beep("notification_type")  # Types: "beep", "search", "deep", etc.
    # Plugin logic...
    return result
```

### LLM Integration

Access the language model directly for specialized processing:

```python
from ai_module import chat_with_providers, remove_chain_of_thought
from config import MAIN_MODEL

def llm_integrated_handler(params: str, conversation_history: list = None) -> str:
    messages = [
        {"role": "system", "content": "Specific instructions for this task"},
        {"role": "user", "content": params}
    ]
    
    response = chat_with_providers(
        model=MAIN_MODEL,
        messages=messages
    )
    
    result_text = remove_chain_of_thought(response["message"]["content"].strip())
    return result_text
```

## Function Calling Integration

The module system now supports OpenAI Function Calling for precise parameter handling and command processing. You can define parameters and their types in the `register()` function:

```python
def register():
    return {
        "command": "weather",
        "aliases": ["pogoda", "forecast"],
        "description": "Gets weather information for a location",
        "handler": weather_handler,
        "function_schema": {  # OpenAI Function Calling schema
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name and country code (e.g., Warsaw,PL)"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "description": "Temperature units (metric for Celsius, imperial for Fahrenheit)"
                    }
                },
                "required": ["location"]
            }
        }
    }
```

When function calling is enabled, the AI will extract structured parameters from the user's request and provide them to your handler:

```python
def weather_handler(params: dict, **kwargs):
    location = params.get("location", "Warsaw,PL")
    units = params.get("units", "metric")
    # Process with validated parameters...
```

## Plugin States and Configuration

Plugins are enabled or disabled via the `plugins_state.json` file:

```json
{
  "plugins": {
    "my_plugin": {
      "enabled": true
    }
  }
}
```

The web interface allows toggling plugins and reloading them without restarting the entire system.

## Best Practices

1. **Error Handling**: Always wrap your main logic in try/except and provide meaningful error messages
2. **Logging**: Use the logger to record operations and errors
3. **Resource Management**: Close connections and free resources in a finally block
4. **Input Validation**: Verify parameters before processing
5. **Help Text**: Provide clear descriptions and parameter documentation
6. **Performance**: Avoid blocking operations in the main thread

## Example Plugins

Study these existing plugins for reference:

- **search_module.py**: Web search functionality
- **memory_module.py**: Long-term storage operations
- **deepseek_module.py**: Advanced reasoning capabilities
- **see_screen_module.py**: Screen capture and analysis

## Testing Your Plugin

1. Create a simple test file in `tests_unit/` (e.g., `test_my_plugin.py`)
2. Use pytest to verify your plugin's functionality
3. Run Gaja and test your plugin with direct commands

## Deploying Your Plugin

1. Place your plugin file in the `modules/` directory
2. Restart Gaja or use the reload function in the web UI
3. Verify your plugin appears in the plugins management page
4. Enable your plugin if it's not automatically enabled

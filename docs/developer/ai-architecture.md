# AI System Architecture

This document explains the AI layers and components that power the Gaja system, updated for version 1.2.0.

## AI Processing Pipeline

Gaja uses a multi-layered architecture to process inputs and generate intelligent responses:

```
Input → Wake Word → STT → Language Detection → Query Refinement → Intent Classification → LLM → Tool Use → TTS → Output
```

## Layer-by-Layer Breakdown

### 1. Input Processing

**Speech Recognition**
- **Wake Word Detection**: Continuously listens for a trigger phrase via `audio_modules/wakeword_detector.py` using openWakeWord.
- **Speech-to-Text (STT)**: Converts audio into text using Whisper (local or API) via `audio_modules/whisper_asr.py`.
  - Automatic language detection for multilingual support is handled by Whisper.

**Text Input**
- Web UI chat interface 
- Direct API calls
- Command queue processing

### 2. Query Processing Pipeline

Located primarily in `ai_module.py` and enhanced with function calling:

- **Language Detection**: Identifies input language with `detect_language` and `detect_language_async`
- **Query Refinement**: Preprocesses raw text to improve LLM performance via `refine_query`
- **Intent Classification**: Categorizes inputs via `intent_system.py` and routes to appropriate handlers
- **Function Calling System**: Extracts structured parameters from requests via `function_calling_system.py`

### 3. Conversation Management

- **History Management**: Tracks conversation context using deque in `assistant.py` (representing Gaja)
- **Memory System**: Long-term storage in `modules/memory_module.py` with database persistence
- **Context Preservation**: Maintains coherent conversation flow with dynamic token management
- **Active Window Context**: Tracks current application for contextual assistance via `modules/active_window_module.py`

### 4. Response Generation & Processing

Located in `ai_module.py`:

- **Multi-Provider Support**: Unified interface to multiple LLM providers via `chat_with_providers`
- **Generation**: `generate_response` and `generate_response_logic` functions handle LLM interaction
- **Post-Processing**: `remove_chain_of_thought` and `parse_response` clean up model output
- **Command Extraction**: `process_query` method identifies actions to perform with structured output parsing

### 5. Tool/Command Execution

- **Module System**: Dynamically loaded from the `modules/` directory with file watching for real-time updates
- **Intent Routing**: Commands mapped to appropriate module handlers via `intent_system.py`
- **Function Calling System**: Structured tool use via `function_calling_system.py` for more reliable command parsing
- **Core Modules**:
  - **API Integration**: External services in `modules/api_module.py`
  - **Web Search**: Internet lookup in `modules/search_module.py`
  - **Deep Reasoning**: Enhanced thinking in `modules/deepseek_module.py`
  - **Visual Analysis**: Screen capture in `modules/see_screen_module.py`
  - **Memory Management**: Long-term storage in `modules/memory_module.py`
  - **Daily Briefing**: Personalized summaries in `modules/daily_briefing_module.py`
  - **Music Control**: Media playback in `modules/music_module.py`
  - **Web Navigation**: Browser control in `modules/open_web_module.py`
  - **Core Utilities**: Timers, reminders, and tasks in `modules/core_module.py`
  - **Active Window**: Context tracking in `modules/active_window_module.py`
  - **Web Browser**: URL opening in `modules/open_web_module.py`

### 6. Text-to-Speech (TTS)

Located in `audio_modules/tts_module.py`:

- **Speech Synthesis**: Converts text to spoken output
- **Cancellation Support**: Interrupts ongoing speech for new responses
- **Async Processing**: Non-blocking speech generation with asyncio
- **Muting Control**: Conditional output based on interaction mode

### 7. Performance Monitoring

Located in `performance_monitor.py`:

- **Decorator-based Tracking**: `@measure_performance` for function timing
- **Resource Monitoring**: CPU, memory, and disk usage tracking
- **Response Time Analysis**: AI processing time measurements
- **Logging Integration**: Performance data stored for analysis

### 8. Multiprocessing Architecture

- **Main Process** (`main.py`): Runs the Web UI
- **Gaja Process** (spawned by `main.py`): Handles AI assistant functionality
- **Inter-Process Communication**: Uses multiprocessing Queue
- **Asynchronous Operations**: Uses asyncio for non-blocking operations

## LLM Provider Integration

The system supports multiple LLM providers through a unified interface:

- **OpenAI**: GPT models via API
- **Ollama**: Local models with various sizes
- **DeepSeek**: Specialized reasoning models
- **Anthropic**: Claude models via API

Integration is managed via the `ai_module.py` file with appropriate configuration settings and model-specific handling.

## Data Flow

1. **Input Capture**: Voice or text is received through UI or microphone
2. **Language Processing**: Input is analyzed, language detected, and query refined
3. **Intent Classification**: System determines the purpose of the query
4. **Context Assembly**: Conversation history, active window context, and relevant memories are gathered
5. **LLM Interaction**: Prepared context is sent to the selected language model
6. **Response Parsing**: Model output is structured into text and potential commands
7. **Function Calling**: Structured parameters are extracted and validated if function calling is enabled
8. **Tool Execution**: If needed, specific module functions are invoked based on intent or function calls
9. **Response Delivery**: Generated output is spoken via TTS and/or displayed in UI
10. **Memory & History Update**: Conversation is stored and relevant information is added to long-term memory

## Extending the AI System

### Adding New LLM Providers

1. Update `ai_module.py` with the new provider's API integration in `chat_with_providers`
2. Add configuration options in `config.py` and ensure they're loaded properly
3. Update the web UI configuration page with provider-specific settings
4. Implement provider-specific handling for features like streaming, tool use, etc.
5. Add appropriate error handling and fallback mechanisms

### Function Calling System

The Function Calling System enhances the AI's ability to understand and execute structured commands:

1. **Module Schema Conversion**: Existing modules are automatically converted to function schemas
2. **Parameter Extraction**: The AI model extracts and validates parameters from user requests
3. **Type Validation**: Parameters are validated against their declared types
4. **Handler Mapping**: Function calls are mapped to appropriate module handlers
5. **Response Formatting**: Results are formatted according to the module's response type

To leverage function calling in your modules:

```python
def register():
    return {
        "command": "weather",
        "description": "Get weather information",
        "handler": weather_handler,
        "function_schema": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name (e.g., Warsaw)"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "description": "Temperature units"
                    }
                },
                "required": ["location"]
            }
        }
    }
```

### Creating New Modules

1. Add a new module to the `modules/` directory with a `_module.py` suffix
2. Implement the required `register()` function with appropriate command definitions:
   ```python
   def register():
       return {
           "command": "your_module_name",
           "description": "Module description",
           "handler": your_handler_function,
           "aliases": ["alias1", "alias2"],
           "function_schema": {
               "name": "function_name",
               "description": "Function description",
               "parameters": {
                   "type": "object",
                   "properties": {
                       "param_name": {
                           "type": "string",
                           "description": "Parameter description"
                       }
                   }
               }
           },
           "sub_commands": {
               "subcmd": {
                   "function": subcmd_handler,
                   "description": "Subcommand description",
                   "aliases": ["sub_alias"]
               }
           }
       }
   ```
3. Create handler functions for processing requests
4. Ensure your module is discoverable through the file watching system
5. Add module-specific configuration if needed

### Customizing the Prompt System

The prompt system has been enhanced with dynamic building features in `prompt_builder.py`:

- `build_full_system_prompt`: Assembles the complete system prompt
- `build_system_prompt`: Creates the base system instructions
- `build_language_info_prompt`: Adds language detection information
- `build_tools_prompt`: Incorporates available tools information
- `build_active_window_prompt`: Adds context about the current application

System prompts in `prompts.py` can be modified to:
- Change Gaja's personality
- Add specialized knowledge
- Adjust response formatting
- Enhance reasoning capabilities
- Update tool descriptions
- Modify language handling

### Performance Optimization

To improve system performance:
1. Use the `@measure_performance` decorator to identify bottlenecks
2. Consider enabling LOW_POWER_MODE for resource-constrained environments
3. Adjust model selection based on complexity requirements
4. Use async operations for I/O-bound tasks
5. Implement caching for frequently accessed data
6. Profile memory usage and optimize data structures (e.g., using deque for conversation history)

# AI System Architecture

This document explains the AI layers and components that power the Asystent system.

## AI Processing Pipeline

Asystent uses a multi-layered architecture to process inputs and generate intelligent responses:

```
Input → Wake Word → STT → Query Processing → LLM → Tool Use → TTS → Output
```

## Layer-by-Layer Breakdown

### 1. Input Processing

**Speech Recognition**
- **Wake Word Detection**: Continuously listens for a trigger phrase
- **Speech-to-Text (STT)**: Converts audio into text using either:
  - Vosk (offline, lightweight)
  - Whisper (higher accuracy)

**Text Input**
- Web UI chat interface
- Direct API calls

### 2. Query Processing Pipeline

Located primarily in `ai_module.py`:

- **Query Refinement**: Preprocesses raw text to improve LLM performance
- **Intent Classification**: Categorizes inputs (in `assistant.py` - `IntentClassifier` class)

### 3. Conversation Management

- **History Management**: Tracks conversation context in `assistant.py`
- **Memory System**: Long-term storage in `modules/memory_module.py`
- **Context Preservation**: Maintains coherent conversation flow within token limits

### 4. Response Generation & Processing

Located in `ai_module.py`:

- **Generation**: `generate_response` function handles LLM interaction
- **Post-Processing**: `remove_chain_of_thought` and `parse_response` clean up model output
- **Command Extraction**: `process_query` method identifies actions to perform

### 5. Tool/Command Execution

- **Module System**: Dynamically loaded from the `modules/` directory
- **Core Modules**:
  - **API Integration**: External services in `modules/api_module.py`
  - **Web Search**: Internet lookup in `modules/search_module.py`
  - **Deep Reasoning**: Enhanced thinking in `modules/deepseek_module.py`
  - **Visual Analysis**: Screen capture in `modules/see_screen_module.py`
  - **Memory Management**: Long-term storage in `modules/memory_module.py`

### 6. Text-to-Speech (TTS)

Located in `audio_modules/tts_module.py`:

- **Speech Synthesis**: Converts text to spoken output
- **Cancellation Support**: Interrupts ongoing speech for new responses
- **Audio Queuing**: Manages multiple speech segments

### 7. Web UI Integration

Located in `web_ui/app.py`:

- **Configuration Interface**: System settings management
- **Conversation History**: Records of interactions
- **Long-Term Memory Management**: UI for memory operations

### 8. Multiprocessing Architecture

- **Main Process** (`main.py`): Runs the Web UI
- **Assistant Process** (spawned by `main.py`): Handles AI assistant functionality
- **Inter-Process Communication**: Uses multiprocessing Queue

## LLM Provider Integration

The system supports multiple LLM providers:

- **OpenAI**: GPT models via API
- **Ollama**: Local models
- **DeepSeek**: Specialized reasoning
- **Anthropic**: Claude models

Integration is managed via the `ai_module.py` file with appropriate configuration settings.

## Data Flow

1. **Input**: Voice or text is received
2. **Processing**: Input is analyzed, intent classified, and context established
3. **LLM Interaction**: Prepared context is sent to language model
4. **Tool Use**: If needed, special functions are invoked based on intent
5. **Response**: Generated output is processed and delivered
6. **Memory Update**: Relevant information is stored for future reference

## Extending the AI System

### Adding New LLM Providers

1. Update `ai_module.py` with the new provider's API integration
2. Add configuration options in `config.py`
3. Update the web UI configuration page

### Creating New Tools/Commands

1. Add a new module to the `modules/` directory
2. Implement the `register()` function with appropriate command definition
3. Create the handler function for processing requests
4. Update `plugins_state.json` to enable the new module

### Customizing the Prompt System

System prompts in `prompts.py` can be modified to:
- Change the assistant's personality
- Add specialized knowledge
- Adjust response formatting
- Enhance reasoning capabilities

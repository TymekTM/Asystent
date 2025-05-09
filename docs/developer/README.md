# Developer Setup Guide

This guide will help you set up a development environment for Asystent and understand the system architecture. Updated for version 1.1.0.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Project Structure](#project-structure)
4. [Architecture Overview](#architecture-overview)
5. [Core Components](#core-components)
6. [Module Development](#module-development)
7. [Performance Monitoring](#performance-monitoring)
8. [Testing](#testing)

## Prerequisites

Before setting up Asystent for development, ensure you have:

- Python 3.10 or higher
- Git
- FFmpeg (for audio processing)
- Compatible speech-to-text models:
  - Vosk model files (for offline recognition)
  - Whisper model setup (for higher accuracy)
- Access to LLM providers:
  - OpenAI API key for GPT models
  - Ollama for local model hosting
  - DeepSeek API access (optional)
  - Anthropic API access (optional)

### Required Python Libraries

The main dependencies are listed in `requirements.txt` and include:

- Flask (web interface and API)
- SQLite (database for memory and configuration)
- Edge-TTS (for text-to-speech)
- OpenAI/Ollama/DeepSeek/Anthropic libraries (LLM providers)
- Watchdog (for file monitoring)
- Transformers (for language detection and model handling)
- SoundDevice and related audio libraries
- DXcam and PIL for screen capture
- Joblib for model serialization

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/asystent.git
   cd asystent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Linux/Mac
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Download required models:
   - For Vosk: Download a model from https://alphacephei.com/vosk/models and extract it to `vosk_model/`
   - For Whisper: The first run will automatically download the selected model

5. Set up configuration:
   - Copy `config.json.example` to `config.json`
   - Edit `config.json` with your API keys and preferences

6. Run the development server:
   ```bash
   python main.py
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the application:
   - Copy `config.json.example` to `config.json` if it doesn't exist
   - Edit settings as needed (API keys, model paths, etc.)

5. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

The project is organized for modularity and maintainability:

```
asystent/
├── main.py                 # Application entry point
├── assistant.py            # Core assistant logic
├── ai_module.py            # LLM integration with multiple providers
├── ai_layers.txt           # Layer structure for AI processing
├── config.py               # Configuration management
├── prompt_builder.py       # Dynamic prompt construction
├── prompts.py              # System prompt templates
├── database_manager.py     # Database interface
├── database_models.py      # Database schema definitions
├── intent_system.py        # Intent detection and routing
├── performance_monitor.py  # Performance tracking
├── audio_modules/          # Audio processing components
│   ├── beep_sounds.py      # Audio feedback system
│   ├── list_audio_devices.py # Audio device management
│   ├── speech_recognition.py # Speech input handling
│   ├── tts_module.py       # Text-to-speech system
│   ├── whisper_asr.py      # Whisper integration for STT
│   └── wakeword_detector.py # Wake word detection system
├── modules/                # Pluggable functionality modules
│   ├── active_window_module.py # Active window tracking
│   ├── api_module.py       # External API integration
│   ├── api_integrations_config.json # API configuration 
│   ├── core_module.py      # Core system utilities
│   ├── core_storage.json   # Core module data storage
│   ├── deepseek_module.py  # Advanced reasoning
│   ├── memory_module.py    # Long-term memory management
│   ├── memory/             # Memory storage files 
│   ├── open_web_module.py  # Web browser control
│   ├── search_module.py    # Web search capability
│   ├── see_screen_module.py # Screenshot and analysis
│   └── weather_module.py   # Weather information
├── resources/              # Resource files
│   ├── Intent_AI/          # Intent classification models
│   ├── piper/              # Voice files for TTS
│   └── sounds/             # System sounds
├── screenshots/            # Captured screenshots
├── tests_integration/      # Integration tests
├── tests_pytest/           # Pytest configurations
├── tests_unit/             # Unit tests
├── vosk_model/             # Vosk model files
├── web_ui/                 # Web interface files
│   ├── app.py              # Flask web server
│   ├── routes/             # API routes
│   ├── static/             # CSS, JS, and assets
│   └── templates/          # HTML templates
├── CHANGELOG.md            # Version history
├── README.md               # Project overview
├── requirements.txt        # Dependencies
└── config.json             # Configuration file
│   ├── wakeword_detector.py # Wake word activation
│   └── whisper_asr.py      # Whisper integration
├── modules/               # Functional modules
│   ├── active_window_module.py  # Active window tracking
│   ├── api_module.py      # External API integration
│   ├── core_module.py     # Core system functions
│   ├── deepseek_module.py # Advanced reasoning
│   ├── memory_module.py   # Memory management
│   ├── open_web_module.py # Web browser control
│   ├── search_module.py   # Web search functionality
│   ├── see_screen_module.py # Screen capture and analysis
│   └── weather_module.py  # Weather information
├── resources/            # Static resources
│   ├── Intent_AI/        # Intent classification models
│   ├── piper/            # TTS voice models
│   └── sounds/           # System sound files
├── web_ui/              # Web interface
│   ├── app.py           # Flask application
│   ├── static/          # Static assets (JS, CSS)
│   └── templates/       # HTML templates
├── tests_unit/         # Unit tests
├── tests_integration/  # Integration tests
├── tests_pytest/       # Pytest configuration
└── docs/               # Documentation
```

## Architecture Overview

Asystent uses a multi-process architecture with these main components:

1. **Assistant Process**: Manages voice interaction, AI processing, and core functionality
2. **Web Server Process**: Handles the web UI and API endpoints
3. **Inter-process Communication**: Uses shared queues for messaging between processes

The system is designed with these key architectural principles:

- **Modularity**: Functionality is divided into pluggable modules
- **Asynchronous Operation**: Uses asyncio for non-blocking operations
- **Stateful Conversations**: Maintains context across interactions
- **Multi-modal Interaction**: Supports voice, text, and visual inputs/outputs
- **Extensible Module System**: Allows adding new capabilities with minimal changes
- **Performance Monitoring**: Decorator-based timing and resource tracking
- **Dynamic Reconfiguration**: Hot-reload capability for modules and settings
- **Multi-provider AI**: Unified interface to multiple LLM providers
- **Context Awareness**: Active window tracking and conversation history

## Core Components

### Assistant Class

The `Assistant` class in `assistant.py` is the central coordinator that:
- Initializes and manages all subsystems
- Handles the main interaction loop via asyncio
- Routes commands to appropriate handlers
- Manages conversation state with deque
- Coordinates speech recognition and response generation
- Monitors system performance
- Handles file system events for dynamic module loading

Key methods:
- `run_async()`: Main execution loop with event handling
- `process_query()`: Processes user input with language detection and intent classification
- `process_audio()`: Manages audio input and wake word detection
- `load_plugins()`: Dynamically loads and updates modules
- `trigger_manual_listen()`: Activates listening without wake word

### AI Module

The `ai_module.py` file provides a unified interface to multiple LLM providers:
- OpenAI (GPT models)
- Ollama (local models)
- DeepSeek
- Anthropic (Claude)

Key functions:
- `chat_with_providers()`: Routes requests to the appropriate provider with fallback logic
- `generate_response()`: Creates AI responses using the selected model
- `generate_response_logic()`: Core generation logic with provider handling
- `refine_query()`: Enhances user queries for better understanding
- `detect_language()` and `detect_language_async()`: Identifies input language
- `parse_response()`: Extracts structured data from AI responses

### Speech Processing

Speech processing is handled by specialized modules in the `audio_modules/` directory:
- `speech_recognition.py`: Records and processes audio input using Vosk
- `wakeword_detector.py`: Listens for the activation phrase with async handling
- `whisper_asr.py`: High-accuracy transcription with Whisper models
- `tts_module.py`: Converts text responses to spoken audio with Edge TTS
- `beep_sounds.py`: Provides audio feedback for system events
- `list_audio_devices.py`: Manages audio device enumeration and selection

### Intent System

The intent system in `intent_system.py` routes commands to the appropriate handlers:
- Classifies user intent using trained models with Joblib
- Maps intents to handler functions in various modules
- Supports function extraction from AI responses
- Provides unified intent routing with `handle_intent()`
- Manages sub-command registry with aliases
- Supports both sync and async handler functions

### Module System

Functional capabilities are organized into modules in the `modules/` directory:
- Each module provides specific functionality through a standard interface
- Modules register commands with the `register()` function
- File watching system detects module changes in real-time
- Modules support sub-commands and aliases
- Configuration and state are persisted as needed
- Module loading/unloading handled by watchdog events

### Web Interface

The web UI in `web_ui/app.py` provides:
- User interface for interacting with the assistant
- Configuration management
- System monitoring and control
- API endpoints for external integration
- User authentication and session management

### Configuration System

The configuration system in `config.py`:
- Loads settings from `config.json`
- Provides defaults for missing values
- Validates configuration parameters
- Allows runtime updates to most settings
- Exports configuration for use throughout the application

## Module Development

To develop modules for Asystent, follow these guidelines:

1. **Module Creation**: Create a new file in the `modules/` directory with a `_module.py` suffix
2. **Registration Function**: Implement a `register()` function that returns module metadata:
   ```python
   def register():
       return {
           "name": "your_module",
           "description": "Module description",
           "handler": your_main_handler,
           "aliases": ["alias1", "alias2"],  # Optional
           "sub_commands": {  # Optional
               "subcommand_name": {
                   "function": subcommand_handler,
                   "description": "Subcommand description",
                   "aliases": ["sub_alias1"]
               }
           }
       }
   ```
3. **Handler Implementation**: Create handler functions that receive and process parameters:
   ```python
   def your_main_handler(params, **kwargs):
       # Process request and return result
       return "Result text"
   ```
4. **Access Context**: Handlers can receive additional context through kwargs:
   - `conversation_history`: Access to conversation history
   - `user_lang`: Detected language code
   - Other contextual information

5. **Async Support**: Handlers can be asynchronous for non-blocking operations:
   ```python
   async def async_handler(params, **kwargs):
       result = await some_async_operation()
       return result
   ```

6. **Testing**: Create tests in the appropriate test directories
7. **Documentation**: Update the plugin documentation in `docs/user-guide/plugins.md`

## Performance Monitoring

Asystent includes a comprehensive performance monitoring system:

### Decorator-based Tracking

Use the `@measure_performance` decorator to track function execution time:
```python
from performance_monitor import measure_performance

@measure_performance
def your_function():
    # Function code
```

### Key Features

- **Function Timing**: Tracks execution time for decorated functions
- **Resource Monitoring**: CPU, memory, and disk usage statistics
- **Response Metrics**: AI processing and generation times
- **Structured Logging**: JSON-formatted performance data
- **Visualization**: Performance graphs in the web UI
- **Bottleneck Identification**: Helps locate performance issues
- **Historical Data**: Performance trends over time

### Performance Logs

Performance data is stored in `performance_stats.jsonl` for analysis and can be viewed in the web UI's Performance page.

## Testing

The codebase includes a comprehensive testing suite:

### Test Types

1. **Unit Tests** (`tests_unit/`): Test individual functions and components in isolation
2. **Integration Tests** (`tests_integration/`): Test interactions between multiple components
3. **Pytest Setup** (`tests_pytest/`): Configuration and fixtures for pytest
4. **Manual Tests**: Documented procedures for human verification

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests_unit/test_file.py

# Run with coverage report
pytest --cov=.

# Run with verbose output
pytest -v
```

### Test Guidelines

When creating tests:

1. **Unit Tests**: Focus on testing a single function or class in isolation
   - Mock external dependencies
   - Test edge cases and error conditions
   - Verify expected output for known inputs

2. **Integration Tests**: Test how components work together
   - Minimize mocking where possible
   - Test realistic user scenarios
   - Verify system behavior end-to-end

3. **Test Structure**:
   - Use descriptive test names
   - Follow the Arrange-Act-Assert pattern
   - Group related tests with appropriate fixtures

4. **CI Integration**: 
   - Tests are automatically run on commits
   - Failed tests block merges
   - Coverage reports are generated automatically

# Developer Setup Guide

This guide will help you set up a development environment for Asystent and understand the system architecture.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Project Structure](#project-structure)
4. [Architecture Overview](#architecture-overview)
5. [Core Components](#core-components)
6. [Plugin Development](#plugin-development)
7. [Testing](#testing)

## Prerequisites

Before setting up Asystent, ensure you have:

- Python 3.10 or higher
- Git
- FFmpeg (for audio processing)
- A compatible speech-to-text model (Vosk or Whisper)
- Access to LLM providers (local or API-based)

### Required Python Libraries

The main dependencies are listed in `requirements.txt` and include:

- Flask (web interface)
- SQLite (database)
- OpenAI/Ollama/DeepSeek libraries (LLM providers)
- SoundDevice and related audio libraries

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/asystent.git
   cd asystent
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

```
asystent/
├── main.py                 # Application entry point
├── assistant.py            # Core assistant logic
├── ai_module.py            # LLM integration
├── config.py               # Configuration management
├── prompts.py              # System prompts
├── database_manager.py     # Database interface
├── database_models.py      # Database schema
├── audio_modules/          # Audio processing components
│   ├── speech_recognition.py
│   ├── tts_module.py
│   ├── wakeword_detector.py
│   └── ...
├── modules/                # Plugin modules
│   ├── api_module.py
│   ├── search_module.py
│   ├── memory_module.py
│   └── ...
├── web_ui/                 # Web interface
│   ├── app.py              # Flask application
│   ├── templates/          # HTML templates
│   └── static/             # CSS, JS, assets
├── tests_unit/             # Unit tests
└── tests_integration/      # Integration tests
```

## Architecture Overview

Asystent uses a layered architecture with these main components:

1. **Input Processing**: Wake word detection, speech-to-text conversion
2. **Query Processing**: Intent classification, query refinement
3. **Conversation Management**: History tracking, memory system
4. **Response Generation**: LLM integration, post-processing
5. **Tool/Command Execution**: Dynamic plugin system
6. **Output Processing**: Text-to-speech, web UI updates

The application runs two main processes:
- Assistant process (voice interactions)
- Web UI process (Flask server)

These processes communicate via a multiprocessing queue.

## Core Components

### Assistant Class (`assistant.py`)

The central controller that:
- Manages audio input/output
- Processes commands
- Handles conversation history
- Orchestrates module/plugin interactions

### AI Module (`ai_module.py`)

Manages interactions with language models:
- Formats prompts and messages
- Routes queries to appropriate providers
- Post-processes responses

### Database Systems

Two main storage systems:
- **SQLite DB** (`database_manager.py`): Structured storage for memories, users, etc.
- **Config System** (`config.py`): JSON-based configuration management

### Web UI (`web_ui/app.py`)

Flask-based web interface that:
- Provides control panel functionality
- Exposes REST API endpoints
- Renders the user interface

## Plugin Development

Create new plugins by adding modules to the `modules/` directory.

### Plugin Structure

Each plugin must have:

```python
def register():
    return {
        "command": "plugin_name",  # Command to invoke the plugin
        "aliases": ["alternate_name", "another_name"],  # Alternative commands
        "description": "What the plugin does",  # For help systems
        "handler": plugin_handler_function,  # Main function
        "prompt": "OPTIONAL_PROMPT"  # System prompt for LLM context
    }
```

The handler function should have this signature:

```python
def plugin_handler_function(params: str = "", conversation_history: list = None) -> str:
    # Process the params
    # Return a response string
```

### Enabling Plugins

Plugins are managed via the `plugins_state.json` file:

```json
{
  "plugins": {
    "your_plugin_name": {
      "enabled": true
    }
  }
}
```

## Testing

### Unit Tests

Run unit tests with:

```bash
python -m pytest tests_unit/
```

Unit tests focus on individual components and mock dependencies.

### Integration Tests

Run integration tests with:

```bash
python -m pytest tests_integration/
```

These tests verify end-to-end functionality.

### Test Interface

The Dev section in the web UI provides a test runner with:
- Test execution
- Status reporting
- History tracking
- AI-generated test summaries

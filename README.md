# Asystent - Advanced AI Assistant System

Asystent is a powerful AI assistant system that provides interactive natural language processing through text, voice, and web interfaces. It's designed to be modular, extensible, and adaptable to various usage scenarios.

## Features

- **Multi-modal interaction:** Communicate via text chat, voice commands, or web UI
- **Wake word detection:** Activate voice interaction with a customizable trigger phrase
- **Multiple LLM support:** Compatible with OpenAI, Ollama, DeepSeek, and Anthropic models
- **Voice capabilities:** Advanced speech-to-text (STT) and text-to-speech (TTS)
- **Long-term memory:** Persistent storage of conversation history and important information
- **Modular plugin system:** Easily extend functionality with custom plugins
- **Tool integration:** Built-in tools for web search, API connections, screen analysis, and more
- **Web control panel:** Configure, monitor, and interact with the system via browser

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Git (for cloning the repository)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/asystent.git
cd asystent
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Configure your settings in `config.json` or via the web interface

4. Run the application:
```bash
python main.py
```

## Usage

### Web Interface

Access the control panel by navigating to http://localhost:5000 in your browser after starting the application.

### Voice Interaction

1. Start the application with voice support enabled
2. Use the wake word (default: "Hey Assistant") to begin voice interaction
3. Speak your command or question

### API Integration

Asystent provides REST API endpoints for programmatic interaction. See the [API documentation](docs/api/README.md) for details.

## Documentation

Comprehensive documentation is available in the following sections:

- [User Guide](docs/user-guide/README.md) - How to use Asystent
- [Developer Guide](docs/developer/README.md) - Technical information and setup instructions
- [API Documentation](docs/api/README.md) - API reference and integration guides

## Development

To contribute to Asystent:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- OpenAI, Ollama, DeepSeek, and Anthropic for their language models
- Flask for the web framework
- All contributors who have helped build and improve Asystent

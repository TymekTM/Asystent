# LEGACY CODEBASE LOOK AT [NEW REPOSITORY](https://github.com/TymekTM/Gaja)

# Gaja - Advanced AI Assistant System (v1.2.0)

Gaja is a powerful AI assistant system that provides interactive natural language processing through text, voice, and web interfaces. It's designed to be modular, extensible, and adaptable to various usage scenarios. With its new Daily Briefing capability and enhanced API, version 1.2.0 brings even more functionality to users.

## Features

- **Multi-modal interaction:** Communicate via text chat, voice commands, or web UI
- **Wake word detection:** Activate voice interaction with a customizable trigger phrase
- **Multiple LLM support:** Compatible with OpenAI, Ollama, DeepSeek, and Anthropic models
- **Voice capabilities:** Advanced speech-to-text (STT) and text-to-speech (TTS)
- **Long-term memory:** Persistent storage of conversation history and important information
- **Modular plugin system:** Easily extend functionality with custom plugins
- **Tool integration:** Built-in tools for web search, API connections, screen analysis, and more
- **Web control panel:** Configure, monitor, and interact with the system via browser
- **Daily Briefings:** AI-generated personalized daily summaries with weather and memory integration
- **RESTful API:** Comprehensive API for external system integration
- **Documentation Integration:** Web UI integrated documentation viewer

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Git (for cloning the repository)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gaja.git
cd gaja
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Configure your settings:
   - Create a `config.json` file from `dummy_config.json`
   - Add your API keys and customize settings
   - Or configure via the web interface after first run

4. Run the application:
```bash
python main.py
```

5. Build an executable (optional):
```bash
python build.py
```
   See [README_BUILD.md](README_BUILD.md) for detailed build instructions.

## Usage

### Web Interface

Access the control panel by navigating to http://localhost:5000 in your browser after starting the application. Default login credentials are:
- Username: `dev` or `user`
- Password: `devpassword` or `password`

### Voice Interaction

1. Start the application with voice support enabled
2. Use the wake word (default: "gaja") to begin voice interaction
3. Speak your command or question
4. Or click the "Activate" button in the web UI to listen without a wake word

### API Integration

Gaja provides REST API endpoints for programmatic interaction. See the [API documentation](docs/api/README.md) for details.

## Documentation

Comprehensive documentation is available in the following sections:

- [User Guide](docs/user-guide/README.md) - How to use Gaja
- [Developer Guide](docs/developer/README.md) - Technical information and setup instructions
- [API Documentation](docs/api/README.md) - API reference and integration guides

## Development

To contribute to Gaja:

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
- All contributors who have helped build and improve Gaja

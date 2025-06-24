# 🤖 GAJA Assistant

[![Coverage](./coverage.svg)](./coverage.svg)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Advanced AI-powered voice assistant with user mode system and real-time overlay interface.**

## 🚀 Quick Start

### 🐳 With Docker (Recommended)

```bash
# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Start with CPU support
docker-compose up -d

# Or start with GPU support
docker-compose --profile gpu up -d
```

### 🐍 Traditional Python Setup

```bash
# Install dependencies with Poetry
poetry install

# Start client (voice assistant)
poetry run python -m gaja_client.main

# Start server (AI processing)
poetry run python -m gaja_server.main

# Start web UI (configuration)
cd web_ui && python app.py
```

### 🧪 Development Setup

```bash
# Install development dependencies
poetry install --with dev

# Install pre-commit hooks
poetry run pre-commit install

# Run tests
poetry run pytest

# Run linting
poetry run ruff check .
poetry run black --check .
```

For detailed Docker setup, see [README_DOCKER.md](README_DOCKER.md)

## 📁 Project Structure

```
f:\Asystent\
├── 📦 src/                 # Source code (new structure)
│   ├── gaja_server/        # AI processing server
│   ├── gaja_client/        # Voice assistant client
│   └── gaja_core/          # Shared utilities
├── 🐳 docker/              # Docker configuration
│   ├── Dockerfile          # Multi-stage build
│   ├── nginx.conf          # Reverse proxy config
│   └── init-db.sql         # Database initialization
├── 🔄 .github/workflows/   # CI/CD pipelines
├── 🎙️ client/              # Voice assistant client (legacy)
├── 🧠 server/              # AI processing server (legacy)
├── 🌐 web_ui/              # Web configuration interface
├── 🎨 overlay/             # Visual status overlay
├── 🔊 audio_modules/       # TTS, STT, wake word detection
├── 🧩 modules/             # Feature modules (weather, music, etc.)
├── 🧪 tests/               # Testing utilities
│   ├── performance/        # Load and performance tests
│   ├── integration/        # Component integration tests
│   └── debug/              # Debug and diagnostic tools
├── 🎭 demos/               # Feature demonstration scripts
├── 📊 reports/             # Test reports and documentation
├── ⚙️ configs/             # Configuration files
├── 📚 docs/                # Documentation
├── 📝 pyproject.toml       # Poetry configuration
├── 🐳 docker-compose.yml   # Docker orchestration
└── 🔧 .pre-commit-config.yaml  # Code quality hooks
```

## ✨ Key Features

### 🎯 User Mode System

- **Poor Man Mode**: Free Edge TTS + Local Whisper
- **Paid User Mode**: OpenAI TTS + OpenAI Whisper
- **Enterprise Mode**: Azure TTS + Azure Whisper

### 🎙️ Voice Capabilities

- Wake word detection ("Gaja")
- Real-time speech recognition
- Natural language processing
- Text-to-speech responses

### 🖥️ Interface Options

- Voice-only interaction
- Visual overlay with status
- Web UI for configuration
- Desktop notifications

### 🧠 AI Features

- Context-aware conversations
- Memory system with persistence
- Function calling (weather, music, web search)
- Advanced prompt engineering

## 🛠️ Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd GAJA-Assistant
```

### 2. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Client dependencies
pip install -r client/requirements_client.txt

# Server dependencies
pip install -r server/requirements_server.txt

# Demo dependencies (optional)
pip install -r demos/requirements_user_modes.txt
```

### 3. Configuration

```bash
# Copy and edit configuration
cp dummy_config.json config.json

# Add your API keys
nano config.json
```

### 4. First Run

```bash
# Run setup wizard
python setup_wizard.py

# Or quick start
python quick_start.py
```

## 🧪 Testing

### Performance Testing

```bash
cd tests/performance
python concurrent_users_test.py    # Full load testing (100-10k users)
python quick_perf_test.py          # Quick performance check
```

### Integration Testing

```bash
cd tests/integration
python test_client_integration.py  # Client compatibility test
```

### Feature Demos

```bash
cd demos
python demo_user_modes.py          # User mode system demo
python demo_enhanced_tts.py        # TTS providers demo
```

## 📊 Performance

**Tested with concurrent users:**

- ✅ **200 users**: 100% success, <1s response time
- ⚠️ **1000 users**: 54.5% success (API rate limited)
- 🚀 **Peak throughput**: 323.8 requests/second

## 🔧 Development

### Core Modules

- `user_modes.py` - User mode management system
- `audio_modules/enhanced_tts_module.py` - Multi-provider TTS
- `audio_modules/enhanced_whisper_asr.py` - Dynamic ASR
- `auth_system.py` - Authentication and roles
- `mode_integrator.py` - System integration layer
- `mode_test.py` - Simple CLI for checking free vs. paid mode

### Architecture

- **Client-Server Architecture**: Scalable AI processing
- **Modular Design**: Easy to extend and customize
- **Async Processing**: High performance concurrent handling
- **Fallback Systems**: Graceful degradation on failures

## 📈 Deployment

### Local Development

- Suitable for development and testing
- 200 concurrent users maximum
- Home internet limitations

### Production Server

- 5-25x higher capacity (1000-5000 users)
- 2-3x faster response times
- Enterprise-grade reliability
- Professional monitoring

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for GPT and Whisper APIs
- Microsoft for Edge TTS
- All contributors and testers

---

**Status: ✅ Production Ready**
**Last Updated: June 10, 2025**
**Version: 2.0 (User Modes + Performance Tested)**

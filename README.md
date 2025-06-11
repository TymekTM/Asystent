# 🤖 GAJA Assistant

**Advanced AI-powered voice assistant with user mode system and real-time overlay interface.**

## 🚀 Quick Start

```bash
# Start client (voice assistant)
cd client && python client_main.py

# Start server (AI processing) 
cd server && python server_main.py

# Start web UI (configuration)
cd web_ui && python app.py
```

To check which TTS/ASR modules are active you can run:

```bash
python mode_test.py --mode poor_man  # or --mode paid
```

## 📁 Project Structure

```
f:\Asystent\
├── 🎙️ client/              # Voice assistant client
├── 🧠 server/              # AI processing server  
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
└── 📚 docs/                # Documentation
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

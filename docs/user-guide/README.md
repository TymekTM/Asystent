# Asystent User Guide

This guide helps you navigate and use all the features of the Asystent AI assistant system, updated for version 1.1.0.

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Web UI Interface](#web-ui-interface)
4. [Voice Interaction](#voice-interaction)
5. [System Configuration](#system-configuration)
6. [Long-term Memory Management](#long-term-memory-management)
7. [Available Modules and Tools](#available-modules-and-tools)
8. [Context-Aware Features](#context-aware-features)
9. [Performance Settings](#performance-settings)
10. [Troubleshooting](#troubleshooting)

## Introduction

Asystent is an advanced AI assistant system designed to help you with various tasks through natural language interaction. It supports multiple interaction methods including voice commands, text chat, and a comprehensive web interface for configuration and management. The system includes enhanced context awareness, multi-provider LLM support, and specialized tools for a more natural and helpful experience.

## Getting Started

To start using Asystent:

1. Make sure Python 3.10 or higher is installed on your system
2. Launch the application by running `python main.py` from the Asystent directory
3. The system will start both the assistant process and the web UI server
4. Access the web interface at `http://localhost:5000` (default address)
5. Log in with your credentials (default is dev/devpassword or user/password)
6. You can interact with the assistant in three ways:
   - Through voice using the wake word "asystencie" (configurable)
   - Via text input in the web UI chat interface
   - Through the integrated API endpoints

### First-time Setup

For optimal experience, configure these settings after installation:

1. Configure your preferred AI models in Config > AI Settings
2. Set up your audio devices in Config > Audio Settings
3. Customize the wake word if needed
4. Enable desired modules in Modules page

## Web UI Interface

The Asystent web interface includes several pages:

### Dashboard

The main control center displaying:<br>
- Assistant status (online/offline)<br>
- Quick actions (activate, restart, stop)<br>
- Recent activity and interaction history<br>
- Performance statistics and response times<br>
- System resource usage<br>

### Chat

Text interaction with the assistant:<br>
- Type messages in the input field<br>
- Use the microphone button for voice input<br>
- View full conversation history with timestamps<br>
- Multi-language support with automatic detection<br>
- Markdown rendering for formatted responses<br>
- Code highlighting for programming responses<br>

### Configuration

Comprehensive system settings management: <br>
- **AI Settings**: Choose between OpenAI, Ollama, DeepSeek, or Anthropic models<br>
- **Voice Recognition**: Configure STT engines (Whisper or Vosk) and parameters<br>
- **TTS Settings**: Voice settings with Edge TTS<br>
- **Wake Word**: Customize activation phrase and sensitivity<br>
- **Audio Devices**: Select microphone and output devices<br>
- **API Keys**: Securely store provider credentials<br>
- **Performance Mode**: Toggle low-power mode for resource-constrained systems<br>
- **Active Window Tracking**: Enable/disable context-aware assistance<br>

### Long-Term Memory

Memory management interface:<br>
- View stored memories with timestamps<br>
- Add new memories manually<br>
- Search through existing memories<br>

### Modules

Module management system:<br>
- Enable/disable individual modules<br>

Out of the box asystent comes with those modules:<br>
- Weather module with forecasting<br>
- DeepSeek module for complex reasoning tasks - to be reworked<br>
- Screen capture for visual analysis - broken<br>
- Core utilities for timers and more<br>
- Search module for web information access<br>
- Screen capture module for visual context<br>
- Web browser module for opening pages<br>

### Logs & Analytics

Comprehensive monitoring and analytics:<br>
- Real-time log streaming with filtering by level and module<br>
- Performance metrics tracking response times<br>
- System resource usage monitoring<br>
- Interaction history with timestamps<br>
- Export options for logs and analytics data<br>

## Voice Interaction

Asystent provides a natural voice interaction experience:

### Wake Word Detection

- Default wake word: "asystencie" (configurable)
- Upon detection, the system plays a beep indicating it's listening
- Speak your command or question after the beep
- The system processes your speech and responds verbally

### Speech-to-Text Options

Asystent supports two STT engines:

1. **Vosk** (default):
   - Offline operation
   - Lower resource usage
   - Works well for simple commands
   - Available in downloaded languages only

2. **Whisper(prefered)**:
   - Higher accuracy for complex speech
   - More resource intensive
   - Better for natural conversations
   - Excellent multilingual support

Configure your preference in the web UI settings.

### Voice Commands

Examples of supported voice commands:

- "What's the weather like today?"
- "Set a timer for 5 minutes"
- "Remember that I need to buy groceries"
- "Take a screenshot and tell me what you see"
- "Search for quantum computing information"

For more examples, see the [Voice Interaction Guide](voice-interaction.md).

### Context-Aware Voice Interaction

The system now maintains awareness of:<br>
- Active window title for contextual responses<br>
- Conversation continuity across interactions<br>
- Intent detection for handling specific command types<br>
- Question detection for automatic follow-up<br>

## System Configuration

### General Configuration

Basic settings are stored in `config.json` and can be modified via the web UI:

### Audio Configuration

Configure audio settings for optimal voice interaction:

1. Navigate to the Configuration page
2. Select "Audio Settings"
3. Choose your input device (microphone)
4. Adjust silence threshold if needed
5. Select your output device for TTS
6. Save changes

### AI Model Configuration

Asystent now supports an expanded range of AI models with enhanced configuration:

1. Navigate to the AI Settings tab
2. Select your preferred provider:
   - OpenAI (gpt-4.1-mini, gpt-4o)
   - Ollama (local models)
   - DeepSeek
   - Anthropic (Claude models)
3. Configure separate models for different functions:
   - Main conversation model
   - Query refinement model
   - Deep reasoning model
4. Set API keys securely
5. Configure context length and temperature settings

### Wake Word Settings

Customize the wake word detection:

1. Go to Wake Word settings
2. Enter your preferred activation phrase
3. Adjust activation threshold (lower = more sensitive)
4. Test the settings in a typical environment
5. Save configuration

### Active Window Tracking

New context-aware feature to help the assistant understand what you're working on:

1. Enable/disable in Configuration > Context Settings

### Auto-Listen Feature

Configure the assistant to automatically listen after it speaks:

1. Enable in Configuration > Voice Interaction
2. Set delay time between assistant response and listening activation
3. Configure question detection sensitivity

- **Query Refinement**: The system can automatically refine user queries to improve AI responses. This can be toggled on/off in settings.

- **Dynamic Configuration**: Most settings can be changed at runtime through the web interface without requiring a restart. Some hardware-related settings (like microphone device ID) may still require a system restart to take effect.

- **Language Detection**: Asystent automatically detects the language of your input and responds in the same language. This works across all supported language models.

## Long-term Memory Management

### Adding Memories

1. Navigate to Long-Term Memory page
2. Fill in the content field
3. (Optional) Specify a user attribute
4. Click "Add to memory"

### Searching Memories

1. On the Long-Term Memory page
2. Type search terms in the search box
3. Click "Search" to filter results

### Deleting Memories

1. Find the memory you wish to remove
2. Click the "Delete" button next to it
3. The memory will be removed from the database

## Multilingual Support

Asystent now features enhanced multilingual capabilities:

### Automatic Language Detection

The system automatically detects the language you're using and responds in the same language. This applies to:<br>
- Voice inputs<br>
- Text chat messages<br>
- Commands and queries<br>

### Supported Languages

Primary languages with full support:<br>
- English<br>
- Polish<br>

## Available Modules and Tools

Asystent has a modular plugin system that extends functionality.

### Currently Implemented Modules

- **Search Module**: Performs web searches and summarizes results
- **Memory Module**: Manages long-term memory storage and retrieval
- **Screen Capture**: Captures and analyzes screen contents
- **Deepseek Module**: Performs advanced reasoning tasks
- **Core Module**: Provides timers, reminders, and task management
- **Weather Module**: Fetches and reports weather information
- **Active Window Module**: Tracks current application context

For detailed information about each module, see the [Plugins Documentation](plugins.md).

## Context-Aware Features

### Active Window Context

When enabled, Asystent can track the currently active window:

1. Enable this feature in Configuration > Advanced Settings
2. The assistant will now be aware of which application you're using
3. Responses can be tailored to your current context
4. This improves assistance for application-specific questions

### Multilingual Awareness

Asystent detects the language you're speaking:

1. Automatic language detection for input
2. Responses in the same language
3. Currently supports Polish and English fully
4. Limited support for other languages

## Performance Settings

### Low Power Mode

For systems with limited resources:

1. Enable in Configuration > Performance
2. Reduces model complexity
3. Uses lighter STT processing
4. May reduce accuracy but improves responsiveness

### Development Mode

For developers and testing:

1. Enable in Configuration (or use DEV_MODE environment variable)
2. Keeps models loaded for faster turnaround
3. Provides additional debugging information
4. Shows technical details in responses

## Troubleshooting

### Voice Recognition Issues

If the assistant doesn't respond to your voice:

1. Check that your microphone is properly connected
2. Verify the correct microphone is selected in settings
3. Adjust the silence threshold (try lower values)
4. Speak more clearly and loudly
5. Try using the manual activation button

### AI Response Problems

If responses are incorrect or incomplete:

1. Check your internet connection (for cloud models)
2. Verify API keys are correctly entered
3. Try a different AI model or provider
4. Restart the assistant
5. Check system logs for errors

### Web UI Access Issues

If you can't access the web interface:

1. Verify the application is running
2. Check if the server address has been changed in config
3. Make sure no other service is using the same port
4. Check firewall settings if accessing from another device
5. Look for server errors in the console output

### Module Functionality Issues

If specific features aren't working:

1. Check module is enabled in the Modules page
2. Verify required API keys are provided (for external services)
3. Check logs for specific module errors
4. Restart the assistant after changing module settings

For additional help or to report issues, please visit the project repository.

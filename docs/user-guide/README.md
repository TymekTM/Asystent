# Asystent User Guide

This guide helps you navigate and use all the features of the Asystent AI assistant system.

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Web UI Interface](#web-ui-interface)
4. [Voice Interaction](#voice-interaction)
5. [System Configuration](#system-configuration)
6. [Long-term Memory Management](#long-term-memory-management)
7. [Plugins and Extensions](#plugins-and-extensions)
8. [Troubleshooting](#troubleshooting)

## Introduction

Asystent is an AI assistant system designed to help you with various tasks through natural language interaction. It supports both voice and text-based interfaces and includes a web control panel for configuration and management.

## Getting Started

To start using Asystent:

1. Ensure the system is running (check the dashboard for status)
2. Access the web interface at `http://localhost:5000` (default address)
3. Log in with your credentials
4. Navigate to the chat interface to start interacting with the assistant

## Web UI Interface

The Asystent web interface includes several pages:

### Dashboard

The main control center displaying:
- Assistant status (online/offline)
- Quick actions (activate, restart, stop)
- Recent activity
- Usage statistics

![Dashboard](../screenshots/dashboard.png) <!-- Create and add screenshots -->

### Chat

Direct text interaction with the assistant:
- Type messages in the input field
- Use the microphone button for voice input
- View conversation history
- Clear chat history as needed

### Configuration

Adjust system settings including:
- Voice recognition settings
- Language model selection
- Wake word customization
- Microphone selection
- API keys configuration

### Long-Term Memory

Manage what the assistant remembers:
- View all stored memories
- Add new memories manually
- Search through existing memories
- Delete specific memories

### Plugins

Manage the plugin system:
- Enable/disable plugins
- View plugin status
- Reload plugins

### Logs

Monitor system operations:
- Filter logs by level (INFO, WARNING, ERROR)
- Download logs for analysis
- Navigate through log history

### History

Review past conversations:
- Chronological view of interactions
- Archive conversations

## Voice Interaction

Asystent responds to voice commands when activated by:
1. Speaking the wake word (default is "asystent")
2. Clicking the "Activate Manually" button on the dashboard or chat interface

After activation, speak your command or question clearly. The system will process your speech and respond audibly.

## System Configuration

### Wake Word Customization

1. Navigate to the Configuration page
2. Find the "Wake Word" input field
3. Enter your preferred wake word
4. Save configuration

### Voice Selection

1. Access the Configuration page
2. Navigate to TTS (Text-to-Speech) settings
3. Choose from available voices
4. Adjust speed and other parameters as needed
5. Save configuration

### Model Selection

Asystent supports multiple AI models:
1. Navigate to Configuration
2. Under "LLM & Provider Settings"
3. Select your preferred provider (OpenAI, Ollama, etc.)
4. Specify model names for different functions
5. Save configuration

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
3. Confirm deletion when prompted

## Plugins and Extensions

Asystent has a modular plugin system that allows extending functionality.

### Enabled Plugins

- **Search Module**: Web search capabilities
- **API Module**: Third-party service integration
- **Screen Capture**: Analysis of screen contents
- **Memory Module**: Long-term memory management
- **Deepseek Module**: Advanced reasoning (when enabled)

To manage plugins:
1. Navigate to the Plugins page
2. Toggle plugins on/off using the provided buttons
3. Use "Reload" to refresh a plugin after changes

## Troubleshooting

### Assistant Not Responding

1. Check status on dashboard
2. Verify microphone is working
3. Try restarting the assistant
4. Check logs for errors

### Voice Recognition Issues

1. Ensure proper microphone is selected in Configuration
2. Speak clearly and at a moderate pace
3. Check if the wake word is correctly set
4. Verify that voice models are properly installed

### Web Interface Problems

1. Clear browser cache
2. Try a different browser
3. Check if server is running
4. Restart the web panel if needed

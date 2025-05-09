# Web UI Guide

This guide provides detailed information about using the Asystent Web User Interface.

## General Navigation

The web interface is structured with a navigation bar at the top containing links to all major sections. The currently active section is highlighted.

### Theme Switching

You can toggle between light and dark themes using the theme button in the top-right corner of the navigation bar.

## Dashboard

The Dashboard provides an overview of system status and quick access to common actions.

### Key Elements

- **Assistant Status**: Shows if the assistant is online, offline, or restarting
- **Wake Word**: Displays the current wake word configuration
- **STT Engine**: Shows which speech recognition engine is being used
- **Quick Actions**: 
  - **Activate Manually**: Triggers the assistant to listen without wake word
  - **Restart Assistant**: Restarts the assistant process
  - **Restart Web Panel**: Restarts the web interface
  - **Restart All**: Restarts both components
  - **Stop Assistant**: Shuts down the assistant process
- **Performance Stats**: Displays CPU, memory usage, and response times
- **Recent Activity**: Shows recent interaction logs

## Chat Interface

The chat page allows direct text interaction with the assistant.

### Features

- **Message Input**: Type your message in the input field at the bottom
- **Send Button**: Click to send your message
- **Microphone Button**: Click to activate voice input
- **Conversation Display**: Shows the conversation history with user and assistant messages
- **Clear Chat**: Button to clear the current conversation history

## Configuration Page

The configuration page allows you to customize various system settings.

### Configuration Sections

- **Voice Recognition Settings**:
  - Wake word customization
  - Microphone device selection
  - STT engine selection (Vosk/Whisper)
  - Silence threshold adjustment
  
- **AI Settings**:
  - Provider selection (OpenAI, Ollama, DeepSeek, Anthropic)
  - Model selection for different functions
  - API key management
  - Context length and temperature settings
  
- **TTS Settings**:
  - Voice selection
  - Speech rate adjustment
  - Output device selection
  
- **Performance Settings**:
  - Low power mode toggle
  - Development mode options
  - Resource allocation settings

- **Context Settings**:
  - Active window tracking toggle
  - Polling interval adjustment
  - Privacy settings

### Saving Configuration

After making changes, click the "Save Configuration" button at the bottom of the page. Some settings may require a restart to take effect.

## Long-Term Memory Page

The Long-Term Memory page manages the assistant's persistent knowledge.

### Managing Memories

- **Adding Memories**: Enter content in the form at the top of the page
- **Searching Memories**: Use the search box to filter memories by content
- **Viewing Memories**: All memories are listed with timestamp and content
- **Deleting Memories**: Click the delete button next to any memory entry

## Modules Page

The Modules page allows management of system modules.

### Module Management

- **Status Toggles**: Enable or disable individual modules 
- **Module Settings**: Configure specific module parameters
- **Module Information**: View descriptions of each module's functionality
- **Reload Button**: Refresh modules after configuration changes

## Logs Page

The Logs page provides access to system logs for troubleshooting.

### Features

- **Log Level Filtering**: Filter by INFO, WARNING, or ERROR
- **Component Filtering**: Filter logs by specific system components
- **Real-time Updates**: View logs as they occur
- **Download**: Save logs for offline analysis

## Performance Page

The Performance page displays system resource usage and response metrics.

### Features

- **CPU/Memory Usage**: Graphs showing resource consumption over time
- **Response Time**: Charts of AI and system response times
- **Operation Counts**: Statistics on different types of operations
- **Component Performance**: Breakdown of performance by system component

## History Page

The History page shows a chronological record of conversations.

### Features

- **Conversation Timeline**: View all interactions organized chronologically
- **Archive**: Store the current history and start fresh

## Dev Tools (Admin Only)

The Dev section provides advanced tools for system administrators.

### Features

- **Unit Tests**: Run and view results of system tests
- **Benchmarks**: Measure system performance
- **User Management**: Add, edit, and delete user accounts

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
- **Quick Actions**: 
  - Activate Manually: Triggers the assistant to listen without wake word
  - Restart Assistant: Restarts the assistant process
  - Restart Web Panel: Restarts the web interface
  - Restart All: Restarts both components
  - Stop Assistant: Shuts down the assistant process
- **Recent Activity**: Shows the most recent interactions with the assistant
- **Usage Statistics**: Displays metrics like message count, unique users, and response time

## Chat Interface

The Chat interface allows direct text conversation with the assistant.

### Features

- **Text Input**: Type messages in the input field
- **Voice Input**: Use the microphone button to speak your message
- **Chat History**: Displays the ongoing conversation
- **Clear Chat**: Removes the current conversation history

### Chat Commands

You can use special commands in chat by prefixing them with an exclamation mark:

- `!search [query]`: Performs a web search
- `!deep [query]`: Activates deep reasoning mode
- `!memory add [content]`: Adds information to long-term memory
- `!memory get [query]`: Retrieves information from memory

## Configuration Page

The Configuration page allows customization of all system parameters.

### Settings Categories

- **Vosk Settings**: Configure wake word detection and speech-to-text
- **LLM & Provider Settings**: Set up language models and AI providers
- **TTS Settings**: Configure text-to-speech parameters
- **API Keys**: Store credentials for external services
- **Other Settings**: Miscellaneous system parameters

### Saving Configuration

After making changes, click the "Save Configuration" button at the bottom of the page. The system may restart to apply changes.

## Long-Term Memory Page

The Long-Term Memory page manages the assistant's persistent knowledge.

### Managing Memories

- **Adding Memories**: Enter content in the form at the top of the page
- **Searching Memories**: Use the search box to filter memories by content
- **Viewing Memories**: All memories are listed with ID, user attribution, and timestamp
- **Deleting Memories**: Click the delete button next to any memory entry

## Logs Page

The Logs page provides access to system logs for troubleshooting.

### Features

- **Log Level Filtering**: Filter by INFO, WARNING, or ERROR
- **Pagination**: Navigate through log pages
- **Download**: Save logs for offline analysis

## Plugins Page

The Plugins page allows management of system extensions.

### Plugin Management

- **Status View**: See which plugins are enabled or disabled
- **Toggle**: Enable or disable plugins without restart
- **Reload**: Refresh a plugin after making changes to its configuration

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

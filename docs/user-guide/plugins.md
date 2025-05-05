# Plugin System Documentation

## Currently Implemented Plugins

### Search Module
- **Command**: `search` (aliases: `search`, `wyszukaj`, `web`)
- **Description**: Searches for information on the internet and summarizes the results
- **Features**:
  - Performs web searches using DuckDuckGo
  - Fetches and extracts text content from search results
  - Summarizes content using the language model
  - Caches results for better performance
  - Supports language detection for appropriate responses

### Memory Module
- **Command**: `memory` (aliases: `memory`, `pamięć`, `pamiec`)
- **Description**: Manages the assistant's long-term memory
- **Sub-commands**:
  - `add`: Saves new information to memory
  - `get`: Retrieves information from memory
  - `delete`: Removes information from memory
- **Features**:
  - Persistent storage in database
  - Search functionality to find specific memories
  - User attribution for memory entries
  - Integration with web UI for management

### See Screen Module
- **Command**: `screenshot` (aliases: `screenshot`, `screen`)
- **Description**: Captures the screen and analyzes its contents
- **Features**:
  - Multiple capture methods (DXcam, pyautogui, ImageGrab)
  - Vision analysis of screen contents
  - Can answer specific questions about screen content
  - Notifications when capturing the screen

### Deepseek Module
- **Command**: `deep` (aliases: `deep`, `wgłęb`)
- **Description**: Performs advanced reasoning on complex topics
- **Features**:
  - Uses specialized language models for deep thinking
  - Processes complex reasoning tasks
  - Returns detailed analytical results
  - Can be enabled/disabled via the plugins page

### API Module
- **Command**: `api` (aliases: `api`, `pogoda`, `weather`)
- **Description**: Handles API queries based on JSON configuration
- **Features**:
  - Configuration-based API integrations
  - Currently implemented for weather queries
  - Extensible for additional API endpoints
  - Error handling for API failures

## Plugin Management

All plugins can be managed via the Plugins page in the web UI:
1. Enable/disable plugins
2. View current status
3. Reload plugins after configuration changes

For information on developing custom plugins, see the [Plugin Development Guide](../developer/plugin-development.md).

# Module System Documentation

## Currently Implemented Modules

### Daily Briefing Module
- **Command**: `briefing` (aliases: `brief`, `podsumowanie`, `dzień`)
- **Description**: Generates personalized daily briefing with weather, memories, and other relevant information
- **Features**:
  - AI-generated personalized briefings
  - Weather data integration
  - Memory context integration
  - Language detection and multi-language support
  - Style variations (normal, funny, serious)
  - Scheduled briefings at specified times
  - Holiday and special date notifications
  - Calendar integration for upcoming events
- **Example**: "Give me my daily briefing" or "Co dziś planujemy?"

### Search Module
- **Command**: `search` (aliases: `search`, `wyszukaj`, `web`)
- **Description**: Searches for information on the internet and summarizes the results
- **Features**:
  - Performs web searches using DuckDuckGo
  - Fetches and extracts text content from search results
  - Summarizes content using the language model
  - Caches results for better performance
  - Supports language detection for appropriate responses
- **Example**: "Search for information about quantum computing"

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
- **Example**: "Remember that my meeting is on Thursday at 3pm"

### See Screen Module
- **Command**: `screenshot` (aliases: `screenshot`, `screen`)
- **Description**: Captures the screen and analyzes its contents
- **Features**:
  - Multiple capture methods (DXcam, pyautogui, ImageGrab)
  - Vision analysis of screen contents
  - Can answer specific questions about screen content
  - Notifications when capturing the screen
- **Example**: "Take a screenshot and tell me what you see"

### Deepseek Module
- **Command**: `deep` (aliases: `deep`, `wgłęb`)
- **Description**: Performs advanced reasoning on complex topics
- **Features**:
  - Uses specialized language models for deep thinking
  - Processes complex reasoning tasks
  - Returns detailed analytical results
  - Can be enabled/disabled via the modules page
- **Example**: "Use deep reasoning to analyze this problem"

### Weather Module
- **Command**: `weather` (aliases: `weather`, `pogoda`)
- **Description**: Fetches weather information from APIs
- **Features**:
  - Current weather conditions
  - Temperature information
  - Weather forecasting
  - Multiple location support
- **Example**: "What's the weather like in Warsaw today?"

### Core Module
- **Command**: `core` 
- **Description**: Provides essential utility functions
- **Sub-commands**:
  - `set_timer`: Creates a countdown timer
  - `view_timers`: Shows active timers
  - `add_event`: Adds event to calendar
  - `view_calendar`: Shows calendar events
  - `set_reminder`: Creates a reminder
  - `view_reminders`: Shows active reminders
  - `add_task`: Creates a new task
  - `view_tasks`: Lists all tasks
  - `complete_task`: Marks task as complete
  - `remove_task`: Deletes a task
  - `add_item`: Adds item to shopping list
  - `view_list`: Shows shopping list
  - `remove_item`: Removes item from shopping list
- **Features**:
  - Timer functionality
  - Task management
  - Reminder system
  - Shopping list
- **Example**: "Set a timer for 5 minutes"

### Active Window Module
- **Description**: Tracks the currently active window
- **Features**:
  - Provides context about current application
  - Helps assistant understand user's current activity
  - Can be enabled/disabled for privacy

### Function Calling Integration
- **Description**: Enables structured function calling with LLM models
- **Features**:
  - Converts module system to OpenAI function calling format
  - Allows for more precise command interpretation
  - Enhances module execution accuracy
  - Streamlined parameter handling for all modules
  - Support for nested function calling
  - Configurable polling interval
- **Note**: This module runs in the background and doesn't have direct commands

### Open Web Module
- **Command**: `open_web` (aliases: `open`, `otwórz`)
- **Description**: Opens websites in the browser
- **Features**:
  - Can open specific URLs
  - Can search and open common websites
- **Example**: "Open GitHub website"

### API Module
- **Command**: `api` (aliases: `api`, `endpoint`)
- **Description**: Makes requests to external APIs
- **Features**:
  - Supports various HTTP methods (GET, POST, PUT, DELETE)
  - Can send and receive JSON data
  - Handles authentication
  - Configurable via `api_integrations_config.json`
- **Example**: "Make an API call to get the latest data"

### Music Module
- **Command**: `music` (aliases: `play`, `graj`, `muzyka`)
- **Description**: Controls music playback
- **Features**:
  - Play/pause/stop music
  - Skip tracks
  - Volume control
  - Playlist management
  - Genre-based recommendations
- **Example**: "Play some relaxing music"

### Open Web Module
- **Command**: `open` (aliases: `otwórz`, `web`, `webpage`)
- **Description**: Opens websites and performs web navigation
- **Features**:
  - Opens URLs in default browser
  - Intelligent URL construction from search terms
  - Support for common websites and services
  - Handles URL validation and formatting
- **Example**: "Open Google" or "Otwórz YouTube"

## Module Management

### Enabling/Disabling Modules
1. Navigate to the Modules page in the web UI
2. Toggle the switch next to each module to enable or disable
3. Changes take effect immediately without restart

### Module Configuration
Some modules have configuration options that can be modified:
1. Click the "Settings" button next to the module
2. Adjust parameters as needed
3. Save changes

### Module Troubleshooting
If a module isn't functioning correctly:
1. Check if it's properly enabled in the Modules page
2. Verify any required API keys are set in Configuration
3. Check the logs for specific error messages
4. Try reloading modules using the "Reload Modules" button
  - Extensible for additional API endpoints
  - Error handling for API failures

## Plugin Management

All plugins can be managed via the Plugins page in the web UI:
1. Enable/disable plugins
2. View current status
3. Reload plugins after configuration changes

For information on developing custom plugins, see the [Plugin Development Guide](../developer/plugin-development.md).

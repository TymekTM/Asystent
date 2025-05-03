# REST API Endpoints Reference

This document provides detailed specifications for all REST API endpoints in the Asystent system.

## Authentication Endpoints

### POST /login

Authenticates a user and creates a session.

**Request Body:**
- Form data with `username` and `password`

**Responses:**
- 200 OK: Authentication successful, user is logged in
- 401 Unauthorized: Invalid credentials

### GET /logout

Ends the current user session.

**Responses:**
- 302 Found: Redirects to login page

## Status Endpoints

### GET /api/status

Retrieves the current system status.

**Response Body:**
```json
{
  "status": "Online",
  "uptime": 3600,
  "wake_word": "asystent",
  "last_activity": "2025-05-03T12:34:56"
}
```

**Status Values:**
- `Online`: Assistant is running and responsive
- `Offline`: Assistant process is stopped
- `Restarting`: Assistant is currently restarting

## Assistant Control

### POST /api/activate

Activates the assistant to listen for voice input.

**Response Body:**
```json
{
  "success": true,
  "message": "Activation request sent"
}
```

**Error Responses:**
- 500 Internal Server Error: If the assistant process is not running

### POST /api/stop/assistant

Stops the assistant process.

**Response Body:**
```json
{
  "success": true,
  "message": "Assistant stopped"
}
```

### POST /api/restart/assistant

Restarts the assistant process.

**Response Body:**
```json
{
  "success": true,
  "message": "Assistant restart initiated"
}
```

### POST /api/restart/web

Restarts the web interface.

**Response Body:**
```json
{
  "success": true,
  "message": "Web interface restart initiated"
}
```

### POST /api/restart/all

Restarts both the assistant and web interface.

**Response Body:**
```json
{
  "success": true,
  "message": "Full system restart initiated"
}
```

## Configuration

### GET /api/config

Retrieves the current system configuration.

**Response Body:**
```json
{
  "WAKE_WORD": "asystent",
  "MIC_DEVICE_ID": "",
  "PROVIDER": "ollama",
  "MAIN_MODEL": "llama3",
  "DEEP_MODEL": "mistral",
  "TTS_PROVIDER": "system",
  "STT_MODEL": "whisper-small",
  "MAX_HISTORY_LENGTH": 10,
  "PLUGIN_MONITOR_INTERVAL": 5,
  "API_KEYS": {
    "OPENAI_API_KEY": "••••••••",
    "DEEPSEEK_API_KEY": "••••••••"
  }
}
```

**Notes:**
- Sensitive values like API keys are masked in the response
- Not all configuration parameters may be shown

### POST /api/config

Updates the system configuration.

**Request Body:**
```json
{
  "WAKE_WORD": "jarvis",
  "MAIN_MODEL": "gpt4",
  "API_KEYS": {
    "OPENAI_API_KEY": "sk-..."
  }
}
```

**Response Body:**
```json
{
  "success": true,
  "message": "Configuration updated"
}
```

**Error Responses:**
- 400 Bad Request: Invalid configuration parameters
- 500 Internal Server Error: Error saving configuration

## Chat Interface

### GET /api/chat/history

Retrieves the conversation history.

**Query Parameters:**
- `limit` (optional): Maximum number of messages to return (default: 50)

**Response Body:**
```json
{
  "history": [
    {
      "role": "user",
      "content": "What time is it?",
      "timestamp": "2025-05-03T10:15:30"
    },
    {
      "role": "assistant",
      "content": "It's currently 10:15 AM on May 3rd, 2025.",
      "timestamp": "2025-05-03T10:15:32"
    }
  ]
}
```

### POST /api/chat/send

Sends a message to the assistant.

**Request Body:**
```json
{
  "message": "What's the weather like today?"
}
```

**Response Body:**
```json
{
  "success": true,
  "response": "I don't have real-time weather data, but I can search for that information if you'd like."
}
```

**Error Responses:**
- 400 Bad Request: Missing or invalid message
- 500 Internal Server Error: Error processing message

### POST /api/chat/clear

Clears the conversation history.

**Response Body:**
```json
{
  "success": true
}
```

## Long-Term Memory

### GET /api/ltm/get

Retrieves memories from long-term storage.

**Query Parameters:**
- `query` (optional): Search term to filter memories
- `user` (optional): Filter by user attribution
- `limit` (optional): Maximum number of memories to return (default: 100)

**Response Body:**
```json
[
  {
    "id": 1,
    "content": "The user prefers coffee over tea",
    "timestamp": "2025-04-10T08:15:22",
    "user": "assistant"
  },
  {
    "id": 2,
    "content": "Meeting scheduled for May 5th at 2pm",
    "timestamp": "2025-05-02T14:30:10",
    "user": "assistant"
  }
]
```

### POST /api/ltm/add

Adds a new memory to long-term storage.

**Request Body:**
```json
{
  "content": "User's birthday is on June 15",
  "user": "assistant"
}
```

**Response Body:**
```json
{
  "success": true,
  "id": 3
}
```

**Error Responses:**
- 400 Bad Request: Missing content or invalid format
- 500 Internal Server Error: Database error

### DELETE /api/ltm/delete/{id}

Deletes a specific memory by ID.

**URL Parameters:**
- `id`: The numeric ID of the memory to delete

**Response Body:**
```json
{
  "success": true
}
```

**Error Responses:**
- 404 Not Found: Memory with the specified ID doesn't exist
- 500 Internal Server Error: Database error

## Plugin Management

### GET /api/plugins

Lists all available plugins and their status.

**Response Body:**
```json
{
  "search_module": {
    "enabled": true,
    "description": "Wyszukuje informacje w internecie i podsumowuje wyniki."
  },
  "deepseek_module": {
    "enabled": false,
    "description": "Wykonuje głębokie rozumowanie."
  },
  "see_screen_module": {
    "enabled": true,
    "description": "Wykonuje zrzut ekranu i analizuje zawartość."
  },
  "api_module": {
    "enabled": true,
    "description": "Integruje się z zewnętrznymi API."
  }
}
```

### POST /api/plugins/{plugin_name}/toggle

Enables or disables a specific plugin.

**URL Parameters:**
- `plugin_name`: Name of the plugin to toggle

**Request Body:**
```json
{
  "enabled": true
}
```

**Response Body:**
```json
{
  "success": true,
  "status": "enabled"
}
```

**Error Responses:**
- 404 Not Found: Plugin doesn't exist
- 500 Internal Server Error: Error updating plugin state

### POST /api/plugins/{plugin_name}/reload

Reloads a specific plugin.

**URL Parameters:**
- `plugin_name`: Name of the plugin to reload

**Response Body:**
```json
{
  "success": true,
  "message": "Plugin reloaded"
}
```

**Error Responses:**
- 404 Not Found: Plugin doesn't exist
- 500 Internal Server Error: Error reloading plugin

## System Logs

### GET /api/logs

Retrieves system logs with filtering and pagination.

**Query Parameters:**
- `level` (optional): Log level to filter by (ALL, INFO, WARNING, ERROR)
- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Number of log entries per page (default: 100)

**Response Body:**
```json
{
  "logs": [
    "2025-05-03 10:15:30 - MainProcess - assistant - INFO - Bot is starting...",
    "2025-05-03 10:15:32 - MainProcess - assistant - INFO - Wake word detector initialized"
  ],
  "page": 1,
  "total_pages": 5
}
```

### GET /api/logs/download

Downloads the complete log file as plain text.

**Response:**
- Content-Type: text/plain
- Content-Disposition: attachment; filename=assistant_logs.txt

## Analytics

### GET /api/analytics

Retrieves usage statistics.

**Response Body:**
```json
{
  "msg_count": 152,
  "unique_users": ["user1", "user2"],
  "avg_response_time": 1.23,
  "last_query_time": 1714743330,
  "plugin_usage": {
    "search_module": 45,
    "deepseek_module": 12,
    "memory_module": 34
  }
}
```

## User Management (Dev Only)

### GET /dev/users

Lists all users (requires dev role).

**Response Body:**
```json
[
  {
    "username": "user",
    "role": "user",
    "display_name": "Regular User",
    "ai_persona": null,
    "personalization": null
  },
  {
    "username": "dev",
    "role": "dev",
    "display_name": "Developer",
    "ai_persona": null,
    "personalization": null
  }
]
```

### POST /dev/users/add

Adds a new user (requires dev role).

**Request Body:**
```json
{
  "username": "new_user",
  "password": "secure_password",
  "role": "user",
  "display_name": "New User",
  "ai_persona": "friendly",
  "personalization": "likes coffee"
}
```

**Response Body:**
```json
{
  "success": true
}
```

### POST /dev/users/delete

Deletes a user (requires dev role).

**Request Body:**
```json
{
  "username": "user_to_delete"
}
```

**Response Body:**
```json
{
  "success": true
}
```

### POST /dev/users/update

Updates user details (requires dev role).

**Request Body:**
```json
{
  "username": "existing_user",
  "display_name": "Updated Name",
  "ai_persona": "formal"
}
```

**Response Body:**
```json
{
  "success": true
}
```

## Health Check

### GET /health

Simple health check endpoint for monitoring.

**Response Body:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

# API Documentation

This document outlines the API endpoints available in the Gaja system, allowing for integration with external applications.

## Base URL

All API endpoints are relative to the base URL where your Gaja instance is running:

```
http://[host]:[port]/api
```

By default, this would be: `http://localhost:5000/api`

## Authentication

API access requires authentication. Use standard HTTP Basic Authentication with your username and password, or include a valid session cookie from a web UI login.

## General Response Format

API responses follow a consistent JSON format:

Success responses:
```json
{
  "success": true,
  "data": { ... }  // Response data varies by endpoint
}
```

Error responses:
```json
{
  "success": false,
  "error": "Error message"
}
```

## Available Endpoints

### System Status

#### GET /api/status

Returns the current status of the assistant.

**Response:**
```json
{  "status": "Online",  // Can be "Online", "Offline", or "Restarting"
  "uptime": 3600,      // Seconds since last startup
  "wake_word": "gaja"
}
```

### Assistant Interaction

#### POST /api/activate

Activates the assistant to listen for voice input without using the wake word.

**Response:**
```json
{
  "success": true,
  "message": "Activation request sent"
}
```

#### POST /api/chat/send

Sends a text message to the assistant.

**Request Body:**
```json
{
  "message": "What's the weather like today?"
}
```

**Response:**
```json
{
  "success": true,
  "response": "I don't have real-time weather data, but I can search for that information if you'd like."
}
```

#### GET /api/chat/history

Retrieves recent chat history.

**Query Parameters:**
- `limit` (optional): Maximum number of messages to return (default: 50)

**Response:**
```json
{
  "history": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2025-05-03T10:15:30"
    },
    {
      "role": "assistant",
      "content": "Hello! How can I help you today?",
      "timestamp": "2025-05-03T10:15:32"
    }
  ]
}
```

#### POST /api/chat/clear

Clears the chat history.

**Response:**
```json
{
  "success": true
}
```

### Configuration Management

#### GET /api/config

Retrieves the current system configuration.

**Response:**
```json
{
  "WAKE_WORD": "gaja",
  "MIC_DEVICE_ID": "",
  "PROVIDER": "ollama",
  "MAIN_MODEL": "llama3",
  "TTS_PROVIDER": "system",
  "TTS_VOICE": "default",
  // Additional configuration parameters...
}
```

#### POST /api/config

Updates system configuration.

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

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated, restarting assistant"
}
```

### Memory Management

#### GET /api/ltm/get

Retrieves long-term memories.

**Query Parameters:**
- `query` (optional): Search term to filter memories
- `user` (optional): Filter by user attribution
- `limit` (optional): Maximum number of memories to return

**Response:**
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

#### POST /api/ltm/add

Adds a new memory.

**Request Body:**
```json
{
  "content": "The user's favorite color is blue",
  "user": "assistant"  // Optional, defaults to "assistant"
}
```

**Response:**
```json
{
  "success": true,
  "id": 3
}
```

#### DELETE /api/ltm/delete/{id}

Deletes a memory by ID.

**Response:**
```json
{
  "success": true
}
```

### Plugin Management

#### GET /api/plugins

Lists all available plugins and their status.

**Response:**
```json
{
  "search_module": {
    "enabled": true,
    "description": "Wyszukuje informacje w internecie i podsumowuje wyniki."
  },
}
```

#### POST /api/plugins/{plugin_name}/toggle

Enables or disables a plugin.

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "status": "enabled"
}
```

#### POST /api/plugins/{plugin_name}/reload

Reloads a plugin (useful after modifying plugin code).

**Response:**
```json
{
  "success": true,
  "message": "Plugin reloaded"
}
```

### System Control

#### POST /api/restart/assistant

Restarts the assistant process.

**Response:**
```json
{
  "success": true,
  "message": "Assistant restart initiated"
}
```

#### POST /api/restart/web

Restarts the web interface.

**Response:**
```json
{
  "success": true,
  "message": "Web interface restart initiated"
}
```

#### POST /api/restart/all

Restarts both the assistant and web interface.

**Response:**
```json
{
  "success": true,
  "message": "Full system restart initiated"
}
```

#### POST /api/stop/assistant

Stops the assistant process.

**Response:**
```json
{
  "success": true,
  "message": "Assistant stopped"
}
```

### Logs and Analytics

#### GET /api/logs

Retrieves system logs.

**Query Parameters:**
- `level` (optional): Log level to filter by (ALL, INFO, WARNING, ERROR)
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of log entries per page

**Response:**
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

#### GET /api/logs/download

Downloads the complete log file.

**Response:** Binary file download (text/plain)

#### GET /api/analytics

Retrieves usage statistics.

**Response:**
```json
{
  "msg_count": 152,
  "unique_users": ["user1", "user2"],
  "avg_response_time": 1.23,
  "last_query_time": 1714743330
}
```

### Module-Specific Endpoints

#### GET /api/briefing

Generates and retrieves a daily briefing.

**Query Parameters:**
- `style` (optional): Briefing style, can be "normal", "funny", or "serious" (default: "normal")
- `lang` (optional): Language code for the briefing (default: auto-detect)

**Response:**
```json
{
  "success": true,
  "briefing": "Good morning! Today is Monday, June 2, 2025. The weather in your area is sunny with a temperature of 22°C. You have 2 events scheduled today. Remember that yesterday you asked me to remind you about submitting your report."
}
```

## Error Codes

- 400: Bad Request - Invalid input
- 401: Unauthorized - Authentication required
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource doesn't exist
- 500: Internal Server Error - Server-side failure

## Integrating with the API

### Example: Sending a Message

```python
import requests

base_url = "http://localhost:5000"

# Authenticate
session = requests.Session()
response = session.post(
    f"{base_url}/login",
    data={"username": "user", "password": "password"}
)

# Send message to assistant
response = session.post(
    f"{base_url}/api/chat/send",
    json={"message": "Hello, what can you do?"}
)
print(response.json())
```

### Example: Controlling the Assistant

```javascript
// JavaScript example
async function restartAssistant() {
    const response = await fetch('/api/restart/assistant', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    
    const result = await response.json();
    if (result.success) {
        console.log("Assistant is restarting");
    } else {
        console.error("Failed to restart assistant:", result.error);
    }
}
```

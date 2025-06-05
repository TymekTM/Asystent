# API Integration Guide

This guide explains how to integrate external applications with the Asystent system using the REST API.

## Overview

Asystent provides a comprehensive RESTful API that allows you to:
- Control the assistant programmatically
- Send and receive messages
- Access system features
- Retrieve system information and status

## Authentication

All API requests require authentication. There are two ways to authenticate:

### 1. Session Authentication

If you're integrating within a web browser or application that supports cookies:

1. First authenticate via the `/login` endpoint
2. The server will set a session cookie
3. Include this cookie in all subsequent requests

```python
import requests

base_url = "http://localhost:5000"
session = requests.Session()

# Log in and store session cookie
response = session.post(
    f"{base_url}/login",
    data={"username": "user", "password": "password"}
)

# Now session will include the authentication cookie automatically
result = session.get(f"{base_url}/api/status")
print(result.json())
```

### 2. HTTP Basic Authentication

For direct API access from applications:

```python
import requests
from requests.auth import HTTPBasicAuth

base_url = "http://localhost:5000"
auth = HTTPBasicAuth('user', 'password')

response = requests.get(
    f"{base_url}/api/status", 
    auth=auth
)
print(response.json())
```

## Common Use Cases

### Sending Messages

To send a message to the assistant and get a response:

```python
response = session.post(
    f"{base_url}/api/chat/send",
    json={"message": "What's the weather like today?"}
)
result = response.json()
print(f"Assistant says: {result['response']}")
```

### Activating Voice Recognition

To trigger the assistant to listen without using the wake word:

```python
response = session.post(f"{base_url}/api/activate")
print("Assistant is now listening...")
```

### Getting a Daily Briefing

To retrieve a personalized daily briefing:

```python
response = session.get(
    f"{base_url}/api/briefing",
    params={"style": "normal", "lang": "en"}
)
print(f"Daily briefing: {response.json()['briefing']}")
```

### Controlling the Assistant

To restart the assistant:

```python
response = session.post(f"{base_url}/api/restart/assistant")
print(response.json()['message'])
```

## Error Handling

The API uses standard HTTP status codes:
- 200: Success
- 400: Bad request, check your parameters
- 401: Authentication required
- 403: Insufficient permissions
- 404: Endpoint not found
- 500: Server-side error

All error responses include a JSON body with details:

```json
{
  "success": false,
  "error": "Detailed error description"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:
- 60 requests per minute for authenticated users
- 5 requests per minute for unauthenticated requests

When rate limited, you'll receive a 429 Too Many Requests response with a Retry-After header.

## API Reference

For a complete list of all available endpoints, parameters, and response formats, see the [API Documentation](../api/README.md).

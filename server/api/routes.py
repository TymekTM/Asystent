"""API routes for Gaja Web UI integration.

Provides REST API endpoints for web UI functionality.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

# Import server components
# from server_main import server_app  # Import moved to avoid circular import
from plugin_manager import plugin_manager
from pydantic import BaseModel, Field

# Server app will be injected after initialization
server_app = None


def set_server_app(app):
    """Set server app instance after initialization."""
    global server_app
    server_app = app


# Security
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Router
router = APIRouter(prefix="/api/v1", tags=["api"])


# Request/Response models
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str
    user: dict[str, Any]


class UserSettings(BaseModel):
    voice: str | None = None
    language: str = "pl"
    wakeWord: bool | None = None
    privacy: dict[str, Any] | None = None


class User(BaseModel):
    id: str
    email: str
    role: str
    settings: UserSettings
    createdAt: str


class Memory(BaseModel):
    id: str
    userId: str
    content: str
    createdAt: str
    importance: int = Field(ge=0, le=5)
    isDeleted: bool = False
    tags: list[str] | None = None


class Plugin(BaseModel):
    slug: str
    name: str
    version: str
    enabled: bool
    author: str
    description: str | None = None
    installedAt: str | None = None


class SystemMetrics(BaseModel):
    cpu: float
    ram: dict[str, int]
    gpu: dict[str, int] | None = None
    tokensPerSecond: float | None = None
    uptime: int


class LogEntry(BaseModel):
    id: str
    level: str
    message: str
    timestamp: str
    module: str | None = None
    metadata: dict[str, Any] | None = None


class ApiResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: str | None = None
    message: str | None = None


# Mock users for demo - in production, use proper authentication
MOCK_USERS = {
    "admin@gaja.app": {
        "id": "1",
        "email": "admin@gaja.app",
        "role": "admin",
        "password": "admin123",
        "settings": {
            "language": "en",
            "voice": "default",
            "wakeWord": True,
            "privacy": {"shareAnalytics": True, "storeConversations": True},
        },
    },
    "demo@mail.com": {
        "id": "2",
        "email": "demo@mail.com",
        "role": "user",
        "password": "demo",
        "settings": {
            "language": "pl",
            "voice": "default",
            "wakeWord": True,
            "privacy": {"shareAnalytics": False, "storeConversations": True},
        },
    },
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Get current user from JWT token (mock implementation)."""
    token = credentials.credentials

    # Check if it's a mock token first (for backward compatibility)
    if token == "valid-token":
        return MOCK_USERS["admin@gaja.app"]
    elif token == "demo-token":
        return MOCK_USERS["demo@mail.com"]
    else:
        # Try to decode JWT token from frontend
        try:
            # Simple JWT validation - in production, use proper library like PyJWT
            import base64
            import json

            # Split JWT token
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")

            # Decode payload (without signature verification for demo)
            payload_b64 = parts[1]
            # Add padding if needed
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload_json = base64.b64decode(payload_b64)
            payload = json.loads(payload_json)

            # Check if user exists in our mock users
            user_id = payload.get("userId")
            email = payload.get("email")

            # Find user by email or ID
            for user_email, user_data in MOCK_USERS.items():
                if user_data["email"] == email or user_data["id"] == user_id:
                    return user_data

            raise HTTPException(status_code=401, detail="User not found")

        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")


def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
) -> dict[str, Any] | None:
    """Optional authentication for public endpoints."""
    if not credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


# Auth endpoints
@router.post("/auth/login")
async def login(request: LoginRequest) -> LoginResponse:
    """User login endpoint."""
    try:
        user = MOCK_USERS.get(request.email)
        if not user or user["password"] != request.password:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Mock token generation
        token = "valid-token" if request.email == "admin@gaja.app" else "demo-token"

        return LoginResponse(
            success=True,
            token=token,
            user={
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "settings": user["settings"],
                "createdAt": datetime.now().isoformat(),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/auth/magic-link")
async def magic_link(request: dict[str, str]) -> ApiResponse:
    """Send magic link (mock implementation)."""
    email = request.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    # Mock magic link sending
    logger.info(f"Magic link sent to {email}")
    return ApiResponse(success=True, message="Magic link sent")


@router.get("/me")
async def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> User:
    """Get current user information."""
    return User(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        settings=UserSettings(**current_user["settings"]),
        createdAt=datetime.now().isoformat(),
    )


@router.patch("/me/settings")
async def update_settings(
    settings: UserSettings, current_user: dict[str, Any] = Depends(get_current_user)
) -> User:
    """Update user settings."""
    # Update user settings in mock data
    MOCK_USERS[current_user["email"]]["settings"].update(
        settings.dict(exclude_unset=True)
    )

    return User(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        settings=UserSettings(**MOCK_USERS[current_user["email"]]["settings"]),
        createdAt=datetime.now().isoformat(),
    )


# Memory endpoints
@router.get("/memory")
async def get_memories(
    page: int = 1,
    limit: int = 20,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get user memories."""
    try:
        user_id = current_user["id"]

        # Get memories from database
        if hasattr(server_app, "db_manager"):
            history = await server_app.db_manager.get_user_history(user_id, limit=limit)

            memories = []
            for i, item in enumerate(history):
                memories.append(
                    {
                        "id": str(i),
                        "userId": user_id,
                        "content": item.get("user_query", "")
                        + " -> "
                        + item.get("ai_response", ""),
                        "createdAt": item.get("timestamp", datetime.now().isoformat()),
                        "importance": 3,  # Default importance
                        "isDeleted": False,
                        "tags": ["conversation"],
                    }
                )

            return {"memories": memories, "total": len(memories)}
        else:
            return {"memories": [], "total": 0}

    except Exception as e:
        logger.error(f"Get memories error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get memories")


@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str, current_user: dict[str, Any] = Depends(get_current_user)
) -> ApiResponse:
    """Delete a memory."""
    # Mock implementation - in production, delete from database
    logger.info(f"Memory {memory_id} deleted by user {current_user['id']}")
    return ApiResponse(success=True, message="Memory deleted")


# Plugin endpoints
@router.get("/plugins")
async def get_plugins(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> list[Plugin]:
    """Get available plugins."""
    try:
        plugins = []

        if server_app and hasattr(server_app, "plugin_manager"):
            pm = server_app.plugin_manager
            user_plugins = pm.get_user_plugins(current_user["id"])

            for plugin_name, plugin_info in pm.plugins.items():
                plugins.append(
                    Plugin(
                        slug=plugin_name,
                        name=plugin_info.name,
                        version=plugin_info.version,
                        enabled=user_plugins.get(plugin_name, False),
                        author=plugin_info.author,
                        description=plugin_info.description,
                        installedAt=datetime.now().isoformat(),
                    )
                )
        else:
            # Fallback to global plugin_manager
            user_plugins = plugin_manager.get_user_plugins(current_user["id"])

            for plugin_name, plugin_info in plugin_manager.plugins.items():
                plugins.append(
                    Plugin(
                        slug=plugin_name,
                        name=plugin_info.name,
                        version=plugin_info.version,
                        enabled=user_plugins.get(plugin_name, False),
                        author=plugin_info.author,
                        description=plugin_info.description,
                        installedAt=datetime.now().isoformat(),
                    )
                )

        return plugins

    except Exception as e:
        logger.error(f"Get plugins error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get plugins")


@router.patch("/plugins/{plugin_slug}")
async def toggle_plugin(
    plugin_slug: str,
    request: dict[str, bool],
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Plugin:
    """Toggle plugin enabled status."""
    try:
        enabled = request.get("enabled", False)
        user_id = current_user["id"]

        if hasattr(server_app, "plugin_manager"):
            pm = server_app.plugin_manager

            if enabled:
                success = await pm.enable_plugin_for_user(user_id, plugin_slug)
            else:
                success = await pm.disable_plugin_for_user(user_id, plugin_slug)

            if not success:
                raise HTTPException(status_code=400, detail="Failed to toggle plugin")

            # Update database
            if hasattr(server_app, "db_manager"):
                await server_app.db_manager.update_user_plugin_status(
                    user_id, plugin_slug, enabled
                )

            # Return updated plugin info
            plugin_info = pm.plugins.get(plugin_slug)
            if plugin_info:
                return Plugin(
                    slug=plugin_slug,
                    name=plugin_info.name,
                    version=plugin_info.version,
                    enabled=enabled,
                    author=plugin_info.author,
                    description=plugin_info.description,
                    installedAt=datetime.now().isoformat(),
                )

        raise HTTPException(status_code=404, detail="Plugin not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toggle plugin error: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle plugin")


# System metrics endpoints
@router.get("/metrics")
async def get_metrics(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> SystemMetrics:
    """Get system metrics."""
    try:
        import psutil

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        # Get uptime
        uptime = 0
        if hasattr(server_app, "start_time"):
            uptime = int((datetime.now() - server_app.start_time).total_seconds())

        return SystemMetrics(
            cpu=cpu_percent,
            ram={"used": memory.used, "total": memory.total},
            uptime=uptime,
        )

    except Exception as e:
        logger.error(f"Get metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


# Log endpoints
@router.get("/logs")
async def get_logs(
    level: str | None = None,
    tail: int | None = 100,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[LogEntry]:
    """Get system logs."""
    try:
        logs = []

        # Read from log files
        logs_dir = Path("logs")
        if logs_dir.exists():
            log_files = sorted(
                logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True
            )

            if log_files:
                log_file = log_files[0]  # Most recent log file

                try:
                    with open(log_file, encoding="utf-8") as f:
                        lines = f.readlines()

                    # Get last 'tail' lines
                    recent_lines = (
                        lines[-tail:] if tail and len(lines) > tail else lines
                    )

                    for i, line in enumerate(recent_lines):
                        # Parse log line (simplified)
                        parts = line.strip().split(" | ")
                        if len(parts) >= 4:
                            timestamp = parts[0]
                            level_str = parts[1]
                            location = parts[2]
                            message = parts[3]

                            # Filter by level if specified
                            if level and level_str.upper() != level.upper():
                                continue

                            logs.append(
                                LogEntry(
                                    id=str(i),
                                    level=level_str.lower(),
                                    message=message,
                                    timestamp=timestamp,
                                    module=location.split(":")[0]
                                    if ":" in location
                                    else None,
                                )
                            )

                except Exception as e:
                    logger.error(f"Error reading log file: {e}")

        return logs

    except Exception as e:
        logger.error(f"Get logs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get logs")


# Health check endpoint
@router.get("/healthz")
async def health_check(
    user: dict[str, Any] | None = Depends(optional_auth)
) -> dict[str, Any]:
    """Health check endpoint."""
    try:
        uptime = 0
        if hasattr(server_app, "start_time"):
            uptime = int((datetime.now() - server_app.start_time).total_seconds())

        return {
            "version": "1.0.0",
            "uptime": uptime,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


# AI Query endpoint for web UI
@router.post("/ai/query")
async def ai_query(
    request: dict[str, Any], current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """Process AI query from web UI."""
    try:
        query = request.get("query", "")
        context = request.get("context", {})

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Process query using server's AI module
        request_data = {"type": "ai_query", "query": query, "context": context}

        response = await server_app.process_user_request(
            current_user["id"], request_data
        )

        if response.get("type") == "error":
            raise HTTPException(
                status_code=500, detail=response.get("message", "AI query failed")
            )

        return {
            "success": True,
            "response": response.get("response", ""),
            "timestamp": response.get("timestamp", datetime.now().timestamp()),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI query error: {e}")
        raise HTTPException(status_code=500, detail="AI query failed")


# WebSocket status endpoint
@router.get("/ws/status")
async def ws_status(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """Get WebSocket connection status."""
    try:
        user_id = current_user["id"]

        # Check if user is connected via WebSocket
        connected = False
        if hasattr(server_app, "connection_manager"):
            connected = user_id in server_app.connection_manager.active_connections

        return {
            "connected": connected,
            "userId": user_id,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"WebSocket status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get WebSocket status")


# Daily briefing endpoint
@router.get("/briefing/daily")
async def get_daily_briefing(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """Get daily briefing for user."""
    try:
        user_id = current_user["id"]

        if hasattr(server_app, "daily_briefing"):
            briefing = await server_app.daily_briefing.generate_daily_briefing(user_id)
            return {
                "success": True,
                "briefing": briefing,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"success": False, "error": "Daily briefing not available"}

    except Exception as e:
        logger.error(f"Daily briefing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get daily briefing")


# Export router
__all__ = ["router"]

"""GAJA Assistant Server Główny serwer obsługujący wielu użytkowników, zarządzający AI,
bazą danych i pluginami."""

import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any

import uvicorn
from environment_manager import EnvironmentManager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from server import onboarding_module as server_onboarding
from server.ai_module import AIModule
from server.config_loader import load_config
from server.daily_briefing_module import DailyBriefingModule
from server.database_manager import initialize_database_manager
from server.day_narrative_module import DayNarrativeModule
from server.day_summary_module import DaySummaryModule
from server.extended_webui import ExtendedWebUI
from server.function_calling_system import FunctionCallingSystem
from server.plugin_manager import plugin_manager
from server.plugin_monitor import plugin_monitor
from server.proactive_assistant_simple import get_proactive_assistant
from server.routines_learner_module import RoutinesLearnerModule
from server.user_behavior_module import UserBehaviorModule

OnboardingModule = server_onboarding.OnboardingModule


# Data models for REST API
class AIQueryRequest(BaseModel):
    user_id: str
    query: str
    context: dict = {}


class UserHistoryRequest(BaseModel):
    user_id: str
    limit: int = 50


class AIQueryResponse(BaseModel):
    ai_response: str
    function_calls: list = []
    plugins_used: list = []


class UserHistoryResponse(BaseModel):
    history: list
    total_count: int


class RequestType(str, Enum):
    HANDSHAKE = "handshake"
    QUERY = "query"
    AUDIO = "audio"
    FUNCTION_CALL = "function_call"


class WebSocketRequest(BaseModel):
    type: RequestType
    version: str | None = None
    data: dict[str, Any] | None = None
    query: str | None = None
    user_id: str | None = None
    audio_data: str | None = None
    function_name: str | None = None
    parameters: dict[str, Any] | None = None


class WebSocketResponse(BaseModel):
    type: str
    success: bool = True
    data: dict[str, Any] | None = None
    error: str | None = None
    server_version: str | None = None
    ai_response: str | None = None
    result: Any | None = None


class ConnectionManager:
    """Zarządza połączeniami WebSocket z klientami."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.user_sessions: dict[str, dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Połącz nowego klienta."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_sessions[user_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "status": "connected",
        }
        logger.info(f"User {user_id} connected")

    def disconnect(self, user_id: str):
        """Rozłącz klienta."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: str):
        """Wyślij wiadomość do konkretnego użytkownika."""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast(self, message: dict, exclude_user: str | None = None):
        """Wyślij wiadomość do wszystkich podłączonych użytkowników."""
        for user_id, websocket in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {user_id}: {e}")
                self.disconnect(user_id)

    def update_user_status(self, user_id: str, status: str, message: str = ""):
        """Aktualizuj status użytkownika."""
        if user_id in self.user_sessions:
            self.user_sessions[user_id]["status"] = status
            self.user_sessions[user_id]["last_message"] = message
            logger.debug(f"Updated status for {user_id}: {status}")

    def get_user_status(self, user_id: str) -> dict[str, Any]:
        """Pobierz status użytkownika."""
        return self.user_sessions.get(user_id, {})


class ServerApp:
    """Główna klasa serwera GAJA."""

    def __init__(self):
        self.config = None
        self.db_manager = None
        self.ai_module = None
        self.function_system = None
        self.connection_manager = ConnectionManager()
        self.user_plugins: dict[str, dict[str, Any]] = {}

        # New modules
        self.onboarding_module = None
        self.plugin_monitor = plugin_monitor
        self.web_ui = None
        self.start_time = None

        # Daily briefing and proactive modules
        self.daily_briefing = None
        self.day_summary = None
        self.user_behavior = None
        self.routines_learner = None
        self.day_narrative = None
        self.proactive_assistant = None

    async def initialize(self):
        """Inicjalizuj wszystkie komponenty serwera."""
        try:
            from datetime import datetime

            self.start_time = datetime.now()

            # Załaduj konfigurację
            self.config = load_config("server_config.json")
            logger.info("Configuration loaded")

            # Konfiguruj CORS - dodaj middleware po załadowaniu konfiguracji
            self._configure_cors_middleware()

            # Inicjalizuj bazę danych
            self.db_manager = initialize_database_manager("server_data.db")
            await self.db_manager.initialize()
            logger.info("Database initialized")

            # Inicjalizuj moduły konfiguracji i onboarding
            from config_loader import ConfigLoader

            config_loader = ConfigLoader("server_config.json")
            self.onboarding_module = OnboardingModule(config_loader, self.db_manager)
            logger.info("Onboarding module initialized")

            # Inicjalizuj Web UI
            self.web_ui = ExtendedWebUI(config_loader, self.db_manager)
            self.web_ui.set_server_app(self)
            logger.info("Extended Web UI initialized")

            # Inicjalizuj AI module
            self.ai_module = AIModule(self.config)
            logger.info("AI module initialized")

            # Inicjalizuj system funkcji
            self.function_system = FunctionCallingSystem()
            await self.function_system.initialize()
            logger.info("Function calling system initialized")

            # Inicjalizuj plugin manager
            await plugin_manager.discover_plugins()
            await self.load_all_user_plugins()
            logger.info("Plugin manager initialized")

            # Inicjalizuj monitorowanie pluginów
            await self.plugin_monitor.start_monitoring()
            logger.info(
                "Plugin monitoring started"
            )  # Inicjalizuj moduły daily briefing
            self.daily_briefing = DailyBriefingModule(
                self.config.get("daily_briefing", {})
            )
            self.day_summary = DaySummaryModule(self.config, self.db_manager)
            self.user_behavior = UserBehaviorModule(self.config, self.db_manager)
            self.routines_learner = RoutinesLearnerModule(self.config, self.db_manager)
            self.day_narrative = DayNarrativeModule(self.config, self.db_manager)
            logger.info("Daily briefing modules initialized")
            # Inicjalizuj proaktywnego asystenta
            self.proactive_assistant = get_proactive_assistant()
            self.proactive_assistant.start()
            logger.info("Proactive assistant started")

            logger.success("Server initialization completed")

        except Exception as e:
            logger.error(f"Server initialization failed: {e}")
            raise

    async def load_all_user_plugins(self):
        """Załaduj pluginy dla wszystkich użytkowników z bazy danych."""
        try:
            # Pobierz listę użytkowników z bazy
            users = await self.db_manager.get_all_users()

            for user in users:
                user_id = str(user.get("id"))
                enabled_plugins = user.get("enabled_plugins", [])

                for plugin_name in enabled_plugins:
                    try:
                        await plugin_manager.enable_plugin_for_user(
                            user_id, plugin_name
                        )
                        logger.info(f"Plugin {plugin_name} enabled for user {user_id}")
                    except Exception as e:
                        logger.error(
                            f"Failed to enable plugin {plugin_name} for user {user_id}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to load user plugins: {e}")

    def _configure_cors_middleware(self):
        """Konfiguruje CORS middleware z bezpiecznymi ustawieniami."""
        cors_origins = self.config.get("security", {}).get(
            "cors_origins", ["http://localhost:3000", "http://localhost:8080"]
        )

        # Sprawdź czy używamy niebezpiecznej konfiguracji
        if "*" in cors_origins:
            logger.warning(
                "CORS is configured to allow all origins (*). This is not recommended for production!"
            )
            if not self.config.get("server", {}).get("debug", False):
                logger.error("Wildcard CORS is only allowed in debug mode!")
                cors_origins = ["http://localhost:3000", "http://localhost:8080"]
        # Import app z modułu globalnego - to może być problematyczne
        # Lepiej będzie to zrobić w main()
        logger.info(f"Configuring CORS for origins: {cors_origins}")

    async def load_plugin(self, plugin_name: str):
        """Dynamicznie załaduj plugin z walidacją bezpieczeństwa.

        Args:
            plugin_name: Nazwa pluginu (tylko alfanumeryczne znaki i podkreślenia)
        """
        try:
            # Walidacja nazwy pluginu - zapobieganie path traversal
            if not plugin_name.replace("_", "").replace("-", "").isalnum():
                logger.error(
                    f"Invalid plugin name: {plugin_name}. Only alphanumeric characters, hyphens and underscores allowed."
                )
                return None

            # Dodatkowa walidacja - nie pozwalaj na ../  lub inne niebezpieczne znaki
            if (
                ".." in plugin_name
                or "/" in plugin_name
                or "\\" in plugin_name
                or plugin_name.startswith(".")
            ):
                logger.error(
                    f"Plugin name contains prohibited characters: {plugin_name}"
                )
                return None

            # Sprawdź długość nazwy (zapobieganie atakom)
            if len(plugin_name) > 50:
                logger.error(f"Plugin name too long: {plugin_name}")
                return None

            # Whitelist dozwolonych pluginów (jeśli skonfigurowane)
            allowed_plugins = self.config.get("plugins", {}).get("whitelist", [])
            if allowed_plugins and plugin_name not in allowed_plugins:
                logger.error(
                    f"Plugin {plugin_name} not in whitelist: {allowed_plugins}"
                )
                return None

            # Sprawdź czy plugin istnieje w modules/ (używaj bezpiecznej konstrukcji ścieżki)
            modules_dir = Path("modules").resolve()  # Resolve to absolute path
            plugin_path = modules_dir / f"{plugin_name}.py"

            # Upewnij się, że ścieżka jest wewnątrz katalogu modules
            if not str(plugin_path.resolve()).startswith(str(modules_dir)):
                logger.error(f"Plugin path outside modules directory: {plugin_path}")
                return None

            if not plugin_path.exists():
                logger.warning(f"Plugin {plugin_name} not found at {plugin_path}")
                return None

            # Sprawdź, czy plik nie jest za duży (zapobieganie atakom DoS)
            file_size = plugin_path.stat().st_size
            max_size = self.config.get("plugins", {}).get(
                "max_file_size", 1024 * 1024
            )  # 1MB default
            if file_size > max_size:
                logger.error(
                    f"Plugin file too large: {file_size} bytes (max {max_size})"
                )
                return None

            # Sprawdź uprawnienia pliku
            if not os.access(plugin_path, os.R_OK):
                logger.error(f"Cannot read plugin file: {plugin_path}")
                return None

            # Dynamiczny import modułu z timeout
            import importlib.util
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Plugin loading timeout")

            # Set timeout for plugin loading (Unix only)
            timeout_seconds = 10
            if hasattr(signal, "SIGALRM"):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)

            try:
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                if not spec or not spec.loader:
                    logger.error(f"Could not create module spec for {plugin_name}")
                    return None

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Sprawdź czy moduł ma wymagane funkcje
                required_functions = ["execute_function", "get_functions"]
                missing_functions = [
                    func for func in required_functions if not hasattr(module, func)
                ]

                if missing_functions:
                    logger.warning(
                        f"Plugin {plugin_name} missing required functions: {missing_functions}"
                    )
                    return None

                # Sprawdź czy plugin ma opcjonalne metadane bezpieczeństwa
                if hasattr(module, "PLUGIN_METADATA"):
                    metadata = module.PLUGIN_METADATA
                    if "permissions" in metadata:
                        logger.info(
                            f"Plugin {plugin_name} requires permissions: {metadata['permissions']}"
                        )
                    if "version" in metadata:
                        logger.info(
                            f"Plugin {plugin_name} version: {metadata['version']}"
                        )

                logger.info(f"Successfully loaded plugin: {plugin_name}")
                return module

            finally:
                # Clear timeout
                if hasattr(signal, "SIGALRM"):
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)

        except TimeoutError:
            logger.error(f"Plugin {plugin_name} loading timed out")
            return None
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return None

    async def process_user_request(self, user_id: str, request_data: dict):
        """Przetwórz request od użytkownika."""
        try:
            request_type = request_data.get("type")

            if request_type == "ai_query":
                return await self.handle_ai_query(user_id, request_data)
            elif request_type == "function_call":
                return await self.handle_function_call(user_id, request_data)
            elif request_type == "plugin_toggle":
                return await self.handle_plugin_toggle(user_id, request_data)
            elif request_type == "plugin_list":
                return await self.handle_plugin_list(user_id)
            elif request_type == "status_update":
                return await self.handle_status_update(user_id, request_data)
            elif request_type == "startup_briefing":
                return await self.handle_startup_briefing_request(user_id)
            elif request_type == "day_summary":
                return await self.handle_day_summary_request(user_id, request_data)
            elif request_type == "get_proactive_notifications":
                return await self.handle_proactive_notifications(user_id)
            elif request_type == "dismiss_notification":
                return await self.handle_dismiss_notification(user_id, request_data)
            elif request_type == "update_user_context":
                return await self.handle_update_user_context(user_id, request_data)
            else:
                return {
                    "type": "error",
                    "message": f"Unknown request type: {request_type}",
                }

        except Exception as e:
            logger.error(f"Error processing request for user {user_id}: {e}")
            return {"type": "error", "message": f"Request processing failed: {str(e)}"}

    async def handle_ai_query(self, user_id: str, request_data: dict):
        """Obsłuż zapytanie AI."""
        try:
            query = request_data.get("query", "")
            context = request_data.get("context", {})

            # Handle both string and numeric user_id
            try:
                numeric_user_id = int(user_id)
            except (ValueError, TypeError):
                # For string user_id, generate a numeric hash for database compatibility
                numeric_user_id = abs(hash(user_id)) % (10**9)
                logger.debug(
                    f"String user_id '{user_id}' converted to numeric: {numeric_user_id}"
                )

            user_level = self.db_manager.get_user_level(numeric_user_id)
            monthly = self.db_manager.count_api_calls(numeric_user_id, days=30)
            daily = self.db_manager.count_api_calls(numeric_user_id, days=1)
            limits = {
                "free": {"monthly": 1000, "daily": 100},
                "plus": {"monthly": 10000, "daily": None},
                "pro": {"monthly": 50000, "daily": None},
            }
            limit = limits.get(user_level, limits["free"])
            if monthly >= limit["monthly"] or (
                limit["daily"] is not None and daily >= limit["daily"]
            ):
                return {
                    "type": "error",
                    "message": "Query limit reached for your account.",
                }

            # Pobierz historię użytkownika z bazy
            logger.debug("About to call get_user_history")
            user_history = await self.db_manager.get_user_history(user_id)
            logger.debug(f"get_user_history returned: {type(user_history)}")

            # Przygotuj kontekst dla AI
            logger.debug("About to call get_available_functions")
            available_plugins = list(
                plugin_manager.get_available_functions(user_id).keys()
            )
            logger.debug(f"get_available_functions returned: {type(available_plugins)}")

            logger.debug("About to call get_modules_for_user")
            modules = plugin_manager.get_modules_for_user(user_id)
            logger.debug(f"get_modules_for_user returned: {type(modules)}")

            logger.debug(f"user_history = {user_history}")
            logger.debug(
                f"user_history length = {len(user_history) if user_history else 'None'}"
            )
            logger.debug(f"available_plugins = {available_plugins}")
            logger.debug(
                f"modules keys = {list(modules.keys()) if modules else 'None'}"
            )
            logger.debug(f"modules = {modules}")

            ai_context = {
                "user_id": user_id,
                "history": user_history,
                "available_plugins": available_plugins,
                "modules": modules,
                "user_name": context.get("user_name", "User"),
                **context,
            }

            logger.info(f"Processing AI query for user {user_id}: FULL_QUERY=[{query}]")
            logger.info(f"Request data received: {request_data}")
            logger.info(f"Context received: {context}")

            # Przetwórz zapytanie przez AI
            response = await self.ai_module.process_query(query, ai_context)

            logger.info(f"AI response received: {response[:100]}...")

            # Zapisz interakcję w bazie
            save_result = await self.db_manager.save_interaction(
                user_id, query, response
            )
            logger.debug(f"save_interaction result = {save_result}")

            return {
                "type": "ai_response",
                "response": response,
                "timestamp": time.time(),
                "tts_engine": "edge" if user_level == "free" else "openai",
            }

        except Exception as e:
            logger.error(f"AI query error for user {user_id}: {e}")
            return {"type": "error", "message": f"AI query failed: {str(e)}"}

    async def handle_function_call(self, user_id: str, request_data: dict):
        """Obsłuż wywołanie funkcji pluginu."""
        try:
            plugin_name = request_data.get("plugin")
            function_name = request_data.get("function")
            parameters = request_data.get("parameters", {})

            if not plugin_name or not function_name:
                return {"type": "error", "message": "Missing plugin or function name"}

            # Sprawdź czy plugin jest włączony dla użytkownika
            user_plugins = plugin_manager.get_user_plugins(user_id)
            if not user_plugins.get(plugin_name, False):
                return {
                    "type": "error",
                    "message": f"Plugin {plugin_name} is not enabled for user",
                }

            # Załaduj plugin jeśli nie jest załadowany
            if not plugin_manager.is_plugin_loaded(plugin_name):
                await plugin_manager.load_plugin(plugin_name)

            # Pobierz moduł pluginu
            plugin_info = plugin_manager.plugins.get(plugin_name)
            if not plugin_info or not plugin_info.module:
                return {
                    "type": "error",
                    "message": f"Plugin {plugin_name} module not available",
                }

            plugin_module = plugin_info.module

            # Wykonaj funkcję
            if hasattr(plugin_module, "execute_function"):
                # Handle both string and numeric user_id
                try:
                    numeric_user_id = int(user_id)
                except (ValueError, TypeError):
                    numeric_user_id = abs(hash(user_id)) % (10**9)

                result = await plugin_module.execute_function(
                    function_name, parameters, numeric_user_id
                )

                return {
                    "type": "function_result",
                    "plugin": plugin_name,
                    "function": function_name,
                    "result": result,
                }
            else:
                return {
                    "type": "error",
                    "message": f"Plugin {plugin_name} does not support function execution",
                }

        except Exception as e:
            logger.error(f"Function call error: {e}")
            return {"type": "error", "message": f"Function call failed: {str(e)}"}

    async def handle_plugin_toggle(self, user_id: str, request_data: dict):
        """Obsłuż włączanie/wyłączanie pluginu."""
        try:
            plugin_name = request_data.get("plugin")
            action = request_data.get("action", "toggle")  # enable, disable, toggle

            if not plugin_name:
                return {"type": "error", "message": "Plugin name required"}

            logger.info(f"Plugin {action} request from user {user_id}: {plugin_name}")

            if action == "enable":
                success = await plugin_manager.enable_plugin_for_user(
                    user_id, plugin_name
                )
                status = "enabled" if success else "failed"
            elif action == "disable":
                success = await plugin_manager.disable_plugin_for_user(
                    user_id, plugin_name
                )
                status = "disabled" if success else "failed"
            elif action == "toggle":
                # Sprawdź aktualny status i przełącz
                user_plugins = plugin_manager.get_user_plugins(user_id)
                is_enabled = user_plugins.get(plugin_name, False)

                if is_enabled:
                    success = await plugin_manager.disable_plugin_for_user(
                        user_id, plugin_name
                    )
                    status = "disabled" if success else "failed"
                else:
                    success = await plugin_manager.enable_plugin_for_user(
                        user_id, plugin_name
                    )
                    status = "enabled" if success else "failed"
            else:
                return {"type": "error", "message": f"Unknown action: {action}"}

            if success:
                # Aktualizuj bazę danych jeśli to konieczne
                await self.db_manager.update_user_plugin_status(
                    user_id, plugin_name, status == "enabled"
                )

                return {
                    "type": "plugin_toggled",
                    "plugin": plugin_name,
                    "status": status,
                    "success": True,
                }
            else:
                return {
                    "type": "error",
                    "message": f"Failed to {action} plugin {plugin_name}",
                }

        except Exception as e:
            logger.error(f"Plugin toggle error: {e}")
            return {"type": "error", "message": f"Plugin toggle failed: {str(e)}"}

    async def handle_plugin_list(self, user_id: str):
        """Zwróć listę dostępnych pluginów i ich status."""
        try:
            all_plugins = plugin_manager.get_all_plugins()
            user_plugins = plugin_manager.get_user_plugins(user_id)

            plugin_list = []
            for plugin_name, plugin_info in all_plugins.items():
                plugin_list.append(
                    {
                        "name": plugin_name,
                        "description": plugin_info.description,
                        "version": plugin_info.version,
                        "author": plugin_info.author,
                        "functions": plugin_info.functions,
                        "enabled": user_plugins.get(plugin_name, False),
                        "loaded": plugin_info.loaded,
                    }
                )

            return {"type": "plugin_list", "plugins": plugin_list}

        except Exception as e:
            logger.error(f"Plugin list error: {e}")
            return {"type": "error", "message": f"Failed to get plugin list: {str(e)}"}

    async def handle_status_update(self, user_id: str, request_data: dict):
        """Obsłuż aktualizację statusu użytkownika."""
        try:
            status = request_data.get("status", "unknown")
            message = request_data.get("message", "")

            # Aktualizuj status w connection manager
            self.connection_manager.update_user_status(user_id, status, message)

            return {
                "type": "status_updated",
                "status": status,
                "message": "Status updated successfully",
            }

        except Exception as e:
            logger.error(f"Error updating status for user {user_id}: {e}")
            return {"type": "error", "message": f"Status update failed: {str(e)}"}

    async def handle_startup_briefing_request(self, user_id: str):
        """Obsłuż request briefingu startowego."""
        try:
            if not self.daily_briefing:
                return {
                    "type": "error",
                    "message": "Daily briefing module not available",
                }

            # Check if briefing should be delivered (prevents duplicates)
            if not self.daily_briefing.should_deliver_briefing():
                logger.info(f"Briefing already delivered today for user {user_id}")
                return {
                    "type": "startup_briefing",
                    "briefing": "Briefing już został dzisiaj dostarczony. Miłego dnia!",
                }

            briefing = await self.daily_briefing.generate_daily_briefing(user_id)

            # Mark briefing as delivered
            self.daily_briefing._mark_briefing_delivered()

            return {"type": "startup_briefing", "briefing": briefing}

        except Exception as e:
            logger.error(f"Error generating startup briefing for user {user_id}: {e}")
            return {"type": "error", "message": f"Startup briefing failed: {str(e)}"}

    async def handle_day_summary_request(self, user_id: str, request_data: dict):
        """Obsłuż request podsumowania dnia."""
        try:
            if not self.day_summary:
                return {"type": "error", "message": "Day summary module not available"}

            summary_type = request_data.get("summary_type", "default")
            date_filter = request_data.get("date", None)

            summary = await self.day_summary.generate_summary(
                user_id, summary_type, date_filter
            )

            return {"type": "day_summary", "summary": summary}

        except Exception as e:
            logger.error(f"Error generating day summary for user {user_id}: {e}")
            return {"type": "error", "message": f"Day summary failed: {str(e)}"}

    async def handle_proactive_notifications(self, user_id: str):
        """Obsłuż request proaktywnych powiadomień."""
        try:
            if not self.proactive_assistant:
                return {"type": "error", "message": "Proactive assistant not available"}

            notifications = await self.proactive_assistant.get_notifications(user_id)

            return {"type": "proactive_notifications", "notifications": notifications}

        except Exception as e:
            logger.error(
                f"Error getting proactive notifications for user {user_id}: {e}"
            )
            return {
                "type": "error",
                "message": f"Getting notifications failed: {str(e)}",
            }

    async def handle_dismiss_notification(self, user_id: str, request_data: dict):
        """Obsłuż odrzucenie powiadomienia."""
        try:
            if not self.proactive_assistant:
                return {"type": "error", "message": "Proactive assistant not available"}

            notification_id = request_data.get("notification_id")
            if not notification_id:
                return {"type": "error", "message": "Notification ID required"}

            success = await self.proactive_assistant.dismiss_notification(
                user_id, notification_id
            )

            return {
                "type": "notification_dismissed",
                "success": success,
                "notification_id": notification_id,
            }

        except Exception as e:
            logger.error(f"Error dismissing notification for user {user_id}: {e}")
            return {
                "type": "error",
                "message": f"Dismissing notification failed: {str(e)}",
            }

    async def handle_update_user_context(self, user_id: str, request_data: dict):
        """Obsłuż aktualizację kontekstu użytkownika."""
        try:
            if not self.proactive_assistant:
                return {"type": "error", "message": "Proactive assistant not available"}

            context_data = request_data.get("context", {})

            await self.proactive_assistant.update_user_context(user_id, context_data)

            return {
                "type": "context_updated",
                "message": "User context updated successfully",
            }

        except Exception as e:
            logger.error(f"Error updating user context for user {user_id}: {e}")
            return {"type": "error", "message": f"Context update failed: {str(e)}"}

    async def send_proactive_notifications_to_clients(self, user_id: str = None):
        """Wyślij proaktywne powiadomienia do klientów."""
        try:
            if not self.proactive_assistant:
                return

            # Jeśli nie podano user_id, wyślij do wszystkich
            if user_id is None:
                for uid in self.connection_manager.active_connections.keys():
                    await self._send_notifications_to_user(uid)
            else:
                await self._send_notifications_to_user(user_id)

        except Exception as e:
            logger.error(f"Error sending proactive notifications: {e}")

    async def _send_notifications_to_user(self, user_id: str):
        """Wyślij powiadomienia do konkretnego użytkownika."""
        try:
            notifications = await self.proactive_assistant.get_notifications(user_id)

            if notifications:
                message = {
                    "type": "proactive_notifications",
                    "notifications": notifications,
                }

                await self.connection_manager.send_personal_message(message, user_id)

        except Exception as e:
            logger.error(f"Error sending notifications to user {user_id}: {e}")

    def _configure_cors_middleware(self):
        """Konfiguruje CORS middleware z bezpiecznymi ustawieniami."""
        cors_origins = self.config.get("security", {}).get(
            "cors_origins", ["http://localhost:3000", "http://localhost:8080"]
        )

        # Sprawdź czy używamy niebezpiecznej konfiguracji
        if "*" in cors_origins:
            logger.warning(
                "CORS is configured to allow all origins (*). This is not recommended for production!"
            )
            if not self.config.get("server", {}).get("debug", False):
                logger.error(
                    "Wildcard CORS is only allowed in debug mode! Using safe defaults."
                )
                cors_origins = ["http://localhost:3000", "http://localhost:8080"]

        # Import app z modułu globalnego - to może być problematyczne
        # Lepiej będzie to zrobić w main()
        logger.info(f"Configuring CORS for origins: {cors_origins}")


# Globalna instancja serwera
server_app = ServerApp()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Zarządzanie cyklem życia aplikacji FastAPI."""
    # Startup
    await server_app.initialize()
    yield
    # Shutdown
    logger.info("Server shutting down...")


# Inicjalizuj FastAPI
app = FastAPI(
    title="GAJA Assistant Server",
    description="Server obsługujący AI Assistant dla wielu użytkowników",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "GAJA Assistant Server", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_connections": len(server_app.connection_manager.active_connections),
        "loaded_users": len(server_app.user_plugins),
    }


@app.post("/api/ai_query")
async def api_ai_query(request: AIQueryRequest):
    """REST API endpoint for AI queries."""
    try:
        logger.info(f"API AI query from user {request.user_id}: {request.query}")

        # Prepare request data in WebSocket format
        request_data = {
            "type": "ai_query",
            "query": request.query,
            "context": request.context,
        }

        # Process the request
        response = await server_app.process_user_request(request.user_id, request_data)

        if response.get("type") == "error":
            raise HTTPException(
                status_code=500, detail=response.get("message", "Unknown error")
            )

        return {
            "ai_response": response.get("response", ""),
            "function_calls": response.get("function_calls", []),
            "plugins_used": response.get("plugins_used", []),
        }

    except Exception as e:
        logger.error(f"Error in API AI query: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/get_user_history")
async def api_get_user_history(request: UserHistoryRequest):
    """REST API endpoint for getting user history."""
    try:
        logger.info(f"API history request for user {request.user_id}")

        # Get history from database
        history = await server_app.db_manager.get_user_history(
            request.user_id, limit=request.limit
        )

        return {"history": history, "total_count": len(history)}

    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint dla komunikacji z klientami."""
    logger.info(f"WebSocket connection attempt for user: {user_id}")

    try:
        await server_app.connection_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connected for user: {user_id}")

        # Wait for version handshake as first message
        try:
            first_data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)

            # Validate JSON structure using pydantic
            try:
                first_request = WebSocketRequest.model_validate(json.loads(first_data))
            except Exception as validation_error:
                logger.error(
                    f"Invalid request format from user {user_id}: {validation_error}"
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "success": False,
                            "error": f"Invalid request format: {str(validation_error)}",
                        }
                    )
                )
                await websocket.close()
                return

            # Check if this is a version handshake
            if first_request.type == RequestType.HANDSHAKE:
                client_version = first_request.version or "unknown"
                server_version = "1.0.0"  # TODO: Get from config

                if client_version != server_version:
                    logger.warning(
                        f"Version mismatch: client={client_version}, server={server_version}"
                    )
                    response = WebSocketResponse(
                        type="handshake_response",
                        success=False,
                        error="Version mismatch",
                        server_version=server_version,
                    )
                    await websocket.send_text(response.model_dump_json())
                    await websocket.close()
                    return

                # Send successful handshake response
                response = WebSocketResponse(
                    type="handshake_response",
                    success=True,
                    server_version=server_version,
                )
                await websocket.send_text(response.model_dump_json())
            else:
                # If no handshake, process as regular message but log warning
                logger.warning(f"No version handshake received from client {user_id}")
                # Process the message as normal
                response = await server_app.process_validated_request(
                    user_id, first_request
                )
                await server_app.connection_manager.send_personal_message(
                    response, user_id
                )

        except TimeoutError:
            logger.error(f"Handshake timeout for user {user_id}")
            await websocket.close()
            return
        except json.JSONDecodeError:
            logger.error(f"Invalid handshake JSON from user {user_id}")
            await websocket.close()
            return

    except Exception as e:
        logger.error(f"Failed to connect WebSocket for user {user_id}: {e}")
        return

    try:
        while True:
            # Odbierz wiadomość od klienta
            data = await websocket.receive_text()

            try:
                # Validate using pydantic
                request_data = WebSocketRequest.model_validate(json.loads(data))

                # Przetwórz request
                response = await server_app.process_validated_request(
                    user_id, request_data
                )

                # Wyślij odpowiedź
                await server_app.connection_manager.send_personal_message(
                    response, user_id
                )

            except Exception as validation_error:
                logger.error(
                    f"Request validation/processing error for user {user_id}: {validation_error}"
                )
                error_response = WebSocketResponse(
                    type="error",
                    success=False,
                    error=f"Request error: {str(validation_error)}",
                )
                await server_app.connection_manager.send_personal_message(
                    error_response.model_dump(), user_id
                )

    except WebSocketDisconnect:
        server_app.connection_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        server_app.connection_manager.disconnect(user_id)


@app.get("/webui")
async def webui():
    """Serwuj webui."""
    return FileResponse("webui.html", media_type="text/html")


@app.get("/api/status")
async def api_status():
    """Endpoint dla overlay - status serwera i aktywnych użytkowników."""
    try:
        active_users = list(server_app.connection_manager.active_connections.keys())
        user_status = {}

        for user_id in active_users:
            session = server_app.connection_manager.user_sessions.get(user_id, {})
            user_status[user_id] = {
                "is_listening": session.get("status") == "listening",
                "is_speaking": session.get("status") == "speaking",
                "is_processing": session.get("status") == "processing",
                "text": session.get("last_message", ""),
                "connected_at": session.get("connected_at", 0),
            }

        return {
            "server_status": "running",
            "active_users": len(active_users),
            "users": user_status,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger.error(f"Error getting API status: {e}")
        return {"error": str(e)}


def main():
    """Main server entry point."""
    run_server()


def run_server():
    """Uruchom serwer."""
    # Load configuration first to obtain logging settings
    config = load_config()

    log_level = config.get("logging", {}).get("level", "INFO").upper()

    # Konfiguracja logowania
    logger.remove()
    logger.add(
        "logs/server_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}:{function}:{line}</cyan> | {message}",
    )

    # Utwórz katalog logs jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)

    logger.info("Starting GAJA Assistant Server...")
    # Configure CORS middleware with security validation
    # Configure CORS middleware with security validation
    env_manager = EnvironmentManager()

    # Get CORS origins from environment variable first, then config, then defaults
    env_cors = os.getenv("ALLOWED_ORIGINS")
    if env_cors:
        cors_origins = [origin.strip() for origin in env_cors.split(",")]
    else:
        cors_origins = config.get("security", {}).get(
            "cors_origins", ["http://localhost:3000", "http://localhost:8080"]
        )

    # Sprawdź czy używamy niebezpiecznej konfiguracji
    if "*" in cors_origins:
        logger.warning(
            "CORS is configured to allow all origins (*). This is not recommended for production!"
        )
        if not config.get("server", {}).get("debug", False):
            logger.error(
                "Wildcard CORS is only allowed in debug mode! Using safe defaults."
            )
            cors_origins = ["http://localhost:3000", "http://localhost:8080"]

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    logger.info(f"CORS configured for origins: {cors_origins}")

    # Use environment manager to sanitize sensitive data in logs
    sanitized_config = env_manager.sanitize_config_for_logging(config)
    logger.info(f"Server starting with config: {sanitized_config}")

    # Use uvloop for improved performance if available
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.debug("uvloop enabled")
    except Exception:
        logger.debug("uvloop not available")

    # Uruchom serwer
    uvicorn.run(
        app,
        host=config.get("server", {}).get(
            "host", "localhost"
        ),  # Default to localhost for security
        port=config.get("server", {}).get("port", 8001),
        log_level=log_level.lower(),
        reload=False,  # W produkcji wyłącz reload
    )


if __name__ == "__main__":
    run_server()

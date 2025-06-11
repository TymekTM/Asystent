"""
GAJA Assistant Server
Główny serwer obsługujący wielu użytkowników, zarządzający AI, bazą danych i pluginami.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from loguru import logger

# Dodaj ścieżkę serwera do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))
# Dodaj ścieżkę modules do PYTHONPATH dla pluginów
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from config_loader import load_config
from database_manager import DatabaseManager, initialize_database_manager
from ai_module import AIModule
from function_calling_system import FunctionCallingSystem
from plugin_manager import plugin_manager
# Import onboarding from current server directory
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import onboarding_module as server_onboarding
OnboardingModule = server_onboarding.OnboardingModule
from plugin_monitor import plugin_monitor
from extended_webui import ExtendedWebUI


class ConnectionManager:
    """Zarządza połączeniami WebSocket z klientami."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Połącz nowego klienta."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_sessions[user_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "status": "connected"
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
    
    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
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
    
    def get_user_status(self, user_id: str) -> Dict[str, Any]:
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
        self.user_plugins: Dict[str, Dict[str, Any]] = {}
        
        # New modules
        self.onboarding_module = None
        self.plugin_monitor = plugin_monitor
        self.web_ui = None
        self.start_time = None
    
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
            logger.info("Plugin monitoring started")
            
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
                user_id = str(user.get('id'))
                enabled_plugins = user.get('enabled_plugins', [])
                
                for plugin_name in enabled_plugins:
                    try:
                        await plugin_manager.enable_plugin_for_user(user_id, plugin_name)
                        logger.info(f"Plugin {plugin_name} enabled for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to enable plugin {plugin_name} for user {user_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to load user plugins: {e}")
    
    def _configure_cors_middleware(self):
        """Konfiguruje CORS middleware z bezpiecznymi ustawieniami."""
        cors_origins = self.config.get('security', {}).get('cors_origins', ["http://localhost:3000", "http://localhost:8080"])
        
        # Sprawdź czy używamy niebezpiecznej konfiguracji
        if "*" in cors_origins:
            logger.warning("CORS is configured to allow all origins (*). This is not recommended for production!")
            if not self.config.get('server', {}).get('debug', False):
                logger.error("Wildcard CORS is only allowed in debug mode!")
                cors_origins = ["http://localhost:3000", "http://localhost:8080"]        
        # Import app z modułu globalnego - to może być problematyczne
        # Lepiej będzie to zrobić w main()
        logger.info(f"Configuring CORS for origins: {cors_origins}")
    
    async def load_plugin(self, plugin_name: str):
        """
        Dynamicznie załaduj plugin z walidacją bezpieczeństwa.
        
        Args:
            plugin_name: Nazwa pluginu (tylko alfanumeryczne znaki i podkreślenia)
        """
        try:
            # Walidacja nazwy pluginu - zapobieganie path traversal
            if not plugin_name.replace('_', '').replace('-', '').isalnum():
                logger.error(f"Invalid plugin name: {plugin_name}. Only alphanumeric characters, hyphens and underscores allowed.")
                return None
            
            # Dodatkowa walidacja - nie pozwalaj na ../  lub inne niebezpieczne znaki
            if '..' in plugin_name or '/' in plugin_name or '\\' in plugin_name or plugin_name.startswith('.'):
                logger.error(f"Plugin name contains prohibited characters: {plugin_name}")
                return None
            
            # Sprawdź długość nazwy (zapobieganie atakom)
            if len(plugin_name) > 50:
                logger.error(f"Plugin name too long: {plugin_name}")
                return None
            
            # Whitelist dozwolonych pluginów (jeśli skonfigurowane)
            allowed_plugins = self.config.get('plugins', {}).get('whitelist', [])
            if allowed_plugins and plugin_name not in allowed_plugins:
                logger.error(f"Plugin {plugin_name} not in whitelist: {allowed_plugins}")
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
            max_size = self.config.get('plugins', {}).get('max_file_size', 1024 * 1024)  # 1MB default
            if file_size > max_size:
                logger.error(f"Plugin file too large: {file_size} bytes (max {max_size})")
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
            if hasattr(signal, 'SIGALRM'):
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
                required_functions = ['execute_function', 'get_functions']
                missing_functions = [func for func in required_functions if not hasattr(module, func)]
                
                if missing_functions:
                    logger.warning(f"Plugin {plugin_name} missing required functions: {missing_functions}")
                    return None
                
                # Sprawdź czy plugin ma opcjonalne metadane bezpieczeństwa
                if hasattr(module, 'PLUGIN_METADATA'):
                    metadata = module.PLUGIN_METADATA
                    if 'permissions' in metadata:
                        logger.info(f"Plugin {plugin_name} requires permissions: {metadata['permissions']}")
                    if 'version' in metadata:
                        logger.info(f"Plugin {plugin_name} version: {metadata['version']}")
                
                logger.info(f"Successfully loaded plugin: {plugin_name}")
                return module
                
            finally:
                # Clear timeout
                if hasattr(signal, 'SIGALRM'):
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
            request_type = request_data.get('type')
            
            if request_type == 'ai_query':
                return await self.handle_ai_query(user_id, request_data)
            elif request_type == 'function_call':
                return await self.handle_function_call(user_id, request_data)
            elif request_type == 'plugin_toggle':
                return await self.handle_plugin_toggle(user_id, request_data)
            elif request_type == 'plugin_list':
                return await self.handle_plugin_list(user_id)
            elif request_type == 'status_update':
                return await self.handle_status_update(user_id, request_data)
            else:
                return {
                    'type': 'error',
                    'message': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            logger.error(f"Error processing request for user {user_id}: {e}")
            return {
                'type': 'error',
                'message': f'Request processing failed: {str(e)}'
            }
    
    async def handle_ai_query(self, user_id: str, request_data: dict):
        """Obsłuż zapytanie AI."""
        try:
            query = request_data.get('query', '')
            context = request_data.get('context', {})
            
            # Pobierz historię użytkownika z bazy
            user_history = await self.db_manager.get_user_history(user_id)            # Przygotuj kontekst dla AI
            available_plugins = list(plugin_manager.get_available_functions(user_id).keys())
            modules = plugin_manager.get_modules_for_user(user_id)
            
            logger.info(f"DEBUG: available_plugins = {available_plugins}")
            logger.info(f"DEBUG: modules keys = {list(modules.keys()) if modules else 'None'}")
            logger.info(f"DEBUG: modules = {modules}")
            
            ai_context = {
                'user_id': user_id,
                'history': user_history,
                'available_plugins': available_plugins,
                'modules': modules,
                'user_name': context.get('user_name', 'User'),
                **context
            }
            
            logger.info(f"Processing AI query for user {user_id}: FULL_QUERY=[{query}]")
            logger.info(f"Request data received: {request_data}")
            logger.info(f"Context received: {context}")
            
            # Przetwórz zapytanie przez AI
            response = await self.ai_module.process_query(query, ai_context)
            
            logger.info(f"AI response received: {response[:100]}...")
            
            # Zapisz interakcję w bazie
            await self.db_manager.save_interaction(user_id, query, response)
            
            return {
                'type': 'ai_response',
                'response': response,
                'timestamp': asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"AI query error for user {user_id}: {e}")
            return {
                'type': 'error',
                'message': f'AI query failed: {str(e)}'
            }
    
    async def handle_function_call(self, user_id: str, request_data: dict):
        """Obsłuż wywołanie funkcji pluginu."""
        try:
            plugin_name = request_data.get('plugin')
            function_name = request_data.get('function')
            parameters = request_data.get('parameters', {})
            
            if not plugin_name or not function_name:
                return {
                    'type': 'error',
                    'message': 'Missing plugin or function name'
                }
            
            # Sprawdź czy plugin jest włączony dla użytkownika
            user_plugins = plugin_manager.get_user_plugins(user_id)
            if not user_plugins.get(plugin_name, False):
                return {
                    'type': 'error',
                    'message': f'Plugin {plugin_name} is not enabled for user'
                }
            
            # Załaduj plugin jeśli nie jest załadowany
            if not plugin_manager.is_plugin_loaded(plugin_name):
                await plugin_manager.load_plugin(plugin_name)
            
            # Wywołaj funkcję pluginu
            plugin_module = await self.load_plugin_module(plugin_name)
            if not plugin_module:
                return {
                    'type': 'error',
                    'message': f'Failed to load plugin {plugin_name}'
                }
            
            # Wykonaj funkcję
            if hasattr(plugin_module, 'execute_function'):
                result = await plugin_module.execute_function(function_name, parameters, int(user_id))
                
                return {
                    'type': 'function_result',
                    'plugin': plugin_name,
                    'function': function_name,
                    'result': result
                }
            else:
                return {
                    'type': 'error',
                    'message': f'Plugin {plugin_name} does not support function execution'
                }
                
        except Exception as e:
            logger.error(f"Function call error: {e}")
            return {
                'type': 'error',
                'message': f'Function call failed: {str(e)}'
            }
    
    async def handle_plugin_toggle(self, user_id: str, request_data: dict):
        """Obsłuż włączanie/wyłączanie pluginu."""
        try:
            plugin_name = request_data.get('plugin')
            action = request_data.get('action', 'toggle')  # enable, disable, toggle
            
            if not plugin_name:
                return {
                    'type': 'error',
                    'message': 'Plugin name required'
                }
            
            logger.info(f"Plugin {action} request from user {user_id}: {plugin_name}")
            
            if action == 'enable':
                success = await plugin_manager.enable_plugin_for_user(user_id, plugin_name)
                status = 'enabled' if success else 'failed'
            elif action == 'disable':
                success = await plugin_manager.disable_plugin_for_user(user_id, plugin_name)
                status = 'disabled' if success else 'failed'
            elif action == 'toggle':
                # Sprawdź aktualny status i przełącz
                user_plugins = plugin_manager.get_user_plugins(user_id)
                is_enabled = user_plugins.get(plugin_name, False)
                
                if is_enabled:
                    success = await plugin_manager.disable_plugin_for_user(user_id, plugin_name)
                    status = 'disabled' if success else 'failed'
                else:
                    success = await plugin_manager.enable_plugin_for_user(user_id, plugin_name)
                    status = 'enabled' if success else 'failed'
            else:
                return {
                    'type': 'error',
                    'message': f'Unknown action: {action}'
                }
            
            if success:
                # Aktualizuj bazę danych jeśli to konieczne
                await self.db_manager.update_user_plugin_status(user_id, plugin_name, status == 'enabled')
                
                return {
                    'type': 'plugin_toggled',
                    'plugin': plugin_name,
                    'status': status,
                    'success': True
                }
            else:
                return {
                    'type': 'error',
                    'message': f'Failed to {action} plugin {plugin_name}'
                }
                
        except Exception as e:
            logger.error(f"Plugin toggle error: {e}")
            return {
                'type': 'error',
                'message': f'Plugin toggle failed: {str(e)}'
            }
    
    async def handle_plugin_list(self, user_id: str):
        """Zwróć listę dostępnych pluginów i ich status."""
        try:
            all_plugins = plugin_manager.get_all_plugins()
            user_plugins = plugin_manager.get_user_plugins(user_id)
            
            plugin_list = []
            for plugin_name, plugin_info in all_plugins.items():
                plugin_list.append({
                    'name': plugin_name,
                    'description': plugin_info.description,
                    'version': plugin_info.version,
                    'author': plugin_info.author,
                    'functions': plugin_info.functions,
                    'enabled': user_plugins.get(plugin_name, False),
                    'loaded': plugin_info.loaded
                })
            
            return {
                'type': 'plugin_list',
                'plugins': plugin_list
            }
            
        except Exception as e:
            logger.error(f"Plugin list error: {e}")
            return {
                'type': 'error',
                'message': f'Failed to get plugin list: {str(e)}'
            }
    
    async def handle_status_update(self, user_id: str, request_data: dict):
        """Obsłuż aktualizację statusu użytkownika."""
        try:
            status = request_data.get('status', 'unknown')
            message = request_data.get('message', '')
            
            # Aktualizuj status w connection manager
            self.connection_manager.update_user_status(user_id, status, message)
            
            return {
                'type': 'status_updated',
                'status': status,
                'message': 'Status updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error updating status for user {user_id}: {e}")
            return {
                'type': 'error',
                'message': f'Status update failed: {str(e)}'
            }
    
    def _configure_cors_middleware(self):
        """Konfiguruje CORS middleware z bezpiecznymi ustawieniami."""
        cors_origins = self.config.get('security', {}).get('cors_origins', ["http://localhost:3000", "http://localhost:8080"])
        
        # Sprawdź czy używamy niebezpiecznej konfiguracji
        if "*" in cors_origins:
            logger.warning("CORS is configured to allow all origins (*). This is not recommended for production!")
            if not self.config.get('server', {}).get('debug', False):
                logger.error("Wildcard CORS is only allowed in debug mode!")
                cors_origins = ["http://localhost:3000", "http://localhost:8080"]
        
        # Import app z modułu globalnego - to może być problematyczne
        # Lepiej będzie to zrobić w main()
        logger.info(f"Configuring CORS for origins: {cors_origins}")
    
    # ...existing code...

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
    lifespan=lifespan
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
        "loaded_users": len(server_app.user_plugins)
    }


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint dla komunikacji z klientami."""
    logger.info(f"WebSocket connection attempt for user: {user_id}")
    
    try:
        await server_app.connection_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connected for user: {user_id}")
    except Exception as e:
        logger.error(f"Failed to connect WebSocket for user {user_id}: {e}")
        return
    
    try:
        while True:
            # Odbierz wiadomość od klienta
            data = await websocket.receive_text()
            
            try:
                request_data = json.loads(data)
                
                # Przetwórz request
                response = await server_app.process_user_request(user_id, request_data)
                
                # Wyślij odpowiedź
                await server_app.connection_manager.send_personal_message(response, user_id)
                
            except json.JSONDecodeError:
                error_response = {
                    'type': 'error',
                    'message': 'Invalid JSON format'
                }
                await server_app.connection_manager.send_personal_message(error_response, user_id)
                
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
                "connected_at": session.get("connected_at", 0)
            }
        
        return {
            "server_status": "running",
            "active_users": len(active_users),
            "users": user_status,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Error getting API status: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    """Uruchom serwer."""
    # Konfiguracja logowania
    logger.remove()
    logger.add(
        "logs/server_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}:{function}:{line}</cyan> | {message}"
    )
    
    # Utwórz katalog logs jeśli nie istnieje    os.makedirs("logs", exist_ok=True)
    
    logger.info("Starting GAJA Assistant Server...")    
    # Load configuration
    config = load_config()
      # Configure CORS middleware with security validation
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from environment_manager import EnvironmentManager
    env_manager = EnvironmentManager()
    cors_origins = config.get('security', {}).get('cors_origins', ["http://localhost:3000", "http://localhost:8080"])
    
    # Sprawdź czy używamy niebezpiecznej konfiguracji
    if "*" in cors_origins:
        logger.warning("CORS is configured to allow all origins (*). This is not recommended for production!")
        if not config.get('server', {}).get('debug', False):
            logger.error("Wildcard CORS is only allowed in debug mode! Using safe defaults.")
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
    
    # Sanitize and log server config
    server_config = config.get('server', {})
    host = server_config.get('host', 'localhost')
    port = server_config.get('port', 8001)
    
    # Use environment manager to sanitize sensitive data in logs
    sanitized_config = env_manager.sanitize_config_for_logging(config)
    logger.info(f"Server starting with config: {sanitized_config}")
      # Uruchom serwer
    uvicorn.run(
        app,
        host=config.get('server', {}).get('host', 'localhost'),  # Default to localhost for security
        port=config.get('server', {}).get('port', 8001),
        log_level="info",
        reload=False  # W produkcji wyłącz reload
    )

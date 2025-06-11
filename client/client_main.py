"""
GAJA Assistant Client
Klient obsługujący lokalne komponenty (wakeword, overlay, Whisper ASR) 
i komunikujący się z serwerem przez WebSocket.
"""

import asyncio
import json
import logging
import os
import sys
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Any
import websockets
from loguru import logger
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import time
import queue
from active_window_module import get_active_window_title

# Dodaj ścieżkę główną projektu do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Import local modules
from audio_modules.advanced_wakeword_detector import create_wakeword_detector
from audio_modules.whisper_asr import create_whisper_asr, create_audio_recorder

# Import enhanced modules if available, fallback to legacy
try:
    from audio_modules.enhanced_tts_module import EnhancedTTSModule as TTSModule
    logger.info("Using Enhanced TTS Module")
except ImportError:
    from audio_modules.tts_module import TTSModule
    logger.info("Using Legacy TTS Module")

try:
    from audio_modules.enhanced_whisper_asr import EnhancedWhisperASR as WhisperASR
    logger.info("Using Enhanced Whisper ASR")
except ImportError:
    from audio_modules.whisper_asr import create_whisper_asr
    WhisperASR = None
    logger.info("Using Legacy Whisper ASR")

# Import user mode system if available
try:
    from mode_integrator import user_integrator
    USER_MODE_AVAILABLE = True
    logger.info("User Mode System available")
except ImportError:
    USER_MODE_AVAILABLE = False
    logger.info("User Mode System not available - using legacy mode")


class ClientApp:
    """Główna klasa klienta GAJA."""
    
    def __init__(self):
        self.config = self.load_client_config()
        self.websocket = None
        self.user_id = self.config.get('user_id', '1')
        self.server_url = self.config.get('server_url', 'ws://localhost:8001/ws/client1')
        self.running = False
        
        # Audio components
        self.wakeword_detector = None
        self.whisper_asr = None
        self.audio_recorder = None
        self.tts = None
        self.overlay_process = None  # External Tauri overlay process
          # State management
        self.monitoring_wakeword = False    # Whether wakeword monitoring is active
        self.wake_word_detected = False     # Whether wakeword was just detected
        self.recording_command = False
        self.tts_playing = False
        self.last_tts_text = ""
        self.current_status = "Starting..."
          # HTTP server for overlay
        self.http_server = None
        self.http_thread = None
        self.command_queue = queue.Queue()  # Queue for HTTP commands
        # Update overlay status data for showing/hiding
        self.overlay_visible = False
        self.sse_clients = []
    
    def load_client_config(self) -> Dict:
        """Załaduj konfigurację klienta."""
        # Config file should be in the same directory as this script
        config_path = Path(__file__).parent / "client_config.json"
        
        logger.info(f"🔧 Looking for config at: {config_path.absolute()}")
        
        if config_path.exists():
            logger.info("📁 Config file found, loading...")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"✅ Config loaded: server_url={config.get('server_url')}")
                return config
        
        logger.warning("⚠️ Config file not found, using defaults")
        # Default config
        return {
            "server_url": "ws://localhost:8001/ws/client1",
            "user_id": "1",
            "wakeword": {
                "enabled": True,
                "keyword": "gaja",
                "sensitivity": 0.6,
                "device_id": None,
                "stt_silence_threshold_ms": 2000
            },
            "whisper": {
                "model": "base",
                "language": "pl"
            },
            "overlay": {
                "enabled": True,
                "position": "top-right",
                "auto_hide_delay": 10
            },            "audio": {
                "sample_rate": 16000,
                "record_duration": 5.0
            }
        }

    async def initialize_components(self):
        """Inicjalizuj komponenty audio i overlay."""
        try:
            # Start HTTP server for overlay first
            self.start_http_server()
            self.update_status("Initializing...")
            
            # Initialize external Tauri overlay only
            if self.config.get('overlay', {}).get('enabled', True):
                await self.start_overlay()
            
            # Initialize wakeword detector
            wakeword_config = self.config.get('wakeword', {})
            if wakeword_config.get('enabled', True):
                self.wakeword_detector = create_wakeword_detector(
                    config=wakeword_config,
                    callback=self.on_wakeword_detected
                )
                logger.info("Wakeword detector initialized")
                
            # Initialize Whisper ASR - Enhanced or Legacy
            whisper_config = self.config.get('whisper', {})
            if WhisperASR and USER_MODE_AVAILABLE:
                # Use Enhanced Whisper ASR with User Mode support
                self.whisper_asr = WhisperASR()
                logger.info("Enhanced Whisper ASR initialized")
            else:
                # Use Legacy Whisper ASR
                self.whisper_asr = create_whisper_asr(whisper_config)
                logger.info("Legacy Whisper ASR initialized")
                
            # Always create audio recorder for wakeword detection
            self.audio_recorder = create_audio_recorder(
                sample_rate=self.config.get('audio', {}).get('sample_rate', 16000),
                duration=self.config.get('audio', {}).get('record_duration', 5.0)
            )
            
            # Initialize TTS - Enhanced or Legacy
            if USER_MODE_AVAILABLE:
                # Enhanced TTS will be managed by user_integrator
                self.tts = user_integrator.tts_module
                logger.info("Enhanced TTS module initialized via User Mode Integrator")
            else:
                # Use Legacy TTS
                self.tts = TTSModule()
                logger.info("Legacy TTS module initialized")
            
            # Set whisper ASR for wakeword detector
            if self.wakeword_detector:
                self.wakeword_detector.set_whisper_asr(self.whisper_asr)
                logger.info("Whisper ASR set for wakeword detector")
            
            logger.info("All client components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise

    async def start_overlay(self):
        """Uruchom zewnętrzny overlay Tauri."""
        try:
            overlay_path = Path(__file__).parent / "overlay" / "target" / "release" / "gaja-overlay.exe"
            
            if overlay_path.exists():
                self.overlay_process = subprocess.Popen(
                    [str(overlay_path)],
                    cwd=overlay_path.parent.parent
                )
                logger.info(f"Started Tauri overlay process: {self.overlay_process.pid}")
            else:
                logger.warning(f"Overlay executable not found: {overlay_path}")
                
        except Exception as e:            logger.error(f"Error starting overlay: {e}")

    async def connect_to_server(self):
        """Nawiąż połączenie z serwerem."""
        try:
            logger.info(f"Attempting to connect to: {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            logger.info(f"Connected to server: {self.server_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            logger.error(f"Server URL was: {self.server_url}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def send_message(self, message: Dict):
        """Wyślij wiadomość do serwera."""
        if self.websocket:
            try:
                logger.info(f"Sending message to server: {message}")
                await self.websocket.send(json.dumps(message))
                logger.debug(f"Sent message: {message['type']}")
            except Exception as e:
                logger.error(f"Error sending message: {e}")

    async def listen_for_messages(self):
        """Nasłuchuj wiadomości od serwera."""
        try:
            while self.running:
                if self.websocket:
                    try:
                        message = await self.websocket.recv()
                        data = json.loads(message)
                        await self.handle_server_message(data)
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("Connection to server lost")
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON from server: {e}")
                else:
                    await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")

    async def handle_server_message(self, data: Dict):
        """Obsłuż wiadomość od serwera."""
        message_type = data.get('type')
        
        if message_type == 'ai_response':
            response = data.get('response', '')
            logger.info(f"AI Response received: {response}")
            
            # Response is already a JSON string from the server
            try:
                if isinstance(response, str):
                    response_data = json.loads(response)
                else:
                    response_data = response
                
                text = response_data.get('text', '')
                if text:
                    logger.info(f"AI text response: {text}")
                    
                    # Update overlay with AI response
                    self.last_tts_text = text
                    self.update_status(f"Response: {text[:50]}...")                    # Play TTS response
                    if self.tts:
                        try:
                            self.tts_playing = True
                            self.update_status("Speaking...")
                            await self.tts.speak(text)
                            logger.info("TTS response played")
                        except Exception as tts_e:
                            logger.error(f"TTS error: {tts_e}")
                        finally:
                            self.tts_playing = False
                            self.wake_word_detected = False  # Reset wakeword flag after speaking
                            self.recording_command = False  # Reset recording flag
                            # Hide overlay after speaking
                            await self.hide_overlay()
                            self.update_status("Listening...")  # Return to listening immediately
                    else:
                        logger.warning("TTS not available")
                        self.wake_word_detected = False
                        self.update_status("Listening...")  # Return to listening even without TTS
                else:
                    logger.warning("No text in AI response")
                        
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing AI response: {e}")
                # Fallback: treat response as plain text
                if isinstance(response, str) and response.strip():
                    text = response.strip()
                    logger.info(f"Using response as plain text: {text}")
                      # Update overlay
                    self.last_tts_text = text
                    self.update_status(f"Response: {text[:50]}...")
                    
                    # Play TTS
                    if self.tts:
                        try:
                            self.tts_playing = True
                            self.update_status("Speaking...")
                            await self.tts.speak(text)
                            logger.info("TTS response played (plain text)")
                        except Exception as tts_e:
                            logger.error(f"TTS error: {tts_e}")
                        finally:
                            self.tts_playing = False
                            self.wake_word_detected = False  # Reset wakeword flag after speaking (fallback)
                            self.recording_command = False  # Reset recording flag
                            # Hide overlay after speaking
                            await self.hide_overlay()
                            self.update_status("Listening...")  # Return to listening immediately
                    else:
                        logger.warning("TTS not available")
                        self.wake_word_detected = False
                        self.update_status("Listening...")  # Return to listening even without TTS
            
        elif message_type == 'function_result':
            function_name = data.get('function')
            result = data.get('result')
            logger.info(f"Function {function_name} result: {result}")
            
        elif message_type == 'plugin_toggled':
            plugin = data.get('plugin')
            status = data.get('status')
            logger.info(f"Plugin {plugin} {status}")
            
        elif message_type == 'plugin_status_updated':
            plugins = data.get('plugins', {})
            logger.info(f"Plugin status update: {plugins}")
            
        elif message_type == 'error':
            error = data.get('error', 'Unknown error')
            logger.error(f"Server error: {error}")
            self.update_status("Error")
            
        else:
            logger.warning(f"Unknown message type: {message_type}")

    async def on_wakeword_detected(self, query: str = None):
        """Callback wywoływany po wykryciu słowa aktywującego i transkrypcji."""
        if query:
            # We already have transcribed text from wakeword detector
            logger.info(f"Wakeword detected with query: {query}")
              # Set wake word detection flag for overlay
            self.wake_word_detected = True
            self.update_status("Wake word detected!")
            
            if self.recording_command:
                logger.warning("Already processing command")
                return
                
            try:
                self.recording_command = True
                self.update_status("Processing...")
                
                # Show overlay when processing starts
                await self.show_overlay()
                
                # Send transcribed query to server
                active_title = get_active_window_title()
                message = {
                    "type": "ai_query",
                    "query": query,
                    "context": {
                        "source": "voice",
                        "user_name": "Voice User",
                        "active_window_title": active_title,
                        "track_active_window_setting": True
                    }
                }
                
                await self.send_message(message)
                
            except Exception as e:
                logger.error(f"Error processing voice command: {e}")
                self.update_status("Error")
                # Reset flags on error
                self.wake_word_detected = False
                self.recording_command = False
                # Return to listening state
                await asyncio.sleep(1)
                self.update_status("Listening...")
            finally:
                # Note: recording_command and wake_word_detected are reset in TTS completion
                pass
        else:
            # Legacy support - wakeword detected without transcription
            logger.info("Wakeword detected! Recording and transcription handled by wakeword detector.")
            self.wake_word_detected = True
            self.update_status("Listening...")

    async def show_overlay(self):
        """Pokaż overlay."""
        try:
            # Set overlay visible flag and update status to something overlay might recognize
            self.overlay_visible = True
            self.update_status("Processing...")  # Use original status
            logger.info("Overlay shown - status updated to Processing...")
        except Exception as e:
            logger.error(f"Error showing overlay: {e}")

    async def hide_overlay(self):
        """Ukryj overlay."""
        try:
            # Set overlay hidden flag and update status  
            self.overlay_visible = False
            self.update_status("Listening...")
            logger.info("Overlay hidden - status updated to Listening...")
        except Exception as e:
            logger.error(f"Error hiding overlay: {e}")

    async def update_overlay_status(self, status: str):
        """Zaktualizuj status w overlay."""
        logger.debug(f"Overlay status: {status}")
        # Overlay is external process - status updates would need IPC

    def get_current_status(self) -> str:
        """Zwróć aktualny status klienta."""
        return self.current_status
    
    def update_status(self, status: str):
        """Zaktualizuj status i powiadom overlay."""
        self.current_status = status
        self.notify_sse_clients()
    
    def add_sse_client(self, client):
        """Dodaj klienta SSE."""
        self.sse_clients.append(client)
        
    def remove_sse_client(self, client):
        """Usuń klienta SSE."""
        if client in self.sse_clients:
            self.sse_clients.remove(client)
    
    def notify_sse_clients(self):
        """Powiadom wszystkich klientów SSE o zmianie statusu."""
        status_data = {
            "status": self.current_status,
            "text": self.last_tts_text,
            "is_listening": self.recording_command,
            "is_speaking": self.tts_playing,
            "wake_word_detected": self.wake_word_detected
        }
        
        message = f"data: {json.dumps(status_data)}\n\n"
        
        # Send to all connected SSE clients
        for client in self.sse_clients[:]:  # Copy list to avoid modification during iteration
            try:
                client.wfile.write(message.encode())
                client.wfile.flush()
            except Exception as e:
                logger.debug(f"SSE client disconnected: {e}")
                self.remove_sse_client(client)
    
    def start_http_server(self):
        """Uruchom HTTP serwer dla overlay."""
        try:
            # Try port 5001 first (debug), then 5000 (release)
            ports = [5001, 5000]
            
            for port in ports:
                try:
                    # Create handler with reference to client app
                    handler = lambda *args, **kwargs: StatusHTTPHandler(self, *args, **kwargs)
                    self.http_server = HTTPServer(('localhost', port), handler)
                    
                    # Start server in separate thread
                    self.http_thread = threading.Thread(
                        target=self.http_server.serve_forever,
                        daemon=True
                    )
                    self.http_thread.start()
                    
                    logger.info(f"HTTP server started on port {port} for overlay")
                    break
                    
                except OSError as e:
                    logger.warning(f"Port {port} unavailable: {e}")
                    continue
            else:
                logger.error("Could not start HTTP server on any port")
                
        except Exception as e:
            logger.error(f"Error starting HTTP server: {e}")
    
    def stop_http_server(self):
        """Zatrzymaj HTTP serwer."""
        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
                logger.info("HTTP server stopped")
            except Exception as e:
                logger.error(f"Error stopping HTTP server: {e}")

    async def run(self):
        """Uruchom główną pętlę klienta."""
        try:
            self.running = True
            
            # Initialize components (includes HTTP server)
            await self.initialize_components()
            
            # Try to connect to server (but don't fail if can't connect)
            try:
                await self.connect_to_server()
                logger.info("Connected to server successfully")
            except Exception as e:
                logger.warning(f"Could not connect to server: {e}")
                logger.warning("Running in standalone mode - overlay and local features will work")
            
            # Start wakeword monitoring
            await self.start_wakeword_monitoring()
            
            # Set status to ready
            self.update_status("Listening...")
              # Listen for server messages (or just keep running if no server)
            if self.websocket:
                # Start command queue processor alongside websocket listener
                await asyncio.gather(
                    self.listen_for_messages(),
                    self.process_command_queue()
                )
            else:
                # Standalone mode - just keep running with wakeword detection
                logger.info("Running in standalone mode - use Ctrl+C to stop")
                await self.process_command_queue()  # Just process commands
            
        except KeyboardInterrupt:
            logger.info("Client interrupted by user")
        except Exception as e:
            logger.error(f"Error in client main loop: {e}")
        finally:
            await self.cleanup()

    async def process_command_queue(self):
        """Process commands from HTTP requests in the main async loop."""
        while self.running:
            try:
                # Check for commands from HTTP handlers
                while not self.command_queue.empty():
                    command = self.command_queue.get_nowait()
                    try:
                        await self.execute_command(command)
                    except Exception as e:
                        logger.error(f"Error executing command {command}: {e}")
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
            except Exception as e:
                logger.error(f"Error in command queue processor: {e}")
                await asyncio.sleep(1)

    async def execute_command(self, command: Dict):
        """Execute a command from the HTTP interface."""
        command_type = command.get('type')
        
        if command_type == 'show_overlay':
            await self.show_overlay()
        elif command_type == 'hide_overlay':
            await self.hide_overlay()
        elif command_type == 'test_wakeword':
            query = command.get('query', 'Powiedz mi coś o sobie.')
            await self.on_wakeword_detected(query)
        else:
            logger.warning(f"Unknown command type: {command_type}")

    async def start_wakeword_monitoring(self):
        """Uruchom monitoring słowa aktywującego w tle."""
        if self.wakeword_detector:
            self.monitoring_wakeword = True
            # Start wakeword detection in separate thread
            wakeword_thread = threading.Thread(target=self.wakeword_detector.start_detection, daemon=True)
            wakeword_thread.start()
            logger.info("Wakeword monitoring started")

    async def cleanup(self):
        """Wyczyść zasoby przed zamknięciem."""
        try:
            self.running = False
            
            # Stop HTTP server
            self.stop_http_server()
            
            # Stop wakeword detection
            if self.wakeword_detector:
                self.wakeword_detector.stop_detection()
                
            # Close overlay process with improved termination
            if self.overlay_process and self.overlay_process.poll() is None:
                logger.info(f"Terminating overlay process (PID: {self.overlay_process.pid})...")
                
                try:
                    # Try graceful termination first
                    self.overlay_process.terminate()
                    self.overlay_process.wait(timeout=3)
                    logger.info("Overlay process terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("Overlay process didn't terminate gracefully, trying forceful kill...")
                    try:
                        self.overlay_process.kill()
                        self.overlay_process.wait(timeout=2)
                        logger.info("Overlay process killed forcefully")
                    except subprocess.TimeoutExpired:
                        logger.error("Failed to kill overlay process - it may remain in memory")
                          # Last resort: try Windows taskkill
                        try:
                            import subprocess
                            result = subprocess.run(
                                ["taskkill", "/PID", str(self.overlay_process.pid), "/F"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.returncode == 0:
                                logger.info("Successfully killed process with taskkill")
                            else:
                                logger.warning(f"Taskkill returned non-zero exit code: {result.returncode}")
                        except subprocess.TimeoutExpired:
                            logger.error("Taskkill command timed out")
                        except Exception as taskkill_e:
                            logger.error(f"Taskkill failed: {taskkill_e}")
                            
                except Exception as term_e:
                    logger.error(f"Error terminating overlay process: {term_e}")
                
            # Close WebSocket connection
            if self.websocket:
                await self.websocket.close()
                logger.info("WebSocket connection closed")
                
            logger.info("Client cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

class StatusHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler dla overlay status API."""
    
    def __init__(self, client_app, *args, **kwargs):
        self.client_app = client_app
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Obsługa GET requests."""
        try:
            path = urlparse(self.path).path
            
            if path == '/api/status':
                # Zwróć aktualny status
                status_data = {
                    "status": self.client_app.get_current_status(),
                    "text": self.client_app.last_tts_text,
                    "is_listening": self.client_app.recording_command,
                    "is_speaking": self.client_app.tts_playing if hasattr(self.client_app, 'tts_playing') else False,
                    "wake_word_detected": self.client_app.wake_word_detected,
                    "overlay_visible": getattr(self.client_app, 'overlay_visible', False),
                    "show_overlay": getattr(self.client_app, 'overlay_visible', False)  # Explicit overlay show flag
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(status_data).encode())
                
            elif path == '/api/overlay/show':                # Pokaż overlay
                self.client_app.command_queue.put({'type': 'show_overlay'})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "shown"}).encode())                
            elif path == '/api/overlay/hide':
                # Ukryj overlay
                self.client_app.command_queue.put({'type': 'hide_overlay'})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "hidden"}).encode())
                
            elif path == '/api/overlay/status':
                # Status overlay
                status_data = {
                    "overlay_visible": self.client_app.overlay_visible,
                    "is_listening": getattr(self.client_app, 'is_listening', False),
                    "is_speaking": getattr(self.client_app, 'is_speaking', False),
                    "current_text": getattr(self.client_app, 'current_text', ''),
                    "status": "active"
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(status_data).encode())
                
            elif path == '/api/test/wakeword':
                # Test endpoint for manual wakeword trigger
                query_params = parse_qs(urlparse(self.path).query)
                test_query = query_params.get('query', ['Powiedz mi coś o sobie.'])[0]
                
                if self.client_app.wakeword_detector:
                    # Put wakeword test in command queue to be processed by main thread
                    self.client_app.command_queue.put({'type': 'test_wakeword', 'query': test_query})
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "triggered", "query": test_query}).encode())
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Wakeword detector not available"}).encode())
                
            elif path == '/status/stream':
                # SSE endpoint for real-time updates
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                # Keep connection alive and send updates
                self.client_app.add_sse_client(self)
                
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            logger.error(f"HTTP handler error: {e}")
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Log HTTP requests for debugging."""
        logger.debug(f"HTTP: {format % args}")


async def main():
    """Funkcja główna."""
    # Setup logging
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.info("Starting GAJA Assistant Client...")
    
    client = ClientApp()
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())

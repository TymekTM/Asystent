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
from active_window_module import get_active_window_title

# Dodaj ścieżkę klienta do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

# Import local modules
from audio_modules.advanced_wakeword_detector import create_wakeword_detector
from audio_modules.whisper_asr import create_whisper_asr, create_audio_recorder
from audio_modules.tts_module import TTSModule


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
        self.overlay_process = None  # External Tauri overlay process# State management
        self.listening_for_wakeword = False
        self.recording_command = False
    
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
            },
            "audio": {
                "sample_rate": 16000,
                "record_duration": 5.0
            }
        }
    
    async def initialize_components(self):
        """Inicjalizuj komponenty audio i overlay."""
        try:
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
                
            # Initialize Whisper ASR
            whisper_config = self.config.get('whisper', {})
            self.whisper_asr = create_whisper_asr(whisper_config)
            self.audio_recorder = create_audio_recorder(
                sample_rate=self.config.get('audio', {}).get('sample_rate', 16000),
                duration=self.config.get('audio', {}).get('record_duration', 5.0)            )
            logger.info("Whisper ASR initialized")
            
            # Initialize TTS
            self.tts = TTSModule()
            logger.info("TTS module initialized")
            
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
        except Exception as e:            logger.error(f"Error listening for messages: {e}")

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
                    await self.update_overlay_status(f"Response: {text[:50]}...")
                      # Play TTS response
                    if self.tts:
                        try:
                            await self.tts.speak(text)
                            logger.info("TTS response played")
                        except Exception as tts_e:
                            logger.error(f"TTS error: {tts_e}")
                    else:
                        logger.warning("TTS not available")
                        
                    # Reset overlay status after a delay
                    await asyncio.sleep(3)
                    await self.update_overlay_status("Listening...")
                else:
                    logger.warning("No text in AI response")
                        
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing AI response: {e}")
                # Fallback: treat response as plain text
                if isinstance(response, str) and response.strip():
                    text = response.strip()
                    logger.info(f"Using response as plain text: {text}")
                    
                    # Update overlay
                    await self.update_overlay_status(f"Response: {text[:50]}...")
                      # Play TTS
                    if self.tts:
                        try:
                            await self.tts.speak(text)
                            logger.info("TTS response played (plain text)")
                        except Exception as tts_e:
                            logger.error(f"TTS error: {tts_e}")
                    
                    # Reset overlay status
                    await asyncio.sleep(3)
                    await self.update_overlay_status("Listening...")
            
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
            await self.update_overlay_status("Error")
            
        else:
            logger.warning(f"Unknown message type: {message_type}")

    async def on_wakeword_detected(self, query: str = None):
        """Callback wywoływany po wykryciu słowa aktywującego i transkrypcji."""
        if query:
            # We already have transcribed text from wakeword detector
            logger.info(f"Wakeword detected with query: {query}")
            
            if self.recording_command:
                logger.warning("Already processing command")
                return
                
            try:
                self.recording_command = True
                await self.update_overlay_status("Processing...")
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
                await self.update_overlay_status("Error")
            finally:                self.recording_command = False
        else:
            # Legacy support - wakeword detected without transcription
            logger.info("Wakeword detected! Recording and transcription handled by wakeword detector.")
            await self.update_overlay_status("Listening...")

    async def update_overlay_status(self, status: str):
        """Zaktualizuj status w overlay."""
        logger.debug(f"Overlay status: {status}")
        # Overlay is external process - status updates would need IPC

    async def run(self):
        """Uruchom główną pętlę klienta."""
        try:
            self.running = True
            
            # Initialize components
            await self.initialize_components()
            
            # Connect to server
            await self.connect_to_server()            # Start wakeword monitoring
            await self.start_wakeword_monitoring()
            
            # Listen for server messages
            await self.listen_for_messages()
            
        except KeyboardInterrupt:
            logger.info("Client interrupted by user")
        except Exception as e:
            logger.error(f"Error in client main loop: {e}")
        finally:
            await self.cleanup()

    async def start_wakeword_monitoring(self):
        """Uruchom monitoring słowa aktywującego w tle."""
        if self.wakeword_detector:
            self.listening_for_wakeword = True
            # Start wakeword detection in separate thread
            wakeword_thread = threading.Thread(target=self.wakeword_detector.start_detection, daemon=True)
            wakeword_thread.start()
            logger.info("Wakeword monitoring started")

    async def cleanup(self):
        """Wyczyść zasoby przed zamknięciem."""
        try:
            self.running = False
            
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
                            import os
                            os.system(f"taskkill /PID {self.overlay_process.pid} /F >nul 2>&1")
                            logger.info("Attempted taskkill as last resort")
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

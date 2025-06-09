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
import threading # Added import
import subprocess

# Dodaj ścieżkę klienta do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

# Import local modules
from audio_modules.wakeword_detector import create_wakeword_detector
from audio_modules.whisper_asr import create_whisper_asr, create_audio_recorder
from audio_modules.overlay import create_overlay


class ClientApp:
    """Główna klasa klienta GAJA."""
    
    def __init__(self):
        self.config = self.load_client_config()
        self.websocket = None
        self.user_id = self.config.get('user_id', '1')
        self.server_url = self.config.get('server_url', 'ws://localhost:8000')
        self.running = False        # Audio components
        self.wakeword_detector = None
        self.whisper_asr = None
        self.audio_recorder = None
        self.overlay_process = None  # External Tauri overlay process
        
        # State management
        self.listening_for_wakeword = False
        self.recording_command = False
    
    def load_client_config(self) -> Dict:
        """Załaduj konfigurację klienta."""
        config_path = Path("client_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading client config: {e}")
        
        # Domyślna konfiguracja
        return {
            "user_id": "1",
            "server_url": "ws://localhost:8000",
            "wakeword": {
                "enabled": True,
                "sensitivity": 0.6
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
            # Start external Tauri overlay
            if self.config.get('overlay', {}).get('enabled', True):
                await self.start_overlay()
            
            # Initialize wakeword detector
            if self.config.get('wakeword', {}).get('enabled', True):
                self.wakeword_detector = create_wakeword_detector(
                    self.config['wakeword'],
                    callback=self.on_wakeword_detected
                )
                logger.info("Wakeword detector initialized")
            
            # Initialize Whisper ASR
            self.whisper_asr = create_whisper_asr(self.config['whisper'])
            await self.whisper_asr.initialize()
            logger.info("Whisper ASR initialized")
            
            # Initialize audio recorder
            sample_rate = self.config.get('audio', {}).get('sample_rate', 16000)
            device_id = self.config.get('audio', {}).get('input_device')
            self.audio_recorder = create_audio_recorder(sample_rate, device_id)
            logger.info("Audio recorder initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    async def connect_to_server(self):
        """Połącz się z serwerem WebSocket."""
        try:
            uri = f"{self.server_url}/ws/{self.user_id}"
            logger.info(f"Connecting to server: {uri}")
            
            self.websocket = await websockets.connect(uri)
            logger.success("Connected to server")
            
            # Wyślij wiadomość testową
            test_message = {
                "type": "ai_query",
                "query": "Cześć! Jestem klientem GAJA.",
                "context": {
                    "client_version": "1.0.0",
                    "features": ["wakeword", "whisper", "overlay"]
                }
            }
            
            await self.send_message(test_message)
            
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            raise
    
    async def send_message(self, message: Dict):
        """Wyślij wiadomość do serwera."""
        if self.websocket:
            try:
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
            logger.info(f"AI Response: {response}")
            await self.update_overlay_status("Ready")
            
        elif message_type == 'function_result':
            function_name = data.get('function')
            result = data.get('result')
            logger.info(f"Function {function_name} result: {result}")
            
        elif message_type == 'plugin_toggled':
            plugin = data.get('plugin')
            status = data.get('status')
            logger.info(f"Plugin {plugin} {status}")
            
        elif message_type == 'error':
            error_message = data.get('message', 'Unknown error')
            logger.error(f"Server error: {error_message}")
            
            await self.update_overlay_status("Error")
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def simulate_user_input(self):
        """Symuluj interakcję użytkownika (do testów)."""
        await asyncio.sleep(2)  # Poczekaj na połączenie
        
        # Symuluj kilka zapytań
        test_queries = [
            "Jaka jest pogoda?",
            "Wyszukaj informacje o Python",
            "Włącz plugin weather_module"
        ]
        
        for query in test_queries:
            await asyncio.sleep(5)  # Pauza między zapytaniami
            
            if query.startswith("Włącz plugin"):
                # Plugin toggle request
                plugin_name = query.split()[-1]
                message = {
                    "type": "plugin_toggle",
                    "plugin": plugin_name,
                    "action": "enable"
                }
            else:                # AI query
                message = {
                    "type": "ai_query",
                    "query": query,
                    "context": {}
                }
            
            await self.send_message(message)
            logger.info(f"Sent query: {query}")
    
    async def start(self):
        """Uruchom klienta."""
        self.running = True
        
        try:
            # Initialize components first
            logger.info("Initializing client components...")
            if not await self.initialize_components():
                logger.error("Failed to initialize components")
                return
            
            logger.info("Client components initialized successfully")
            
            # Połącz się z serwerem
            await self.connect_to_server()
            
            # Start wakeword detection
            await self.start_wakeword_detection()
            
            # Uruchom zadania w tle
            asyncio.create_task(self.listen_for_messages())
            asyncio.create_task(self.simulate_user_input())  # Tylko do testów
            
            logger.info("Client started successfully - listening for commands...")
            
            # Keep client running
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Client stopped by user")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        self.running = False
        
        # Stop wakeword detection
        await self.stop_wakeword_detection()
        
        # Close websocket
        if self.websocket:
            await self.websocket.close()
        
        # Stop overlay
        if self.overlay:
            self.overlay.stop()
        
        logger.info("Client cleanup completed")
    
    def stop(self):
        """Zatrzymaj klienta."""
        self.running = False

    async def on_wakeword_detected(self):
        """Callback wywoływany gdy wykryto wakeword."""
        if self.recording_command:
            logger.debug("Already recording, ignoring wakeword")
            return
        
        logger.info("Wakeword detected! Starting command recording...")
        
        if self.overlay:
            self.overlay.update_status("Listening...")
            self.overlay.add_message("Wakeword detected - listening for command", "system")
        
        await self.start_command_recording()
    
    async def start_command_recording(self):
        """Rozpocznij nagrywanie komendy."""
        if not self.audio_recorder or self.recording_command:
            return
        
        self.recording_command = True
        
        try:
            # Record audio
            duration = self.config.get('audio', {}).get('record_duration', 5.0)
            audio_data = await self.audio_recorder.record_audio(duration)
            
            if audio_data is not None:
                logger.info("Audio recorded, transcribing...")
                
                if self.overlay:
                    self.overlay.update_status("Processing...")
                
                # Transcribe using Whisper
                text = await self.whisper_asr.transcribe_audio(audio_data)
                
                if text:
                    logger.info(f"Transcribed text: {text}")
                    
                    if self.overlay:
                        self.overlay.add_message(text, "user")
                        self.overlay.update_status("Sending to AI...")
                    
                    # Send to server
                    await self.process_voice_command(text)
                else:
                    logger.warning("No text transcribed from audio")
                    
                    if self.overlay:
                        self.overlay.add_message("Could not understand audio", "error")
                        self.overlay.update_status("Ready")
            else:
                logger.error("Failed to record audio")
                
                if self.overlay:
                    self.overlay.add_message("Failed to record audio", "error")
                    self.overlay.update_status("Ready")
        
        except Exception as e:
            logger.error(f"Error in command recording: {e}")
            
            if self.overlay:
                self.overlay.add_message(f"Recording error: {e}", "error")
                self.overlay.update_status("Ready")
        
        finally:
            self.recording_command = False
    
    async def process_voice_command(self, text: str):
        """Przetwórz komendę głosową."""
        try:
            # Create AI query message
            message = {
                "type": "ai_query",
                "query": text,
                "context": {
                    "input_method": "voice",
                    "language": "pl"
                }
            }
            
            # Send to server
            await self.send_message(message)
            
            logger.info(f"Voice command sent: {text}")
            
        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
    
    async def start_wakeword_detection(self):
        """Uruchom detekcję wakeword."""
        if self.wakeword_detector and not self.listening_for_wakeword:
            success = self.wakeword_detector.start()
            if success:
                self.listening_for_wakeword = True
                logger.info("Wakeword detection started")
                
                if self.overlay:
                    self.overlay.update_status("Listening for wakeword")
            else:
                logger.error("Failed to start wakeword detection")
    
    async def stop_wakeword_detection(self):
        """Zatrzymaj detekcję wakeword."""
        if self.wakeword_detector and self.listening_for_wakeword:
            self.wakeword_detector.stop()
            self.listening_for_wakeword = False
            logger.info("Wakeword detection stopped")
            
            if self.overlay:
                self.overlay.update_status("Ready")
    
    async def start_overlay(self):
        """Uruchom zewnętrzny overlay Tauri."""
        try:
            overlay_path = Path("../overlay/target/release/Asystent Overlay.exe")
            if overlay_path.exists():
                self.overlay_process = subprocess.Popen([str(overlay_path)])
                logger.info("External Tauri overlay started")
                return True
            else:
                logger.warning(f"Overlay not found at {overlay_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to start overlay: {e}")
            return False
    
    async def stop_overlay(self):
        """Zatrzymaj zewnętrzny overlay."""
        if self.overlay_process:
            try:
                self.overlay_process.terminate()
                self.overlay_process.wait(timeout=5)
                logger.info("External overlay stopped")
            except subprocess.TimeoutExpired:
                self.overlay_process.kill()
                logger.warning("External overlay force killed")
            except Exception as e:
                logger.error(f"Error stopping overlay: {e}")
            finally:
                self.overlay_process = None

    async def update_overlay_status(self, status: str):
        """Zaktualizuj status w overlay przez API serwera."""
        # Overlay pobiera status z endpointu /api/status serwera
        # Więc wyślemy informację do serwera żeby zaktualizował status
        try:
            message = {
                "type": "status_update",
                "status": status,
                "client_id": self.user_id
            }
            await self.send_message(message)
        except Exception as e:
            logger.error(f"Error updating overlay status: {e}")


def main():
    """Główna funkcja klienta."""
    # Konfiguracja logowania
    logger.remove()
    logger.add(
        "logs/client_{time:YYYY-MM-DD}.log",
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
    
    # Utwórz katalog logs jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Starting GAJA Assistant Client...")
    
    # Uruchom klienta
    client = ClientApp()
    
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Client error: {e}")


if __name__ == "__main__":
    main()

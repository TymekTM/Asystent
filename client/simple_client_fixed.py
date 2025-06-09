"""
Simple GAJA Client bez overlay - tylko połączenie WebSocket i console
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional
import websockets
from loguru import logger

# Add client path to PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

class SimpleClientApp:
    """Prosty klient GAJA - tylko WebSocket i console."""
    
    def __init__(self):
        self.config = self.load_client_config()
        self.websocket = None
        self.user_id = self.config.get('user_id', '1')        self.server_url = self.config.get('server_url', 'ws://localhost:8001')
        self.running = False

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
            "server_url": "ws://localhost:8001"
        }
    
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
                "query": "Cześć! Jestem prostym klientem GAJA.",
                "context": {
                    "client_version": "simple-1.0.0"
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
            logger.info(f"[AI] {response}")
            print(f"🤖 AI: {response}")
            
        elif message_type == 'function_result':
            function_name = data.get('function')
            result = data.get('result')
            logger.info(f"Function {function_name} result: {result}")
            print(f"⚙️ Function {function_name}: {result}")
            
        elif message_type == 'plugin_toggled':
            plugin = data.get('plugin')
            status = data.get('status')
            logger.info(f"Plugin {plugin} {status}")
            print(f"🔌 Plugin {plugin} {status}")
            
        elif message_type == 'error':
            error_message = data.get('message', 'Unknown error')
            logger.error(f"Server error: {error_message}")
            print(f"❌ Error: {error_message}")
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            print(f"❓ Unknown message: {message_type}")
    
    async def simulate_user_input(self):
        """Symuluj interakcję użytkownika."""
        await asyncio.sleep(2)  # Poczekaj na połączenie
        
        test_queries = [
            "Jaka jest pogoda?",
            "Wyszukaj informacje o Python",
            "Test funkcji AI"
        ]
        
        for query in test_queries:
            await asyncio.sleep(3)
            
            message = {
                "type": "ai_query",
                "query": query,
                "context": {}
            }
            
            await self.send_message(message)
            logger.info(f"Sent query: {query}")
            print(f"👤 You: {query}")
    
    async def start(self):
        """Uruchom prostego klienta."""
        try:
            logger.info("Starting Simple GAJA Client...")
            print("🚀 Starting Simple GAJA Client...")
            
            self.running = True
            
            # Połącz się z serwerem
            await self.connect_to_server()
            
            # Start listening for messages and simulating input
            await asyncio.gather(
                self.listen_for_messages(),
                self.simulate_user_input()
            )
            
        except KeyboardInterrupt:
            logger.info("Client stopped by user")
            print("\n👋 Client stopped by user")
        except Exception as e:
            logger.error(f"Client error: {e}")
            print(f"💥 Client error: {e}")
        finally:
            self.running = False
            if self.websocket:
                await self.websocket.close()
            logger.info("Client shutdown complete")
            print("🛑 Client shutdown complete")


def main():
    """Główna funkcja prostego klienta."""
    # Konfiguracja logowania
    logger.remove()
    logger.add(
        "logs/simple_client_{time:YYYY-MM-DD}.log",
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
    
    logger.info("Starting Simple GAJA Assistant Client...")
    
    # Uruchom klienta
    client = SimpleClientApp()
    
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Client error: {e}")


if __name__ == "__main__":
    main()

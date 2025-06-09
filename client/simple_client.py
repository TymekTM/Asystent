"""
Simple GAJA Assistant Client - bez overlay
Test komunikacji z serwerem.
"""

import asyncio
import json
import sys
from pathlib import Path
import websockets
from loguru import logger

# Dodaj ścieżkę klienta do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))


class SimpleClient:
    """Prosty klient testowy."""
    
    def __init__(self):
        self.websocket = None
        self.user_id = "1"
        self.server_url = "ws://localhost:8000"
        self.running = False
    
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
                "query": "Cześć! Jestem prostym klientem testowym.",
                "context": {
                    "client_version": "1.0.0-simple",
                    "features": ["basic_communication"]
                }
            }
            
            await self.send_message(test_message)
            
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            raise
    
    async def send_message(self, message: dict):
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
    
    async def handle_server_message(self, data: dict):
        """Obsłuż wiadomość od serwera."""
        message_type = data.get('type')
        
        if message_type == 'ai_response':
            response = data.get('response', '')
            logger.info(f"AI Response: {response}")
            
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
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def simulate_user_input(self):
        """Symuluj interakcję użytkownika."""
        await asyncio.sleep(2)  # Poczekaj na połączenie
        
        # Symuluj kilka zapytań
        test_queries = [
            "Jaka jest pogoda?",
            "Zapisz w pamięci: 'Test klienta prostego'",
            "Wyszukaj informacje o Python",
            "Co jest zapisane w pamięci?"
        ]
        
        for query in test_queries:
            await asyncio.sleep(3)  # Pauza między zapytaniami
            
            if not self.running:
                break
            
            message = {
                "type": "ai_query",
                "query": query,
                "context": {}
            }
            
            await self.send_message(message)
            logger.info(f"Sent query: {query}")
        
        # Po testach, czekaj na input użytkownika
        logger.info("Test queries completed. Type 'quit' to exit.")
        await self.interactive_mode()
    
    async def interactive_mode(self):
        """Tryb interaktywny."""
        while self.running:
            try:
                # W rzeczywistości asyncio + input() jest problematyczne
                # To jest uproszczenie dla celów testowych
                await asyncio.sleep(1)
                
                # W prawdziwej implementacji użylibyśmy aioconsole lub podobną bibliotekę
                print("\nType your message (or 'quit' to exit):")
                
            except KeyboardInterrupt:
                break
    
    async def start(self):
        """Uruchom klienta."""
        self.running = True
        
        try:
            logger.info("Starting simple client...")
            
            # Połącz się z serwerem
            await self.connect_to_server()
            
            # Uruchom zadania w tle
            listen_task = asyncio.create_task(self.listen_for_messages())
            simulate_task = asyncio.create_task(self.simulate_user_input())
            
            logger.info("Simple client started - press Ctrl+C to stop")
            
            # Czekaj na zadania
            await asyncio.gather(listen_task, simulate_task, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("Client stopped by user")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        self.running = False
        
        # Close websocket
        if self.websocket:
            await self.websocket.close()
        
        logger.info("Simple client cleanup completed")


async def main():
    """Główna funkcja."""
    # Konfiguracja logowania
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}:{function}:{line}</cyan> | {message}"
    )
    
    logger.info("Starting Simple GAJA Client...")
    
    client = SimpleClient()
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())

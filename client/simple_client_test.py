#!/usr/bin/env python3
"""
Prosty klient GAJA do testów komunikacji z serwerem.
"""

import asyncio
import json
import websockets
import logging
from typing import Dict
from pathlib import Path

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class SimpleGAJAClient:
    """Prosty klient GAJA do testów komunikacji."""
    
    def __init__(self):
        self.config = self.load_client_config()
        self.websocket = None
        self.user_id = self.config.get('user_id', '1')
        self.server_url = self.config.get('server_url', 'ws://localhost:8001')
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
            logger.info("Connected to server")
            
            # Wyślij wiadomość testową
            test_message = {
                "type": "ai_query",
                "query": "Cześć! Jestem prostym klientem GAJA. Jaka jest pogoda?",
                "context": {
                    "client_version": "simple-1.0.0"
                }
            }
            
            await self.websocket.send(json.dumps(test_message))
            logger.info("Test message sent")
            
            # Odbierz odpowiedź
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            logger.info(f"Received response: {response_data}")
            print(f"🤖 AI Response: {response_data.get('response', 'No response')}")
            
            if "function_calls" in response_data:
                print(f"🔧 Function calls: {response_data['function_calls']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False
    
    async def test_communication(self):
        """Przetestuj komunikację z serwerem."""
        logger.info("Testing communication with server...")
        print("🧪 Testing communication with server...")
        
        if await self.connect_to_server():
            logger.info("Communication test successful")
            print("✅ Communication test successful")
            
            # Test dodatkowych zapytań
            test_queries = [
                "Znajdź informacje o Python",
                "Jak się masz?"
            ]
            
            for query in test_queries:
                try:
                    message = {
                        "type": "ai_query",
                        "query": query,
                        "context": {"test": True}
                    }
                    
                    await self.websocket.send(json.dumps(message))
                    response = await self.websocket.recv()
                    response_data = json.loads(response)
                    
                    print(f"📝 Query: {query}")
                    print(f"🤖 Response: {response_data.get('response', 'No response')}")
                    
                    if "function_calls" in response_data:
                        print(f"🔧 Function calls: {response_data['function_calls']}")
                    
                    print("-" * 50)
                    
                except Exception as e:
                    logger.error(f"Error sending query '{query}': {e}")
            
        else:
            logger.error("Communication test failed")
            print("❌ Communication test failed")
    
    async def disconnect(self):
        """Rozłącz się z serwerem."""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from server")

async def main():
    """Główna funkcja."""
    logger.info("Starting Simple GAJA Assistant Client...")
    print("🚀 Starting Simple GAJA Assistant Client...")
    
    client = SimpleGAJAClient()
    
    try:
        await client.test_communication()
    except Exception as e:
        logger.error(f"Client error: {e}")
        print(f"💥 Client error: {e}")
    finally:
        await client.disconnect()
        logger.info("Client shutdown complete")
        print("🛑 Client shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())

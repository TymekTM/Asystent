#!/usr/bin/env python3
"""
Prosty test WebSocket serwera na porcie 6001
"""

import asyncio
import websockets
import json
import logging

# Ustaw logi
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def handle_client(websocket, path):
    """Obsługa połączenia WebSocket"""
    logger.info(f"Klient połączony: {websocket.remote_address}")
    
    try:
        # Wyślij wiadomość powitalną
        welcome = {
            "type": "welcome",
            "message": "WebSocket serwer działa!",
            "port": 6001
        }
        await websocket.send(json.dumps(welcome))
        
        # Słuchaj wiadomości
        async for message in websocket:
            logger.info(f"Otrzymano: {message}")
            # Echo odpowiedź
            response = {
                "type": "echo",
                "original": message,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            await websocket.send(json.dumps(response))
            
    except websockets.exceptions.ConnectionClosed:
        logger.info("Klient rozłączony")
    except Exception as e:
        logger.error(f"Błąd: {e}")

async def start_server():
    """Uruchom WebSocket serwer"""
    try:
        # Próbuj różne porty
        ports = [6001, 6000, 6002, 8765]
        server = None
        
        for port in ports:
            try:
                server = await websockets.serve(
                    handle_client,
                    "127.0.0.1",
                    port
                )
                logger.info(f"✅ WebSocket serwer uruchomiony na porcie {port}")
                logger.info(f"🔗 Adres: ws://localhost:{port}")
                break
            except OSError as e:
                logger.warning(f"Port {port} niedostępny: {e}")
                continue
        
        if not server:
            raise Exception("Nie można uruchomić serwera na żadnym porcie")
        
        # Czekaj na zatrzymanie
        await server.wait_closed()
        
    except Exception as e:
        logger.error(f"❌ Błąd uruchamiania serwera: {e}")
        raise

async def main():
    """Główna funkcja"""
    logger.info("🚀 Uruchamianie prostego WebSocket serwera...")
    
    try:
        await start_server()
    except KeyboardInterrupt:
        logger.info("🛑 Serwer zatrzymany przez użytkownika")
    except Exception as e:
        logger.error(f"❌ Błąd krytyczny: {e}")

if __name__ == "__main__":
    asyncio.run(main())

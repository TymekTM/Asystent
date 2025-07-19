#!/usr/bin/env python3
"""
Dedykowany WebSocket server dla overlay - prosty i stabilny
"""

import asyncio
import json
import websockets
import time
from datetime import datetime

class OverlayWebSocketServer:
    def __init__(self, port=6001):
        self.port = port
        self.connected_clients = set()
        self.current_status = {
            "status": "ready",
            "text": "Assistant gotowy",
            "is_listening": False,
            "is_speaking": False,
            "wake_word_detected": False,
            "overlay_visible": True,
            "monitoring": True
        }
    
    async def handle_client(self, websocket, path):
        """Obsługuje połączenie z overlay."""
        client_address = websocket.remote_address
        print(f"🔗 Overlay połączył się: {client_address}")
        
        self.connected_clients.add(websocket)
        
        try:
            # Wyślij aktualny status natychmiast po połączeniu
            await self.send_status(websocket)
            
            # Słuchaj wiadomości od overlay
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"📨 Otrzymano od overlay: {data}")
                    
                    # Odpowiedz na ping
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                    
                except json.JSONDecodeError:
                    print(f"❌ Nieprawidłowy JSON: {message}")
                
        except websockets.exceptions.ConnectionClosed:
            print(f"🔗 Overlay rozłączył się: {client_address}")
        except Exception as e:
            print(f"❌ Błąd obsługi klienta: {e}")
        finally:
            self.connected_clients.discard(websocket)
    
    async def send_status(self, websocket):
        """Wyślij status do overlay."""
        message = {
            "type": "status",
            "data": self.current_status,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await websocket.send(json.dumps(message))
            print(f"📤 Wysłano status: {self.current_status['status']}")
        except Exception as e:
            print(f"❌ Błąd wysyłania: {e}")
    
    async def broadcast_status(self):
        """Rozgłaszaj status do wszystkich połączonych overlay."""
        if self.connected_clients:
            message = {
                "type": "status", 
                "data": self.current_status,
                "timestamp": datetime.now().isoformat()
            }
            
            disconnected = set()
            for websocket in self.connected_clients:
                try:
                    await websocket.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(websocket)
                except Exception as e:
                    print(f"❌ Błąd rozgłaszania: {e}")
                    disconnected.add(websocket)
            
            # Usuń rozłączone klienty
            self.connected_clients -= disconnected
    
    async def status_simulator(self):
        """Symuluje zmiany statusu dla testowania."""
        statuses = [
            ("ready", "Assistant gotowy", False, False),
            ("listening", "Słucham...", True, False),
            ("processing", "Przetwarzam...", False, False),
            ("speaking", "Odpowiadam...", False, True),
            ("ready", "Assistant gotowy", False, False),
        ]
        
        while True:
            for status, text, listening, speaking in statuses:
                self.current_status.update({
                    "status": status,
                    "text": text,
                    "is_listening": listening,
                    "is_speaking": speaking,
                    "wake_word_detected": listening,
                    "overlay_visible": True
                })
                
                await self.broadcast_status()
                print(f"🔄 Status zmieniony na: {status} - {text}")
                await asyncio.sleep(5)  # Zmiana co 5 sekund
    
    async def start_server(self):
        """Uruchom WebSocket server."""
        print(f"🚀 Uruchamiam WebSocket server na porcie {self.port}")
        
        # Uruchom server
        server = await websockets.serve(
            self.handle_client,
            "localhost",
            self.port
        )
        
        print(f"✅ WebSocket server nasłuchuje na ws://localhost:{self.port}")
        print(f"📊 Server object: {server}")
        
        # Uruchom symulator statusu
        status_task = asyncio.create_task(self.status_simulator())
        
        try:
            # Czekaj nieskończenie
            await asyncio.gather(
                server.wait_closed(),
                status_task
            )
        except KeyboardInterrupt:
            print("\n⏹️ Zatrzymywanie serwera...")
            server.close()
            await server.wait_closed()
            status_task.cancel()


async def main():
    """Główna funkcja."""
    print("🎯 DEDYKOWANY WEBSOCKET SERVER DLA OVERLAY")
    print("=" * 50)
    
    server = OverlayWebSocketServer(port=6000)
    await server.start_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Serwer zatrzymany przez użytkownika")

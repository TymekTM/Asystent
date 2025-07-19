#!/usr/bin/env python3
"""
Dogłębna diagnostyka WebSocket klienta
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path

# Dodaj ścieżki
sys.path.append(str(Path(__file__).parent / "client"))

async def diagnose_client_websocket():
    """Dogłębna diagnostyka klienta"""
    print("🔬 DOGŁĘBNA DIAGNOSTYKA KLIENTA WEBSOCKET")
    print("=" * 60)
    
    try:
        # Import z debugging
        print("📥 Importowanie ClientApp...")
        from client.client_main import ClientApp
        print("✅ Import udany")
        
        # Stwórz instancję
        print("🏗️  Tworzenie instancji klienta...")
        client = ClientApp()
        print("✅ Instancja utworzona")
        
        # Sprawdź konfigurację
        print(f"🔧 Konfiguracja: {client.config}")
        print(f"🔗 Server URL: {client.server_url}")
        
        # Sprawdź czy WebSocket server jest None
        print(f"🌐 WebSocket server przed startem: {client.websocket_server}")
        print(f"👥 WebSocket clients przed startem: {client.websocket_clients}")
        
        # Start HTTP server
        print("🚀 Uruchamianie HTTP serwera...")
        client.start_http_server()
        print("✅ HTTP serwer uruchomiony")
        
        # Start WebSocket server z debuggingiem
        print("🚀 Uruchamianie WebSocket serwera...")
        await client.start_websocket_server()
        print("✅ WebSocket serwer uruchomiony")
        
        # Sprawdź status po starcie
        print(f"🌐 WebSocket server po starcie: {client.websocket_server}")
        if client.websocket_server:
            print(f"🔌 Server sockets: {client.websocket_server.sockets}")
            print(f"🏃 Server running: {not client.websocket_server.closed}")
            
            # Test czy server rzeczywiście słucha
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 6001))
            sock.close()
            print(f"🔍 Port 6001 test (0=open): {result}")
            
            if result == 0:
                print("✅ Port 6001 jest otwarty!")
                
                # Test WebSocket connection
                print("🔍 Testuję połączenie WebSocket...")
                try:
                    import websockets
                    async with websockets.connect("ws://127.0.0.1:6001") as ws:
                        print("✅ Połączenie WebSocket udane!")
                        
                        # Test komunikacji
                        test_msg = {"type": "test", "data": "connection test"}
                        await ws.send(json.dumps(test_msg))
                        print("📤 Wiadomość wysłana")
                        
                        return True
                        
                except Exception as e:
                    print(f"❌ Błąd WebSocket: {e}")
            else:
                print(f"❌ Port 6001 zamknięty (kod: {result})")
        
        else:
            print("❌ WebSocket server nie został utworzony!")
        
        return False
        
    except Exception as e:
        print(f"💥 Błąd diagnozy: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_websocket_server():
    """Test czy prosty WebSocket server działa"""
    print("\n🧪 TEST PROSTEGO WEBSOCKET SERWERA")
    print("=" * 50)
    
    try:
        import websockets
        
        async def simple_handler(websocket, path):
            print(f"📞 Połączenie: {websocket.remote_address}")
            async for message in websocket:
                print(f"📥 Otrzymano: {message}")
                await websocket.send(f"Echo: {message}")
        
        print("🚀 Uruchamianie prostego serwera na 6001...")
        server = await websockets.serve(simple_handler, "127.0.0.1", 6001)
        print("✅ Prosty serwer uruchomiony")
        
        # Test połączenia
        await asyncio.sleep(1)
        try:
            async with websockets.connect("ws://127.0.0.1:6001") as ws:
                await ws.send("test message")
                response = await ws.recv()
                print(f"✅ Prosty test udany: {response}")
                return True
        except Exception as e:
            print(f"❌ Prosty test nieudany: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Błąd prostego serwera: {e}")
        return False

async def main():
    """Główna funkcja"""
    # Test 1: Prosty WebSocket
    simple_ok = await test_simple_websocket_server()
    
    # Test 2: WebSocket klienta  
    client_ok = await diagnose_client_websocket()
    
    print("\n" + "=" * 60)
    print("📊 WYNIKI DIAGNOZY")
    print("=" * 60)
    print(f"🔧 Prosty WebSocket:    {'✅' if simple_ok else '❌'}")
    print(f"🤖 Klient WebSocket:    {'✅' if client_ok else '❌'}")
    
    if simple_ok and not client_ok:
        print("\n🎯 WNIOSEK: Problem w implementacji klienta, nie w WebSocket")
    elif client_ok:
        print("\n🎉 SUCCESS: Klient WebSocket działa!")
    else:
        print("\n❌ PROBLEM: WebSocket w ogóle nie działa")
    
    return client_ok

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n{'🎉 SUKCES' if success else '❌ BŁĄD'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Diagnoza przerwana")
        sys.exit(1)

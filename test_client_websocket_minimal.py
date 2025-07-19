#!/usr/bin/env python3
"""
Minimal test WebSocket w kliencie - sprawdza gdzie jest problem
"""

import asyncio
import sys
import os
from pathlib import Path

# Dodaj ścieżki do importów
sys.path.append(str(Path(__file__).parent / "client"))

async def test_client_websocket_minimal():
    """Test minimalny WebSocket klienta"""
    print("🔍 TEST MINIMALNY WEBSOCKET KLIENTA")
    print("=" * 50)
    
    try:
        # Import klienta
        from client.client_main import ClientApp
        print("✅ Import ClientApp udany")
        
        # Stwórz instancję
        client = ClientApp()
        print("✅ Instancja klienta utworzona")
        
        # Uruchom tylko HTTP i WebSocket serwery
        print("🚀 Uruchamianie HTTP serwera...")
        client.start_http_server()
        print("✅ HTTP serwer uruchomiony")
        
        print("🚀 Uruchamianie WebSocket serwera...")
        await client.start_websocket_server()
        print("✅ WebSocket serwer uruchomiony")
        
        if client.websocket_server:
            print(f"📊 WebSocket server: {client.websocket_server}")
            print(f"📊 Server sockets: {client.websocket_server.sockets}")
            
            # Test połączenia po 2 sekundach
            await asyncio.sleep(2)
            
            print("🔍 Testuję połączenie...")
            try:
                import websockets
                async with websockets.connect("ws://127.0.0.1:6001") as websocket:
                    print("✅ Połączenie z klientem WebSocket udane!")
                    
                    # Wyślij test message
                    import json
                    test_msg = {"type": "test", "data": "test connection"}
                    await websocket.send(json.dumps(test_msg))
                    print("📤 Wiadomość wysłana")
                    
                    return True
                    
            except Exception as e:
                print(f"❌ Błąd połączenia: {e}")
                return False
        else:
            print("❌ WebSocket server nie został utworzony")
            return False
            
    except Exception as e:
        print(f"❌ Błąd testu: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Główna funkcja testowa"""
    result = await test_client_websocket_minimal()
    
    if result:
        print("\n🎉 SUCCESS! Klient WebSocket działa!")
    else:
        print("\n❌ FAILED! Problem z klientem WebSocket")
    
    return result

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n{'✅ SUKCES' if success else '❌ BŁĄD'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test przerwany")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Niespodziewany błąd: {e}")
        sys.exit(1)

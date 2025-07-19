#!/usr/bin/env python3
"""
Test bezpośredni portu WebSocket z wnętrza działającego klienta
"""

import asyncio
import websockets
import json
import subprocess
import time
import signal
import sys

async def test_websocket_directly():
    """Test WebSocket bezpośrednio podczas działania klienta"""
    print("🔍 Test bezpośredniego połączenia WebSocket")
    
    # Uruchom klienta w tle
    print("🚀 Uruchamianie klienta...")
    process = subprocess.Popen(
        ["python", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Czekaj na uruchomienie
    print("⏳ Czekam 10 sekund na uruchomienie...")
    await asyncio.sleep(10)
    
    # Test różnych metod połączenia
    test_urls = [
        "ws://localhost:6001",
        "ws://127.0.0.1:6001", 
        "ws://0.0.0.0:6001"
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testuję {url}")
        try:
            # Bardzo krótki timeout
            async with websockets.connect(url, timeout=2) as websocket:
                print(f"✅ {url} - POŁĄCZENIE UDANE!")
                
                # Wyślij test
                test_msg = {
                    "type": "status_update",
                    "status": "testing",
                    "text": "Test połączenia"
                }
                await websocket.send(json.dumps(test_msg))
                print(f"📤 {url} - wiadomość wysłana")
                
                return True
                
        except asyncio.TimeoutError:
            print(f"⏰ {url} - timeout")
        except ConnectionRefusedError:
            print(f"❌ {url} - połączenie odrzucone")
        except Exception as e:
            print(f"❌ {url} - błąd: {e}")
    
    # Sprawdź czy proces nadal działa
    if process.poll() is None:
        print("✅ Klient nadal działa")
        process.terminate()
    else:
        print("❌ Klient się zakończył")
    
    return False

def main():
    print("🧪 TEST BEZPOŚREDNI WEBSOCKET")
    print("=" * 50)
    
    try:
        result = asyncio.run(test_websocket_directly())
        if result:
            print("\n🎉 WebSocket działa!")
        else:
            print("\n❌ WebSocket nie działa")
        return result
    except KeyboardInterrupt:
        print("\n🛑 Test przerwany")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

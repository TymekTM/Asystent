#!/usr/bin/env python3
"""
Test kompletnego systemu GAJA
Sprawdza komunikację między overlay, klientem i serwerem
"""

import asyncio
import websockets
import json
import time
import subprocess
import os
import signal
import sys
from datetime import datetime

class SystemTester:
    def __init__(self):
        self.overlay_process = None
        self.client_process = None
        
    async def test_websocket_connection(self, url, name, timeout=10):
        """Test połączenia WebSocket"""
        print(f"🔍 Testowanie {name} na {url}")
        try:
            async with websockets.connect(url, timeout=timeout) as websocket:
                print(f"✅ {name} - połączenie udane")
                
                # Wyślij test message
                test_message = {
                    "type": "test",
                    "timestamp": datetime.now().isoformat(),
                    "data": f"Test z {name}"
                }
                await websocket.send(json.dumps(test_message))
                print(f"📤 {name} - wiadomość testowa wysłana")
                
                # Czekaj na odpowiedź
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    print(f"📥 {name} - otrzymano odpowiedź: {response[:100]}...")
                except asyncio.TimeoutError:
                    print(f"⏰ {name} - timeout na odpowiedź")
                
                return True
        except Exception as e:
            print(f"❌ {name} - błąd połączenia: {e}")
            return False
    
    def start_overlay(self):
        """Uruchom overlay"""
        print("🚀 Uruchamianie overlay...")
        try:
            os.chdir(r"f:\Asystent\overlay")
            self.overlay_process = subprocess.Popen(
                ["cargo", "tauri", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            print("✅ Overlay uruchomiony")
            return True
        except Exception as e:
            print(f"❌ Błąd uruchamiania overlay: {e}")
            return False
    
    def start_client(self):
        """Uruchom klienta"""
        print("🚀 Uruchamianie klienta...")
        try:
            os.chdir(r"f:\Asystent")
            self.client_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            print("✅ Klient uruchomiony")
            return True
        except Exception as e:
            print(f"❌ Błąd uruchamiania klienta: {e}")
            return False
    
    def cleanup(self):
        """Zatrzymaj wszystkie procesy"""
        print("🧹 Sprzątanie procesów...")
        if self.overlay_process:
            try:
                self.overlay_process.terminate()
                self.overlay_process.wait(timeout=5)
            except:
                self.overlay_process.kill()
        
        if self.client_process:
            try:
                self.client_process.terminate()
                self.client_process.wait(timeout=5)
            except:
                self.client_process.kill()
        print("✅ Procesy zatrzymane")
    
    async def test_server_health(self):
        """Test zdrowia serwera"""
        print("🏥 Testowanie zdrowia serwera...")
        try:
            # Test połączenia WebSocket z serwerem
            return await self.test_websocket_connection(
                "ws://localhost:8001/ws/test_client", 
                "Serwer GAJA"
            )
        except Exception as e:
            print(f"❌ Błąd testu serwera: {e}")
            return False
    
    async def test_client_websocket(self):
        """Test WebSocket klienta dla overlay"""
        print("🔌 Testowanie WebSocket klienta...")
        try:
            return await self.test_websocket_connection(
                "ws://localhost:6001", 
                "Klient WebSocket"
            )
        except Exception as e:
            print(f"❌ Błąd testu klienta: {e}")
            return False
    
    async def run_tests(self):
        """Uruchom wszystkie testy"""
        print("=" * 50)
        print("🧪 ROZPOCZYNAM TESTY SYSTEMU GAJA")
        print("=" * 50)
        
        # Test 1: Sprawdź serwer
        server_ok = await self.test_server_health()
        
        # Test 2: Uruchom klienta
        if not self.start_client():
            print("❌ Nie można uruchomić klienta")
            return False
        
        # Czekaj na uruchomienie klienta
        print("⏳ Czekam 10 sekund na uruchomienie klienta...")
        await asyncio.sleep(10)
        
        # Test 3: Sprawdź WebSocket klienta
        client_ws_ok = await self.test_client_websocket()
        
        # Test 4: Uruchom overlay
        if not self.start_overlay():
            print("❌ Nie można uruchomić overlay")
            return False
        
        # Czekaj na uruchomienie overlay
        print("⏳ Czekam 15 sekund na uruchomienie overlay...")
        await asyncio.sleep(15)
        
        # Test 5: Sprawdź komunikację overlay-klient
        overlay_client_ok = await self.test_client_websocket()
        
        # Podsumowanie
        print("\n" + "=" * 50)
        print("📊 PODSUMOWANIE TESTÓW")
        print("=" * 50)
        print(f"Serwer GAJA: {'✅' if server_ok else '❌'}")
        print(f"Klient WebSocket: {'✅' if client_ws_ok else '❌'}")
        print(f"Komunikacja Overlay-Klient: {'✅' if overlay_client_ok else '❌'}")
        
        all_ok = server_ok and client_ws_ok and overlay_client_ok
        print(f"\n🎯 WYNIK OGÓLNY: {'✅ SUKCES' if all_ok else '❌ BŁĘDY'}")
        
        return all_ok

def signal_handler(sig, frame):
    print("\n🛑 Otrzymano sygnał przerwania")
    sys.exit(0)

async def main():
    # Obsługa Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    tester = SystemTester()
    try:
        result = await tester.run_tests()
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\n🛑 Test przerwany przez użytkownika")
        return 1
    finally:
        tester.cleanup()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Program przerwany")
        sys.exit(1)

#!/usr/bin/env python3
"""
Finalny test systemu - sprawdza czy wszystko działa razem
"""

import asyncio
import subprocess
import time
import websockets
import json
import signal
import sys
import os

class FinalSystemTest:
    def __init__(self):
        self.client_process = None
        self.overlay_process = None
    
    def start_client(self):
        """Uruchom klienta Python"""
        print("🚀 Uruchamianie klienta Python...")
        try:
            os.chdir("f:/Asystent")
            self.client_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            print(f"✅ Klient uruchomiony, PID: {self.client_process.pid}")
            return True
        except Exception as e:
            print(f"❌ Błąd uruchamiania klienta: {e}")
            return False
    
    def start_overlay(self):
        """Uruchom overlay Tauri"""
        print("🚀 Uruchamianie overlay Tauri...")
        try:
            os.chdir("f:/Asystent/overlay")
            self.overlay_process = subprocess.Popen(
                ["cargo", "tauri", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            print(f"✅ Overlay uruchomiony, PID: {self.overlay_process.pid}")
            return True
        except Exception as e:
            print(f"❌ Błąd uruchamiania overlay: {e}")
            return False
    
    async def test_server_connection(self):
        """Test połączenia z serwerem"""
        print("🔍 Test połączenia z serwerem...")
        try:
            async with websockets.connect("ws://localhost:8001/ws/test_final", timeout=5) as ws:
                await ws.send(json.dumps({"type": "test"}))
                response = await asyncio.wait_for(ws.recv(), timeout=3)
                print("✅ Serwer odpowiada")
                return True
        except Exception as e:
            print(f"❌ Błąd serwera: {e}")
            return False
    
    async def test_client_websocket(self, max_attempts=10):
        """Test WebSocket klienta z wieloma próbami"""
        print(f"🔍 Test WebSocket klienta (max {max_attempts} prób)...")
        
        for attempt in range(max_attempts):
            try:
                async with websockets.connect("ws://localhost:6001", timeout=3) as ws:
                    print(f"✅ Połączenie z klientem udane (próba {attempt + 1})")
                    
                    # Test komunikacji
                    test_msg = {
                        "type": "status_update",
                        "status": "testing",
                        "text": "Test systemu",
                        "is_listening": True,
                        "is_speaking": False,
                        "wake_word_detected": False,
                        "overlay_visible": True,
                        "monitoring": True
                    }
                    
                    await ws.send(json.dumps(test_msg))
                    print("📤 Wiadomość testowa wysłana")
                    return True
                    
            except Exception as e:
                print(f"❌ Próba {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2)
        
        return False
    
    def check_processes(self):
        """Sprawdź status procesów"""
        print("🔍 Sprawdzanie procesów...")
        
        if self.client_process:
            status = self.client_process.poll()
            if status is None:
                print("✅ Klient działa")
            else:
                print(f"❌ Klient zakończony z kodem: {status}")
                # Pokaż ostatnie linie output
                try:
                    output = self.client_process.stdout.read()
                    if output:
                        lines = output.split('\n')[-10:]  # Ostatnie 10 linii
                        print("📝 Ostatnie logi klienta:")
                        for line in lines:
                            if line.strip():
                                print(f"   {line}")
                except:
                    pass
        
        if self.overlay_process:
            status = self.overlay_process.poll()
            if status is None:
                print("✅ Overlay działa")
            else:
                print(f"❌ Overlay zakończony z kodem: {status}")
    
    def cleanup(self):
        """Zatrzymaj wszystkie procesy"""
        print("🧹 Sprzątanie...")
        
        if self.client_process and self.client_process.poll() is None:
            print("🛑 Zatrzymuję klienta...")
            self.client_process.terminate()
            try:
                self.client_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.client_process.kill()
        
        if self.overlay_process and self.overlay_process.poll() is None:
            print("🛑 Zatrzymuję overlay...")
            self.overlay_process.terminate()
            try:
                self.overlay_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.overlay_process.kill()
    
    async def run_complete_test(self):
        """Uruchom kompletny test systemu"""
        print("🎯 FINALNY TEST SYSTEMU GAJA")
        print("=" * 60)
        
        try:
            # Test 1: Serwer
            server_ok = await self.test_server_connection()
            
            # Test 2: Klient
            if not self.start_client():
                return False
            
            print("⏳ Czekam 15 sekund na pełne uruchomienie klienta...")
            await asyncio.sleep(15)
            
            self.check_processes()
            
            client_ws_ok = await self.test_client_websocket()
            
            # Test 3: Overlay  
            if not self.start_overlay():
                print("⚠️  Overlay nie uruchomiony, ale klient może działać bez niego")
            
            print("⏳ Czekam 10 sekund na overlay...")
            await asyncio.sleep(10)
            
            self.check_processes()
            
            # Test końcowy komunikacji
            final_test = await self.test_client_websocket(max_attempts=3)
            
            # Podsumowanie
            print("\n" + "=" * 60)
            print("📊 WYNIKI FINALNEGO TESTU")
            print("=" * 60)
            print(f"🔗 Serwer GAJA:           {'✅' if server_ok else '❌'}")
            print(f"🔌 Klient WebSocket:      {'✅' if client_ws_ok else '❌'}")
            print(f"🎯 Test końcowy:          {'✅' if final_test else '❌'}")
            
            all_ok = server_ok and (client_ws_ok or final_test)
            print(f"\n🏆 WYNIK KOŃCOWY: {'🎉 SUKCES!' if all_ok else '⚠️  CZĘŚCIOWY SUKCES' if server_ok else '❌ BŁĄD'}")
            
            if all_ok:
                print("🚀 System jest gotowy do produkcji!")
            elif server_ok:
                print("🔧 Klient wymaga poprawek, ale architektura działa")
            else:
                print("🛠️  System wymaga napraw")
            
            return all_ok
            
        except Exception as e:
            print(f"💥 Błąd testu: {e}")
            return False
        finally:
            self.cleanup()

def signal_handler(sig, frame):
    print("\n🛑 Test przerwany przez użytkownika")
    sys.exit(0)

async def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    tester = FinalSystemTest()
    try:
        result = await tester.run_complete_test()
        return result
    except KeyboardInterrupt:
        print("\n🛑 Test przerwany")
        return False
    finally:
        tester.cleanup()

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n{'🎉 FINALNE TESTY ZAKOŃCZONE SUKCESEM' if success else '❌ FINALNE TESTY WYKAZAŁY PROBLEMY'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Program przerwany")
        sys.exit(1)

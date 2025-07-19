#!/usr/bin/env python3
"""KOMPLETNY TEST OVERLAY - uruchom klienta + overlay + symulacja stanów."""

import asyncio
import json
import subprocess
import time
import websockets
from pathlib import Path


class OverlayTestSuite:
    """Kompletny test suite dla overlay."""
    
    def __init__(self):
        self.client_process = None
        self.overlay_process = None
        self.websocket_connection = None
        
    async def start_client(self):
        """Uruchom klienta."""
        print("🚀 Uruchamiam klienta...")
        
        # Uruchom klienta
        self.client_process = subprocess.Popen([
            "python", "client/client_main.py"
        ], cwd="f:/Asystent")
        
        # Czekaj na uruchomienie
        await asyncio.sleep(15)
        
        if self.client_process.poll() is None:
            print("✅ Klient uruchomiony")
            return True
        else:
            print("❌ Klient nie uruchomił się")
            return False
    
    async def start_overlay(self):
        """Uruchom overlay."""
        print("🎭 Uruchamiam overlay...")
        
        overlay_path = Path("f:/Asystent/overlay/target/release/gaja-overlay.exe")
        if not overlay_path.exists():
            print(f"❌ Overlay nie istnieje: {overlay_path}")
            return False
        
        # Uruchom overlay (powinien być teraz widoczny od razu)
        self.overlay_process = subprocess.Popen([str(overlay_path)])
        
        await asyncio.sleep(5)
        
        if self.overlay_process.poll() is None:
            print("✅ Overlay uruchomiony - powinien być widoczny na ekranie!")
            return True
        else:
            print("❌ Overlay nie uruchomił się")
            return False
    
    async def connect_websocket(self):
        """Połącz się z klientem przez WebSocket."""
        print("🔌 Łączę się z klientem przez WebSocket...")
        
        ports = [6001, 6000]
        
        for port in ports:
            try:
                ws_url = f"ws://localhost:{port}"
                self.websocket_connection = await websockets.connect(ws_url)
                print(f"✅ Połączono WebSocket na porcie {port}")
                return True
            except Exception as e:
                print(f"❌ Port {port}: {e}")
                continue
        
        print("❌ Nie udało się połączyć przez WebSocket")
        return False
    
    async def simulate_overlay_states(self):
        """Symuluj różne stany overlay."""
        print("\n🎭 SYMULACJA STANÓW OVERLAY")
        print("=" * 50)
        print("Każdy stan będzie wyświetlany przez 5 sekund")
        print("Sprawdź czy overlay na ekranie zmienia się!")
        print("=" * 50)
        
        # Stany do symulacji
        states = [
            {
                "name": "Ready State",
                "status": "ready", 
                "text": "Assistant gotowy",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True
            },
            {
                "name": "Wake Word Detected",
                "status": "listening",
                "text": "Słucham...",
                "is_listening": True,
                "is_speaking": False,
                "wake_word_detected": True,
                "overlay_visible": True,
                "monitoring": True
            },
            {
                "name": "Processing",
                "status": "processing",
                "text": "Przetwarzam zapytanie...",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True
            },
            {
                "name": "Speaking Response",
                "status": "speaking",
                "text": "Oto odpowiedź na Twoje pytanie o pogodę",
                "is_listening": False,
                "is_speaking": True,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True
            },
            {
                "name": "Error State",
                "status": "error",
                "text": "Wystąpił błąd połączenia z serwerem",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": False
            },
            {
                "name": "Offline Mode",
                "status": "offline",
                "text": "Tryb offline - brak połączenia",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": False
            },
            {
                "name": "Busy Working",
                "status": "busy",
                "text": "Wykonuję zadanie w tle...",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True
            },
            {
                "name": "Notification",
                "status": "notification",
                "text": "Notification: Masz nową wiadomość!",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True
            }
        ]
        
        for i, state in enumerate(states, 1):
            print(f"\n📺 Stan {i}/{len(states)}: {state['name']}")
            print(f"   Status: {state['status']}")
            print(f"   Text: {state['text']}")
            print(f"   Flags: listening={state['is_listening']}, speaking={state['is_speaking']}")
            
            # Wyślij stan przez WebSocket
            message = {
                "type": "status",
                "data": state
            }
            
            try:
                await self.websocket_connection.send(json.dumps(message))
                print("   📤 Stan wysłany do overlay")
            except Exception as e:
                print(f"   ❌ Błąd wysyłania: {e}")
                break
            
            print("   ⏱️ Wyświetlam przez 5 sekund...")
            await asyncio.sleep(5)
        
        # Powrót do ready
        print(f"\n🔄 Powrót do stanu ready...")
        ready_message = {
            "type": "status", 
            "data": states[0]
        }
        await self.websocket_connection.send(json.dumps(ready_message))
    
    async def cleanup(self):
        """Wyczyść zasoby."""
        print("\n🧹 Sprzątam...")
        
        # Zamknij WebSocket
        if self.websocket_connection:
            await self.websocket_connection.close()
            print("🔌 WebSocket zamknięty")
        
        # Zatrzymaj overlay
        if self.overlay_process and self.overlay_process.poll() is None:
            self.overlay_process.terminate()
            await asyncio.sleep(2)
            if self.overlay_process.poll() is None:
                self.overlay_process.kill()
            print("🛑 Overlay zatrzymany")
        
        # Zatrzymaj klienta
        if self.client_process and self.client_process.poll() is None:
            self.client_process.terminate()
            await asyncio.sleep(3)
            if self.client_process.poll() is None:
                self.client_process.kill()
            print("🛑 Klient zatrzymany")


async def main():
    """Główna funkcja testu."""
    print("🎭 KOMPLETNY TEST OVERLAY + SYMULACJA STANÓW")
    print("=" * 70)
    print("Ten test uruchomi:")
    print("1. Serwer Docker (już powinien działać)")
    print("2. Klient z WebSocket")
    print("3. Overlay (ZAWSZE WIDOCZNY dla testów)")
    print("4. Symulację różnych stanów overlay")
    print("=" * 70)
    
    # Sprawdź serwer Docker
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if "gaja-assistant-server" not in result.stdout:
            print("❌ Serwer Docker nie działa!")
            print("Uruchom: python manage.py start-server")
            return
        print("✅ Serwer Docker działa")
    except:
        print("❌ Docker nie jest dostępny")
        return
    
    suite = OverlayTestSuite()
    
    try:
        # 1. Uruchom klienta
        client_ok = await suite.start_client()
        if not client_ok:
            return
        
        # 2. Uruchom overlay
        overlay_ok = await suite.start_overlay()
        if not overlay_ok:
            return
        
        print("\n🎉 Overlay powinien być teraz WIDOCZNY na ekranie!")
        print("Sprawdź czy widzisz overlay window przed kontynuowaniem")
        
        # Czekaj na potwierdzenie użytkownika
        # input("\nNaciśnij Enter gdy zobaczysz overlay na ekranie...")
        
        # 3. Połącz WebSocket
        ws_ok = await suite.connect_websocket()
        if not ws_ok:
            print("⚠️ WebSocket nie działa, ale overlay może używać HTTP fallback")
        
        # 4. Symuluj stany
        if ws_ok:
            await suite.simulate_overlay_states()
            print("\n🎉 Symulacja zakończona!")
        else:
            print("\n⚠️ Symulacja pominięta - brak WebSocket")
            print("Overlay powinien być widoczny i używać HTTP polling")
            await asyncio.sleep(30)  # Daj 30 sekund na obserwację
        
    except KeyboardInterrupt:
        print("\n⏸️ Test przerwany przez użytkownika")
    except Exception as e:
        print(f"\n❌ Błąd testu: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await suite.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

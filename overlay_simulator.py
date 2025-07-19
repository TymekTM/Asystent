#!/usr/bin/env python3
"""SYMULATOR OVERLAY - testuje różne stany overlay przez WebSocket."""

import asyncio
import json
import time
import websockets
import subprocess
from pathlib import Path


class OverlaySimulator:
    """Symulator stanów overlay."""
    
    def __init__(self):
        self.websocket = None
        self.client_process = None
        self.overlay_process = None
        
    async def start_client(self):
        """Uruchom klienta."""
        print("🚀 Uruchamiam klienta...")
        
        # Uruchom klienta w tle
        self.client_process = subprocess.Popen([
            "python", "-c", """
import asyncio
import sys
sys.path.insert(0, 'client')
from client_main import ClientApp

async def run_client():
    client = ClientApp()
    print('=== KLIENT URUCHOMIONY ===')
    await client.run()

try:
    asyncio.run(run_client())
except KeyboardInterrupt:
    print('Klient zatrzymany')
"""
        ], cwd="f:/Asystent")
        
        # Czekaj na uruchomienie
        await asyncio.sleep(10)
        
        if self.client_process.poll() is None:
            print("✅ Klient uruchomiony")
            return True
        else:
            print("❌ Klient nie uruchomił się")
            return False
    
    async def connect_to_client(self):
        """Połącz się z klientem przez WebSocket."""
        ports = [6001, 6000]
        
        for port in ports:
            try:
                ws_url = f"ws://localhost:{port}"
                print(f"🔌 Próbuję połączenie WebSocket: {ws_url}")
                
                self.websocket = await websockets.connect(ws_url)
                print(f"✅ Połączono z klientem na porcie {port}")
                return True
                
            except Exception as e:
                print(f"❌ Błąd połączenia z portem {port}: {e}")
                continue
        
        print("❌ Nie udało się połączyć z klientem")
        return False
    
    async def send_status_update(self, status_data):
        """Wyślij aktualizację statusu."""
        if not self.websocket:
            print("❌ Brak połączenia WebSocket")
            return False
        
        try:
            message = {
                "type": "status_update",
                "data": status_data
            }
            await self.websocket.send(json.dumps(message))
            print(f"📤 Wysłano: {status_data['status']}")
            return True
        except Exception as e:
            print(f"❌ Błąd wysyłania: {e}")
            return False
    
    async def simulate_overlay_states(self):
        """Symuluj różne stany overlay."""
        print("\n🎭 SYMULACJA STANÓW OVERLAY")
        print("=" * 50)
        
        # Lista stanów do symulacji (każdy przez 5 sekund)
        states = [
            {
                "status": "ready",
                "text": "Assistant gotowy",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True,
                "description": "Stan początkowy - gotowy"
            },
            {
                "status": "listening",
                "text": "Słucham...",
                "is_listening": True,
                "is_speaking": False,
                "wake_word_detected": True,
                "overlay_visible": True,
                "monitoring": True,
                "description": "Wykryto wake word - słuchanie"
            },
            {
                "status": "processing",
                "text": "Przetwarzam zapytanie...",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True,
                "description": "Przetwarzanie zapytania"
            },
            {
                "status": "speaking",
                "text": "Oto odpowiedź na Twoje pytanie...",
                "is_listening": False,
                "is_speaking": True,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True,
                "description": "Odpowiadanie - TTS aktywne"
            },
            {
                "status": "error",
                "text": "Wystąpił błąd połączenia",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": False,
                "description": "Stan błędu"
            },
            {
                "status": "offline",
                "text": "Tryb offline",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": False,
                "description": "Tryb offline - brak połączenia z serwerem"
            },
            {
                "status": "busy",
                "text": "Wykonuję zadanie w tle...",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True,
                "description": "Zajęty - zadanie w tle"
            },
            {
                "status": "idle",
                "text": "Bezczynny...",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "monitoring": True,
                "description": "Stan bezczynności"
            }
        ]
        
        for i, state in enumerate(states, 1):
            print(f"\n📺 Stan {i}/{len(states)}: {state['description']}")
            print(f"   Status: {state['status']}")
            print(f"   Text: {state['text']}")
            print(f"   Listening: {state['is_listening']}")
            print(f"   Speaking: {state['is_speaking']}")
            
            # Wyślij stan do overlay
            success = await self.send_status_update(state)
            if not success:
                print("❌ Nie udało się wysłać stanu")
                break
            
            # Pokaż stan przez 5 sekund
            print("⏱️ Wyświetlam przez 5 sekund...")
            await asyncio.sleep(5)
        
        # Powrót do stanu ready
        print(f"\n🔄 Powrót do stanu ready...")
        await self.send_status_update(states[0])  # ready state
    
    async def cleanup(self):
        """Oczyść zasoby."""
        print("\n🧹 Sprzątam...")
        
        # Zamknij WebSocket
        if self.websocket:
            await self.websocket.close()
            print("🔌 WebSocket zamknięty")
        
        # Zatrzymaj klienta
        if self.client_process and self.client_process.poll() is None:
            self.client_process.terminate()
            await asyncio.sleep(2)
            if self.client_process.poll() is None:
                self.client_process.kill()
            print("🛑 Klient zatrzymany")


async def main():
    """Główna funkcja symulatora."""
    print("🎭 SYMULATOR OVERLAY STATES")
    print("=" * 60)
    print("Ten skrypt symuluje różne stany overlay przez WebSocket")
    print("Każdy stan będzie wyświetlany przez 5 sekund")
    print("=" * 60)
    
    simulator = OverlaySimulator()
    
    try:
        # 1. Uruchom klienta
        client_ok = await simulator.start_client()
        if not client_ok:
            print("❌ Nie udało się uruchomić klienta")
            return
        
        # 2. Połącz się z klientem
        connected = await simulator.connect_to_client()
        if not connected:
            print("❌ Nie udało się połączyć z klientem")
            return
        
        print("\n✅ Wszystko gotowe! Overlay powinien być widoczny.")
        print("Naciśnij Ctrl+C aby przerwać symulację")
        
        # Czekaj chwilę na stabilizację
        await asyncio.sleep(3)
        
        # 3. Symuluj stany
        await simulator.simulate_overlay_states()
        
        print("\n🎉 Symulacja zakończona!")
        print("Overlay powinien pokazać wszystkie stany")
        
    except KeyboardInterrupt:
        print("\n⏸️ Symulacja przerwana przez użytkownika")
    except Exception as e:
        print(f"\n❌ Błąd symulacji: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await simulator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

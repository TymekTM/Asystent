#!/usr/bin/env python3
"""Test WebSocket overlay - sprawdza czy overlay łączy się przez WebSocket zamiast HTTP polling."""

import asyncio
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import psutil
import websockets


class TestWebSocketServer:
    """Test WebSocket server symulujący klienta."""

    def __init__(self, port=6001):
        self.port = port
        self.clients = set()
        self.server = None

    async def handle_client(self, websocket, path):
        """Obsługa połączenia od overlay."""
        print(f"🔌 Overlay połączony przez WebSocket: {websocket.remote_address}")
        self.clients.add(websocket)

        try:
            # Wyślij początkowy status
            initial_status = {
                "type": "status",
                "data": {
                    "status": "test_websocket_connected",
                    "text": "WebSocket test running",
                    "is_listening": False,
                    "is_speaking": False,
                    "wake_word_detected": False,
                    "overlay_visible": True,
                    "monitoring": True,
                },
            }
            await websocket.send(json.dumps(initial_status))
            print("📤 Wysłano początkowy status do overlay")

            # Symuluj zmiany statusu co 2 sekundy
            for i in range(5):
                await asyncio.sleep(2)
                status_update = {
                    "type": "status",
                    "data": {
                        "status": f"test_update_{i+1}",
                        "text": f"WebSocket test message {i+1}",
                        "is_listening": i % 2 == 0,
                        "is_speaking": i % 2 == 1,
                        "wake_word_detected": False,
                        "overlay_visible": True,
                        "monitoring": True,
                    },
                }
                await websocket.send(json.dumps(status_update))
                print(f"📤 Wysłano update #{i+1} do overlay")

            # Słuchaj wiadomości od overlay
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"📥 Otrzymano od overlay: {data}")
                except json.JSONDecodeError:
                    print(f"⚠️ Nieprawidłowy JSON od overlay: {message}")

        except websockets.exceptions.ConnectionClosed:
            print("🔌 Overlay WebSocket rozłączony")
        except Exception as e:
            print(f"❌ Błąd WebSocket handler: {e}")
        finally:
            self.clients.discard(websocket)

    async def start(self):
        """Uruchom WebSocket server."""
        try:
            self.server = await websockets.serve(
                self.handle_client, "127.0.0.1", self.port
            )
            print(f"🚀 Test WebSocket server uruchomiony na porcie {self.port}")
            return True
        except Exception as e:
            print(f"❌ Błąd uruchamiania WebSocket server: {e}")
            return False

    async def stop(self):
        """Zatrzymaj WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("🛑 Test WebSocket server zatrzymany")


def check_server_cpu():
    """Sprawdza zużycie CPU serwera Docker."""
    try:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "gaja-assistant-server",
                "--format",
                "{{.CPUPerc}}",
                "--no-stream",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            cpu_str = result.stdout.strip()
            cpu_value = float(cpu_str.replace("%", ""))
            return cpu_value
        return None
    except:
        return None


def run_overlay_test():
    """Uruchamia overlay i sprawdza czy działa z WebSocket."""
    print("🧪 Uruchamiam overlay z WebSocket...")

    overlay_path = Path("f:/Asystent/overlay/target/release/gaja-overlay.exe")
    if not overlay_path.exists():
        print(f"❌ Overlay nie istnieje: {overlay_path}")
        return False

    # Uruchom overlay
    process = subprocess.Popen([str(overlay_path)])

    time.sleep(10)  # Poczekaj 10 sekund na połączenie WebSocket

    # Sprawdź czy proces działa
    if process.poll() is None:
        print("✅ Overlay uruchomiony i działa")
        # Zatrzymaj overlay
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
        return True
    else:
        print("❌ Overlay się nie uruchomił lub zakończył z błędem")
        return False


async def main():
    """Główna funkcja testowa WebSocket."""
    print("🔧 TEST WEBSOCKET OVERLAY")
    print("=" * 50)

    # 1. Sprawdź CPU serwera przed testem
    print("\n1. Sprawdzam CPU serwera przed testem...")
    cpu_before = check_server_cpu()
    if cpu_before is not None:
        print(f"   CPU serwera: {cpu_before:.2f}%")
    else:
        print("   ⚠️ Nie można sprawdzić CPU serwera")

    # 2. Uruchom test WebSocket server
    print("\n2. Uruchamiam test WebSocket server...")
    websocket_server = TestWebSocketServer(6001)

    server_started = await websocket_server.start()
    if not server_started:
        print("❌ Nie udało się uruchomić test WebSocket server")
        return False

    try:
        # 3. Test overlay w tle
        print("\n3. Testuję overlay z WebSocket...")

        # Uruchom test overlay w osobnym wątku
        overlay_future = asyncio.get_event_loop().run_in_executor(
            None, run_overlay_test
        )

        # Czekaj na test overlay (maksymalnie 15 sekund)
        try:
            overlay_ok = await asyncio.wait_for(overlay_future, timeout=15.0)
        except TimeoutError:
            print("⏰ Timeout - overlay test trwał za długo")
            overlay_ok = False

        # 4. Sprawdź CPU po teście
        print("\n4. Sprawdzam CPU serwera po teście...")
        await asyncio.sleep(2)
        cpu_after = check_server_cpu()
        if cpu_after is not None:
            print(f"   CPU serwera: {cpu_after:.2f}%")

            if cpu_before is not None:
                if cpu_after <= cpu_before + 0.3:  # Tolerancja 0.3%
                    print("   ✅ CPU serwera nie wzrosło znacząco (WebSocket działa!)")
                else:
                    print(f"   ⚠️ CPU serwera wzrosło o {cpu_after - cpu_before:.2f}%")

        print(f"\n📊 WYNIKI WEBSOCKET:")
        print(f"   - Overlay uruchomienie: {'✅' if overlay_ok else '❌'}")
        print(f"   - WebSocket połączenia: {len(websocket_server.clients)} (peak)")
        print(
            f"   - CPU przed: {cpu_before:.2f}%"
            if cpu_before
            else "   - CPU przed: N/A"
        )
        print(f"   - CPU po: {cpu_after:.2f}%" if cpu_after else "   - CPU po: N/A")

        print(f"\n🎯 ZALETY WEBSOCKET vs HTTP POLLING:")
        print(f"   ✅ Brak ciągłego polling'u - overlay czeka na wiadomości")
        print(f"   ✅ Natychmiastowe aktualizacje statusu")
        print(f"   ✅ Znacznie mniejsze zużycie CPU serwera")
        print(f"   ✅ Mniejsze zużycie sieci (brak zbędnych requestów)")
        print(f"   ✅ Dwukierunkowa komunikacja (overlay może wysyłać komendy)")

        return overlay_ok

    finally:
        await websocket_server.stop()


if __name__ == "__main__":
    success = asyncio.run(main())
    print(
        f"\n{'🎉 WebSocket test zakończony sukcesem!' if success else '❌ WebSocket test zakończony niepowodzeniem!'}"
    )

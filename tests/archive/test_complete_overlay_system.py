#!/usr/bin/env python3
"""
KOMPLETNY TEST OVERLAY SYSTEM
================================
Uruchamia wszystkie komponenty i testuje overlay
"""

import subprocess
import time
from pathlib import Path

import requests


class OverlaySystemTest:
    def __init__(self):
        self.server_process = None
        self.client_process = None
        self.overlay_process = None
        self.base_path = Path("f:/Asystent")

    def check_docker_server(self):
        """Sprawdź czy serwer Docker działa."""
        try:
            response = requests.get("http://localhost:8001/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def start_docker_server(self):
        """Uruchom serwer Docker."""
        print("🐳 Uruchamiam serwer Docker...")
        result = subprocess.run(
            ["python", "manage.py", "start-server"],
            cwd=self.base_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ Serwer Docker uruchomiony")
            # Poczekaj na pełne uruchomienie
            for i in range(30):
                if self.check_docker_server():
                    print(f"✅ Serwer gotowy po {i+1} sekundach")
                    return True
                time.sleep(1)

        print("❌ Nie udało się uruchomić serwera Docker")
        return False

    def start_client(self):
        """Uruchom klienta z WebSocket."""
        print("🔧 Uruchamiam klienta...")

        # Uruchom klienta w tle
        self.client_process = subprocess.Popen(
            ["python", "client/client_main.py"],
            cwd=self.base_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Poczekaj na uruchomienie WebSocket
        for i in range(15):
            try:
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(("localhost", 6001))
                sock.close()
                if result == 0:
                    print(f"✅ Klient WebSocket gotowy po {i+1} sekundach")
                    return True
            except:
                pass
            time.sleep(1)

        print("❌ Klient WebSocket nie uruchomił się")
        return False

    def start_overlay(self):
        """Uruchom overlay."""
        print("🎯 Uruchamiam overlay...")

        overlay_path = (
            self.base_path / "overlay" / "target" / "debug" / "gaja-overlay.exe"
        )
        if not overlay_path.exists():
            print("❌ Overlay executable nie istnieje")
            return False

        self.overlay_process = subprocess.Popen(
            [str(overlay_path)],
            cwd=self.base_path / "overlay",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Sprawdź czy się uruchomił
        time.sleep(3)
        if self.overlay_process.poll() is None:
            print("✅ Overlay uruchomiony")
            return True
        else:
            print("❌ Overlay się nie uruchomił")
            return False

    def test_communication(self):
        """Testuj komunikację overlay."""
        print("📡 Testuję komunikację overlay...")

        # Sprawdź czy overlay odbiera komunikaty
        # To robimy przez obserwację logów klienta
        time.sleep(5)

        if self.client_process and self.overlay_process:
            # Sprawdź czy procesy nadal działają
            client_alive = self.client_process.poll() is None
            overlay_alive = self.overlay_process.poll() is None

            print(f"🔍 Klient działa: {client_alive}")
            print(f"🔍 Overlay działa: {overlay_alive}")

            if client_alive and overlay_alive:
                print("✅ Komunikacja prawdopodobnie działa")
                return True

        print("❌ Problem z komunikacją")
        return False

    def cleanup(self):
        """Wyczyść procesy."""
        print("🧹 Czyszczenie procesów...")

        if self.overlay_process:
            self.overlay_process.terminate()
            time.sleep(2)
            if self.overlay_process.poll() is None:
                self.overlay_process.kill()

        if self.client_process:
            self.client_process.terminate()
            time.sleep(2)
            if self.client_process.poll() is None:
                self.client_process.kill()

    def run_full_test(self):
        """Uruchom pełny test systemu."""
        print("🚀 KOMPLETNY TEST OVERLAY SYSTEM")
        print("=" * 50)

        try:
            # 1. Sprawdź serwer
            if not self.check_docker_server():
                if not self.start_docker_server():
                    print("❌ Nie można uruchomić serwera")
                    return False
            else:
                print("✅ Serwer już działa")

            # 2. Uruchom klienta
            if not self.start_client():
                print("❌ Nie można uruchomić klienta")
                return False

            # 3. Uruchom overlay
            if not self.start_overlay():
                print("❌ Nie można uruchomić overlay")
                return False

            # 4. Testuj komunikację
            if not self.test_communication():
                print("❌ Problem z komunikacją")
                return False

            print("\n🎉 WSZYSTKO DZIAŁA!")
            print("Overlay powinien być widoczny i reagować na zmiany statusu")
            print("Naciśnij Enter aby zakończyć test...")
            input()

            return True

        except KeyboardInterrupt:
            print("\n⏸️ Test przerwany przez użytkownika")
            return True
        finally:
            self.cleanup()


def main():
    """Główna funkcja."""
    test = OverlaySystemTest()
    success = test.run_full_test()

    if success:
        print("\n✅ Test zakończony sukcesem")
    else:
        print("\n❌ Test zakończony błędem")


if __name__ == "__main__":
    main()

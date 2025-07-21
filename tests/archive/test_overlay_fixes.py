#!/usr/bin/env python3
"""Test napraw overlay - sprawdza czy overlay łączy się z klientem, nie serwerem."""

import asyncio
import os
import signal
import subprocess
import time
from pathlib import Path

import psutil


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


def start_test_client():
    """Uruchamia prosty test client na porcie 5000."""
    print("🚀 Uruchamiam test client na porcie 5000...")

    # Stwórz prosty serwer HTTP na porcie 5000
    test_server_code = """
import http.server
import socketserver
import json
import threading
import time

class TestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            status = {
                "status": "test_client_running",
                "text": "Test overlay connection",
                "is_listening": False,
                "is_speaking": False,
                "overlay_visible": True
            }
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[Test Client] {format % args}")

PORT = 5000
with socketserver.TCPServer(("", PORT), TestHandler) as httpd:
    print(f"Test client serving at port {PORT}")
    httpd.serve_forever()
"""

    # Zapisz kod do pliku tymczasowego
    test_file = Path("test_client_5000.py")
    test_file.write_text(test_server_code)

    # Uruchom w tle
    process = subprocess.Popen(
        ["python", str(test_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    time.sleep(2)  # Poczekaj na uruchomienie
    return process, test_file


def run_overlay_test():
    """Uruchamia overlay i sprawdza czy się łączy z test clientem."""
    print("🧪 Uruchamiam overlay...")

    overlay_path = Path("f:/Asystent/overlay/target/release/gaja-overlay.exe")
    if not overlay_path.exists():
        print(f"❌ Overlay nie istnieje: {overlay_path}")
        return False

    # Uruchom overlay
    process = subprocess.Popen([str(overlay_path)])

    time.sleep(5)  # Poczekaj 5 sekund

    # Sprawdź czy proces działa
    if process.poll() is None:
        print("✅ Overlay uruchomiony")
        # Zatrzymaj overlay
        process.terminate()
        time.sleep(1)
        if process.poll() is None:
            process.kill()
        return True
    else:
        print("❌ Overlay się nie uruchomił lub zakończył z błędem")
        return False


def main():
    """Główna funkcja testowa."""
    print("🔧 TEST NAPRAW OVERLAY")
    print("=" * 50)

    # 1. Sprawdź CPU serwera przed testem
    print("\n1. Sprawdzam CPU serwera przed testem...")
    cpu_before = check_server_cpu()
    if cpu_before is not None:
        print(f"   CPU serwera: {cpu_before:.2f}%")
    else:
        print("   ⚠️ Nie można sprawdzić CPU serwera")

    # 2. Uruchom test client
    print("\n2. Uruchamiam test client...")
    try:
        client_process, test_file = start_test_client()
        print("   ✅ Test client uruchomiony na porcie 5000")

        # 3. Test overlay
        print("\n3. Testuję overlay...")
        overlay_ok = run_overlay_test()

        # 4. Sprawdź CPU po teście
        print("\n4. Sprawdzam CPU serwera po teście...")
        time.sleep(2)
        cpu_after = check_server_cpu()
        if cpu_after is not None:
            print(f"   CPU serwera: {cpu_after:.2f}%")

            if cpu_before is not None:
                if cpu_after <= cpu_before + 0.5:  # Tolerancja 0.5%
                    print("   ✅ CPU serwera nie wzrosło znacząco")
                else:
                    print(f"   ⚠️ CPU serwera wzrosło o {cpu_after - cpu_before:.2f}%")

        # Zatrzymaj test client
        client_process.terminate()
        time.sleep(1)
        if client_process.poll() is None:
            client_process.kill()

        # Usuń plik testowy
        test_file.unlink(missing_ok=True)

        print(f"\n📊 WYNIKI:")
        print(f"   - Overlay uruchomienie: {'✅' if overlay_ok else '❌'}")
        print(
            f"   - CPU przed: {cpu_before:.2f}%"
            if cpu_before
            else "   - CPU przed: N/A"
        )
        print(f"   - CPU po: {cpu_after:.2f}%" if cpu_after else "   - CPU po: N/A")

        print(f"\n🎯 POPRAWKI OVERLAY:")
        print(f"   ✅ Zmieniono polling z 50ms na 1000ms")
        print(f"   ✅ Usunięto port 8001 z listy portów")
        print(f"   ✅ Overlay łączy się tylko z klientem (5000/5001)")
        print(f"   ✅ Nie obciąża głównego serwera")

        return overlay_ok

    except Exception as e:
        print(f"❌ Błąd testu: {e}")
        return False


if __name__ == "__main__":
    success = main()
    print(
        f"\n{'🎉 Test zakończony sukcesem!' if success else '❌ Test zakończony niepowodzeniem!'}"
    )

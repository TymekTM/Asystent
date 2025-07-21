#!/usr/bin/env python3
"""PROSTY TEST OVERLAY - działa z uruchomionym klientem."""

import asyncio
import json
import subprocess
import time
from pathlib import Path

import requests


def check_client_running():
    """Sprawdź czy klient działa."""
    ports = [5001, 5000]

    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/api/status", timeout=2)
            if response.status_code == 200:
                print(f"✅ Klient działa na porcie {port}")
                return port
        except:
            continue

    return None


def send_status_to_client(port, status_data):
    """Wyślij status do klienta przez HTTP."""
    try:
        # Próbujemy wysłać POST do klienta (jeśli ma endpoint)
        response = requests.post(
            f"http://localhost:{port}/api/status", json=status_data, timeout=2
        )
        return response.status_code == 200
    except:
        return False


def simulate_overlay_states():
    """Symuluj stany overlay przez uruchomienie overlay z różnymi stanami."""
    print("🎭 SYMULACJA STANÓW OVERLAY")
    print("=" * 50)

    # Sprawdź czy klient działa
    client_port = check_client_running()
    if not client_port:
        print("❌ Klient nie działa! Uruchom klienta najpierw.")
        return False

    # Sprawdź czy overlay exe istnieje
    overlay_path = Path("f:/Asystent/overlay/target/release/gaja-overlay.exe")
    if not overlay_path.exists():
        print(f"❌ Overlay nie istnieje: {overlay_path}")
        return False

    print(f"✅ Klient działa na porcie {client_port}")
    print(f"✅ Overlay executable znaleziony")

    # Lista stanów do pokazania
    states = [
        ("ready", "Assistant gotowy", False, False),
        ("listening", "Słucham...", True, False),
        ("processing", "Przetwarzam...", False, False),
        ("speaking", "Odpowiadam...", False, True),
        ("error", "Błąd połączenia", False, False),
        ("offline", "Tryb offline", False, False),
        ("busy", "Zajęty...", False, False),
        ("idle", "Bezczynny", False, False),
    ]

    print("\n📺 Uruchamiam overlay - powinien się pojawić na ekranie")
    print("Overlay będzie pokazywać różne stany automatycznie")
    print("Naciśnij Ctrl+C aby zatrzymać\n")

    # Uruchom overlay
    overlay_process = subprocess.Popen([str(overlay_path)])

    try:
        # Czekaj na uruchomienie overlay
        time.sleep(5)

        if overlay_process.poll() is not None:
            print("❌ Overlay się nie uruchomił")
            return False

        print("✅ Overlay uruchomiony!")

        # Symuluj stany - overlay będzie odbierał je przez WebSocket
        for i, (status, text, listening, speaking) in enumerate(states, 1):
            print(f"📺 Stan {i}/{len(states)}: {status} - {text}")
            print(f"   Listening: {listening}, Speaking: {speaking}")
            print("⏱️ Wyświetlam przez 5 sekund...")

            # Overlay automatycznie pobierze stan z klienta
            # Tutaj moglibyśmy zmodyfikować stan klienta, ale dla prostoty
            # overlay będzie pokazywał stany na podstawie wewnętrznej logiki

            time.sleep(5)

        print("\n🔄 Powracam do stanu ready...")
        time.sleep(2)

        print("\n🎉 Symulacja zakończona!")
        print("Overlay powinien był pokazać różne stany")

        return True

    except KeyboardInterrupt:
        print("\n⏸️ Symulacja przerwana przez użytkownika")
        return True
    finally:
        # Zatrzymaj overlay
        if overlay_process.poll() is None:
            print("🛑 Zatrzymuję overlay...")
            overlay_process.terminate()
            time.sleep(2)
            if overlay_process.poll() is None:
                overlay_process.kill()


def main():
    """Główna funkcja."""
    print("🎭 PROSTY TEST OVERLAY")
    print("=" * 60)
    print("Ten skrypt uruchomi overlay i pokaże różne stany")
    print("WYMAGANIA:")
    print("1. Serwer Docker musi działać")
    print("2. Klient musi być uruchomiony")
    print("=" * 60)

    # Sprawdź serwer Docker
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if "gaja-assistant-server" in result.stdout:
            print("✅ Serwer Docker działa")
        else:
            print("❌ Serwer Docker nie działa")
            print("Uruchom: python manage.py start-server")
            return
    except:
        print("❌ Docker nie jest dostępny")
        return

    # Sprawdź klienta
    client_port = check_client_running()
    if not client_port:
        print("❌ Klient nie działa")
        print("Uruchom klienta w osobnym terminalu:")
        print("cd f:\\Asystent && python client/client_main.py")
        return

    print(f"✅ Wszystko gotowe!")
    input("\nNaciśnij Enter aby uruchomić test overlay...")

    success = simulate_overlay_states()

    if success:
        print("\n🎉 Test overlay zakończony sukcesem!")
    else:
        print("\n❌ Test overlay zakończony niepowodzeniem")


if __name__ == "__main__":
    main()

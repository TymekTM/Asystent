#!/usr/bin/env python3
"""DIAGNOSTYKA OVERLAY - sprawdza dlaczego overlay się nie wyświetla."""

import subprocess
import time
import asyncio
import websockets
import json
from pathlib import Path


async def test_websocket_connection():
    """Test połączenia WebSocket z klientem."""
    print("🔌 Testuję połączenie WebSocket...")
    
    ports = [6001, 6000]
    
    for port in ports:
        try:
            ws_url = f"ws://localhost:{port}"
            print(f"   Próbuję: {ws_url}")
            
            websocket = await websockets.connect(ws_url)
            print(f"   ✅ Połączono z portem {port}")
            
            # Wyślij test message
            test_message = {
                "type": "status",
                "data": {
                    "status": "test_overlay_visible",
                    "text": "TEST - Overlay powinien być widoczny!",
                    "is_listening": True,
                    "is_speaking": False,
                    "wake_word_detected": True,
                    "overlay_visible": True,
                    "monitoring": True,
                }
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"   📤 Wysłano test message")
            
            await websocket.close()
            return True
            
        except Exception as e:
            print(f"   ❌ Port {port}: {e}")
            continue
    
    print("   ❌ Nie udało się połączyć z WebSocket")
    return False


def test_overlay_visibility():
    """Test czy overlay jest widoczny."""
    print("👁️ Testuję widoczność overlay...")
    
    overlay_path = Path("f:/Asystent/overlay/target/release/gaja-overlay.exe")
    if not overlay_path.exists():
        print(f"   ❌ Overlay nie istnieje: {overlay_path}")
        return False
    
    print(f"   ✅ Overlay executable istnieje")
    
    # Uruchom overlay z logami
    print("   🚀 Uruchamiam overlay z logami...")
    
    # Uruchom overlay i przechwyć output
    process = subprocess.Popen([
        str(overlay_path)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Czekaj 10 sekund
    time.sleep(10)
    
    if process.poll() is None:
        print("   ✅ Overlay process działa")
        
        # Sprawdź output
        try:
            stdout, stderr = process.communicate(timeout=2)
            if stdout:
                print(f"   📜 STDOUT:\n{stdout}")
            if stderr:
                print(f"   📜 STDERR:\n{stderr}")
        except subprocess.TimeoutExpired:
            print("   ⏰ Process nadal działa (to dobrze)")
        
        # Zatrzymaj process
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
        
        return True
    else:
        print("   ❌ Overlay process zakończył się")
        stdout, stderr = process.communicate()
        if stdout:
            print(f"   📜 STDOUT:\n{stdout}")
        if stderr:
            print(f"   📜 STDERR:\n{stderr}")
        return False


def check_client_status():
    """Sprawdź status klienta."""
    print("🔍 Sprawdzam status klienta...")
    
    try:
        import requests
        response = requests.get("http://localhost:5001/api/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Klient odpowiada")
            print(f"   📊 Status: {data.get('status', 'unknown')}")
            print(f"   📊 Text: {data.get('text', 'brak')}")
            print(f"   📊 Overlay visible: {data.get('overlay_visible', 'unknown')}")
            print(f"   📊 Monitoring: {data.get('monitoring', 'unknown')}")
            return True
        else:
            print(f"   ❌ Klient błąd: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Klient niedostępny: {e}")
        return False


async def main():
    """Główna funkcja diagnostyczna."""
    print("🔧 DIAGNOSTYKA OVERLAY")
    print("=" * 50)
    
    # 1. Sprawdź klienta
    client_ok = check_client_status()
    
    # 2. Test WebSocket
    if client_ok:
        websocket_ok = await test_websocket_connection()
    else:
        websocket_ok = False
    
    # 3. Test overlay
    overlay_ok = test_overlay_visibility()
    
    print("\n" + "=" * 50)
    print("📊 WYNIKI DIAGNOSTYKI")
    print("=" * 50)
    print(f"Klient HTTP API: {'✅' if client_ok else '❌'}")
    print(f"WebSocket połączenie: {'✅' if websocket_ok else '❌'}")
    print(f"Overlay process: {'✅' if overlay_ok else '❌'}")
    
    if client_ok and websocket_ok and overlay_ok:
        print("\n🎉 Wszystko działa - overlay powinien być widoczny!")
        print("\n💡 MOŻLIWE PRZYCZYNY NIEWIDOCZNOŚCI:")
        print("1. Overlay jest na innym monitorze")
        print("2. Overlay jest minimalizowany")
        print("3. Overlay jest ukryty za innymi oknami")
        print("4. Overlay jest przezroczysty/nie renderuje się")
        print("5. Problem z GUI framework (Tauri)")
    else:
        print("\n❌ Znaleziono problemy:")
        if not client_ok:
            print("- Klient nie działa lub nie odpowiada")
        if not websocket_ok:
            print("- WebSocket nie łączy się z klientem")
        if not overlay_ok:
            print("- Overlay process nie uruchamia się")
    
    print("\n🔧 SUGEROWANE NAPRAWY:")
    print("1. Sprawdź czy overlay ma focus/jest na wierzchu")
    print("2. Sprawdź monitor/rozdzielczość")
    print("3. Sprawdź czy Tauri GUI działa poprawnie")
    print("4. Sprawdź czy overlay nie jest ukryty w system tray")


if __name__ == "__main__":
    asyncio.run(main())

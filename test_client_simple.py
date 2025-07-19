#!/usr/bin/env python3
"""
Test klienta bez wakeword detectora
Sprawdza czy WebSocket serwer uruchamia się poprawnie
"""

import asyncio
import websockets
import json
import subprocess
import time
import os
from pathlib import Path

async def test_client_websocket():
    """Test WebSocket klienta"""
    print("🔌 Testowanie WebSocket klienta na porcie 6001...")
    
    attempts = 5
    for attempt in range(attempts):
        try:
            async with websockets.connect("ws://localhost:6001", timeout=5) as websocket:
                print(f"✅ Połączenie z klientem WebSocket udane (próba {attempt + 1})")
                
                # Wyślij test message
                test_message = {
                    "type": "status_update",
                    "status": "testing",
                    "text": "Test komunikacji",
                    "is_listening": False,
                    "is_speaking": False,
                    "wake_word_detected": False,
                    "overlay_visible": True,
                    "monitoring": True
                }
                
                await websocket.send(json.dumps(test_message))
                print("📤 Wiadomość testowa wysłana")
                
                return True
                
        except Exception as e:
            print(f"❌ Próba {attempt + 1}/{attempts} - błąd: {e}")
            if attempt < attempts - 1:
                print("⏳ Czekam 3 sekundy...")
                await asyncio.sleep(3)
    
    return False

def start_client_test():
    """Uruchom klienta z testową konfiguracją"""
    print("🚀 Uruchamianie klienta bez wakeword...")
    
    # Skopiuj testową konfigurację
    test_config_path = Path("f:/Asystent/client_config_test.json")
    client_config_path = Path("f:/Asystent/client/client_config.json")
    
    # Backup oryginalnej konfiguracji
    backup_path = Path("f:/Asystent/client/client_config.json.backup")
    if not backup_path.exists() and client_config_path.exists():
        print("💾 Tworzę backup oryginalnej konfiguracji...")
        import shutil
        shutil.copy2(client_config_path, backup_path)
    
    # Skopiuj testową konfigurację
    import shutil
    shutil.copy2(test_config_path, client_config_path)
    print("📋 Skopiowano testową konfigurację")
    
    try:
        # Uruchom klienta
        os.chdir("f:/Asystent")
        process = subprocess.Popen(
            ["python", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        print("⏳ Czekam na uruchomienie klienta...")
        print("📋 Logi klienta:")
        
        # Pokaż pierwsze linie logów
        for _ in range(20):
            try:
                line = process.stdout.readline()
                if line:
                    print(f"  📝 {line.strip()}")
                else:
                    break
            except:
                break
        
        time.sleep(5)
        
        return process
        
    except Exception as e:
        print(f"❌ Błąd uruchamiania klienta: {e}")
        return None

async def main():
    """Główna funkcja testowa"""
    print("=" * 60)
    print("🧪 TEST KLIENTA BEZ WAKEWORD DETECTORA")
    print("=" * 60)
    
    # Uruchom klienta
    client_process = start_client_test()
    if not client_process:
        print("❌ Nie można uruchomić klienta")
        return False
    
    try:
        # Test WebSocket
        success = await test_client_websocket()
        
        if success:
            print("\n🎉 SUCCESS! Klient WebSocket działa poprawnie!")
        else:
            print("\n❌ FAILED! Klient WebSocket nie działa")
        
        return success
        
    finally:
        # Zakończ proces klienta
        if client_process:
            print("🛑 Zatrzymuję klienta...")
            client_process.terminate()
            try:
                client_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                client_process.kill()
        
        # Przywróć oryginalną konfigurację
        backup_path = Path("f:/Asystent/client/client_config.json.backup")
        client_config_path = Path("f:/Asystent/client/client_config.json")
        if backup_path.exists():
            print("🔄 Przywracam oryginalną konfigurację...")
            import shutil
            shutil.copy2(backup_path, client_config_path)

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test przerwany przez użytkownika")
        exit(1)

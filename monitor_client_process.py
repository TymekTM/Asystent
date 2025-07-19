#!/usr/bin/env python3
"""
Monitor procesu klienta - sprawdza dlaczego klient się zamyka
"""

import subprocess
import time
import sys
import os
import psutil
from pathlib import Path

def monitor_client_process():
    """Monitoruj proces klienta i pokaż dlaczego się kończy"""
    print("🔍 MONITOR PROCESU KLIENTA")
    print("=" * 50)
    
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
        
        print(f"🚀 Klient uruchomiony, PID: {process.pid}")
        
        # Monitoruj proces przez 30 sekund
        start_time = time.time()
        output_lines = []
        websocket_started = False
        
        while time.time() - start_time < 30:
            # Sprawdź czy proces nadal działa
            poll = process.poll()
            if poll is not None:
                print(f"❌ Proces klienta zakończył się z kodem: {poll}")
                break
            
            # Czytaj output
            try:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    print(f"📝 {line.strip()}")
                    
                    # Sprawdź kluczowe wydarzenia
                    if "WebSocket server started on port 6001" in line:
                        websocket_started = True
                        print("✅ WebSocket server wystartował!")
                    
                    if "Error" in line or "ERROR" in line:
                        print(f"🔴 BŁĄD: {line.strip()}")
                    
                    if "Exception" in line:
                        print(f"💥 WYJĄTEK: {line.strip()}")
                        
            except:
                pass
            
            time.sleep(0.1)
        else:
            print("⏰ Timeout 30 sekund - proces nadal działa")
            if websocket_started:
                print("✅ WebSocket server uruchomiony pomyślnie")
                
                # Test połączenia
                import asyncio
                import websockets
                
                async def test_connection():
                    try:
                        async with websockets.connect("ws://localhost:6001", timeout=5) as ws:
                            print("✅ Połączenie WebSocket udane!")
                            return True
                    except Exception as e:
                        print(f"❌ Błąd połączenia WebSocket: {e}")
                        return False
                
                result = asyncio.run(test_connection())
                if result:
                    print("🎉 SUCCESS! System działa poprawnie!")
            else:
                print("❌ WebSocket server nie wystartował")
        
        # Zakończ proces
        if process.poll() is None:
            print("🛑 Zatrzymuję proces klienta...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        return websocket_started
        
    except Exception as e:
        print(f"💥 Błąd monitorowania: {e}")
        return False

def check_process_resources():
    """Sprawdź zasoby systemu"""
    print("\n🔍 SPRAWDZANIE ZASOBÓW SYSTEMU")
    print("=" * 50)
    
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"💻 CPU: {cpu_percent}%")
        
        # Memory usage  
        memory = psutil.virtual_memory()
        print(f"🧠 RAM: {memory.percent}% używane ({memory.available // 1024 // 1024} MB dostępne)")
        
        # Disk usage
        disk = psutil.disk_usage('C:')
        print(f"💾 Dysk C: {disk.percent}% używane")
        
        # Check if ports are busy
        connections = psutil.net_connections()
        ports_in_use = [conn.laddr.port for conn in connections if conn.laddr]
        
        critical_ports = [5001, 6001, 8001]
        for port in critical_ports:
            if port in ports_in_use:
                print(f"⚠️  Port {port} jest zajęty")
            else:
                print(f"✅ Port {port} jest wolny")
                
    except Exception as e:
        print(f"❌ Błąd sprawdzania zasobów: {e}")

def main():
    """Główna funkcja"""
    print("🔬 DIAGNOSTYKA PROCESU KLIENTA GAJA")
    print("=" * 60)
    
    check_process_resources()
    result = monitor_client_process()
    
    print("\n" + "=" * 60)
    if result:
        print("🎉 SUKCES - Klient uruchomił WebSocket poprawnie")
    else:
        print("❌ BŁĄD - Klient nie uruchomił WebSocket lub się zamknął")
    print("=" * 60)
    
    return result

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring przerwany")
        sys.exit(1)

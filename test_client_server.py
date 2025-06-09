#!/usr/bin/env python3
"""
test_client_server.py
Skrypt do testowania komunikacji klient-serwer
"""

import asyncio
import json
import sys
from pathlib import Path
import subprocess
import time

def start_server():
    """Uruchom serwer w tle."""
    print("🚀 Starting server...")
    server_dir = Path("server")
    
    try:
        # Uruchom serwer w tle
        server_process = subprocess.Popen([
            sys.executable, "server_main.py"
        ], cwd=server_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Poczekaj chwilę na uruchomienie serwera
        time.sleep(3)
        
        print("✅ Server started (PID: {})".format(server_process.pid))
        return server_process
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def start_client():
    """Uruchom klienta."""
    print("🚀 Starting client...")
    client_dir = Path("client")
    
    try:
        # Uruchom klienta
        client_process = subprocess.Popen([
            sys.executable, "client_main.py"
        ], cwd=client_dir)
        
        print("✅ Client started (PID: {})".format(client_process.pid))
        return client_process
        
    except Exception as e:
        print(f"❌ Failed to start client: {e}")
        return None

def main():
    """Główna funkcja testowa."""
    print("🧪 GAJA Client-Server Test")
    print("=" * 40)
    
    server_process = None
    client_process = None
    
    try:
        # Uruchom serwer
        server_process = start_server()
        if not server_process:
            return
        
        # Uruchom klienta
        client_process = start_client()
        if not client_process:
            return
        
        print("\n🎉 Both server and client are running!")
        print("Press Ctrl+C to stop both processes...")
        
        # Czekaj na zakończenie
        client_process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping processes...")
        
    finally:
        # Zatrzymaj procesy
        if client_process:
            try:
                client_process.terminate()
                client_process.wait(timeout=5)
                print("✅ Client stopped")
            except:
                client_process.kill()
                print("🔪 Client killed")
        
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
                print("✅ Server stopped")
            except:
                server_process.kill()
                print("🔪 Server killed")
    
    print("🏁 Test completed")

if __name__ == "__main__":
    main()

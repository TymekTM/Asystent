#!/usr/bin/env python3
"""
QUICK OVERLAY TEST
==================
Szybki test czy overlay system działa poprawnie
"""

import subprocess
import socket
import requests
import time
import sys

def check_port(port):
    """Check if port is listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(('localhost', port))
            return True
        except (ConnectionRefusedError, OSError):
            return False

def check_docker():
    """Check Docker server."""
    try:
        response = requests.get("http://localhost:8001/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def check_overlay_process():
    """Check if overlay process is running."""
    try:
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        return 'gaja-overlay.exe' in result.stdout
    except:
        return False

def main():
    """Quick system check."""
    print("🔍 QUICK OVERLAY SYSTEM CHECK")
    print("=" * 40)
    
    # Check Docker server
    docker_ok = check_docker()
    print(f"🐳 Docker Server (8001): {'✅ OK' if docker_ok else '❌ NOT RUNNING'}")
    
    # Check Client WebSocket
    ws_6001 = check_port(6001)
    ws_6000 = check_port(6000)
    ws_ok = ws_6001 or ws_6000
    active_port = 6001 if ws_6001 else (6000 if ws_6000 else None)
    print(f"🔧 Client WebSocket: {'✅ OK on port ' + str(active_port) if ws_ok else '❌ NOT RUNNING'}")
    
    # Check overlay process
    overlay_ok = check_overlay_process()
    print(f"🎯 Overlay Process: {'✅ RUNNING' if overlay_ok else '❌ NOT RUNNING'}")
    
    # Overall status
    all_ok = docker_ok and ws_ok and overlay_ok
    print("\n" + "=" * 40)
    if all_ok:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print("Overlay should be working correctly.")
        print("\nTo test overlay statuses:")
        print("  python overlay_tester.py")
    else:
        print("⚠️ SOME ISSUES DETECTED")
        print("\nTo fix automatically:")
        print("  python overlay_launcher.py")
        
        if not docker_ok:
            print("\nTo start Docker manually:")
            print("  python manage.py start-server")
        
        if not ws_ok:
            print("\nTo start client manually:")
            print("  python client/client_main.py")
        
        if not overlay_ok:
            print("\nTo start overlay manually:")
            print("  cd overlay && cargo run")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

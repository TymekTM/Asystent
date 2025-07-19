#!/usr/bin/env python3
"""
GAJA OVERLAY LAUNCHER
====================
Kompletny launcher dla systemu overlay z automatyczną kolejnością uruchamiania
"""

import asyncio
import subprocess
import time
import requests
import json
import socket
import signal
import sys
from pathlib import Path
from typing import Optional, List

class GajaOverlayLauncher:
    def __init__(self):
        self.base_path = Path("f:/Asystent")
        self.processes = {}
        self.running = True
        
        # Setup signal handlers for cleanup
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle interrupt signals."""
        print(f"\n🛑 Received signal {sig}, shutting down...")
        self.running = False
        self.cleanup_all()
        sys.exit(0)
    
    def check_port(self, port: int) -> bool:
        """Check if port is available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect(('localhost', port))
                return True
            except (ConnectionRefusedError, OSError):
                return False
    
    def wait_for_port(self, port: int, timeout: int = 30) -> bool:
        """Wait for port to become available."""
        print(f"⏳ Waiting for port {port}...")
        for _ in range(timeout):
            if self.check_port(port):
                print(f"✅ Port {port} is ready")
                return True
            time.sleep(1)
        print(f"❌ Timeout waiting for port {port}")
        return False
    
    def check_docker_server(self) -> bool:
        """Check if Docker server is running."""
        try:
            response = requests.get("http://localhost:8001/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_docker_server(self) -> bool:
        """Start Docker server."""
        if self.check_docker_server():
            print("✅ Docker server already running")
            return True
        
        print("🐳 Starting Docker server...")
        try:
            process = subprocess.Popen(
                ["python", "manage.py", "start-server"],
                cwd=self.base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes['docker'] = process
            
            # Wait for server to be ready
            if self.wait_for_port(8001, timeout=60):
                print("✅ Docker server started successfully")
                return True
            else:
                print("❌ Docker server failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error starting Docker server: {e}")
            return False
    
    def start_client(self) -> bool:
        """Start Python client with WebSocket."""
        print("🔧 Starting Python client...")
        try:
            process = subprocess.Popen(
                ["python", "client/client_main.py"],
                cwd=self.base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes['client'] = process
            
            # Wait for WebSocket to be ready on 6001 or 6000
            if self.wait_for_port(6001, timeout=15) or self.wait_for_port(6000, timeout=5):
                print("✅ Client WebSocket started successfully")
                return True
            else:
                print("❌ Client WebSocket failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error starting client: {e}")
            return False
    
    def build_overlay(self) -> bool:
        """Build overlay if needed."""
        overlay_exe = self.base_path / "overlay" / "target" / "debug" / "gaja-overlay.exe"
        if overlay_exe.exists():
            print("✅ Overlay executable exists")
            return True
        
        print("🔨 Building overlay...")
        try:
            result = subprocess.run(
                ["cargo", "build"],
                cwd=self.base_path / "overlay",
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and overlay_exe.exists():
                print("✅ Overlay built successfully")
                return True
            else:
                print(f"❌ Overlay build failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Overlay build timed out")
            return False
        except Exception as e:
            print(f"❌ Error building overlay: {e}")
            return False
    
    def start_overlay(self) -> bool:
        """Start Tauri overlay."""
        if not self.build_overlay():
            return False
        
        print("🎯 Starting Tauri overlay...")
        try:
            overlay_exe = self.base_path / "overlay" / "target" / "debug" / "gaja-overlay.exe"
            process = subprocess.Popen(
                [str(overlay_exe)],
                cwd=self.base_path / "overlay",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes['overlay'] = process
            
            # Give overlay time to start and connect
            time.sleep(5)
            
            if process.poll() is None:
                print("✅ Overlay started successfully")
                return True
            else:
                print("❌ Overlay failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error starting overlay: {e}")
            return False
    
    def check_system_health(self) -> dict:
        """Check health of all components."""
        health = {
            'docker': self.check_docker_server(),
            'client_ws': self.check_port(6001) or self.check_port(6000),
            'overlay': self.processes.get('overlay') and self.processes['overlay'].poll() is None
        }
        return health
    
    def print_status(self):
        """Print current system status."""
        health = self.check_system_health()
        print("\n📊 SYSTEM STATUS:")
        print("=" * 40)
        print(f"🐳 Docker Server: {'✅ RUNNING' if health['docker'] else '❌ STOPPED'}")
        print(f"🔧 Client WebSocket: {'✅ RUNNING' if health['client_ws'] else '❌ STOPPED'}")
        print(f"🎯 Overlay: {'✅ RUNNING' if health['overlay'] else '❌ STOPPED'}")
        
        if all(health.values()):
            print("\n🎉 ALL SYSTEMS OPERATIONAL!")
            print("Overlay should be visible and responding to status changes")
        else:
            print("\n⚠️ Some components are not running")
    
    def cleanup_all(self):
        """Clean up all processes."""
        print("🧹 Cleaning up processes...")
        
        for name, process in self.processes.items():
            if process and process.poll() is None:
                print(f"🛑 Stopping {name}...")
                try:
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        process.kill()
                except:
                    pass
        
        self.processes.clear()
        print("✅ Cleanup completed")
    
    def launch_full_system(self) -> bool:
        """Launch complete overlay system."""
        print("🚀 GAJA OVERLAY SYSTEM LAUNCHER")
        print("=" * 50)
        
        try:
            # Step 1: Start Docker server
            if not self.start_docker_server():
                print("❌ Failed to start Docker server")
                return False
            
            # Step 2: Start client with WebSocket
            if not self.start_client():
                print("❌ Failed to start client")
                return False
            
            # Step 3: Start overlay
            if not self.start_overlay():
                print("❌ Failed to start overlay")
                return False
            
            # System is ready
            self.print_status()
            
            # Monitor system
            print("\n🔍 Monitoring system... (Press Ctrl+C to stop)")
            try:
                while self.running:
                    time.sleep(10)
                    if not all(self.check_system_health().values()):
                        print("⚠️ System health check failed")
                        self.print_status()
                        break
            except KeyboardInterrupt:
                pass
            
            return True
            
        except Exception as e:
            print(f"❌ System launch failed: {e}")
            return False
        finally:
            self.cleanup_all()

def main():
    """Main function."""
    launcher = GajaOverlayLauncher()
    success = launcher.launch_full_system()
    
    if success:
        print("\n✅ Overlay system launched successfully")
    else:
        print("\n❌ Overlay system launch failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

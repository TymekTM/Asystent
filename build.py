#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAJA Assistant Build Script - Client-Server Architecture
Builds separate executables for server and client components.
"""

import sys
import os
import subprocess
import shutil
import argparse
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def run_command(cmd, description=""):
    """Run a command and handle errors gracefully."""
    print(f"[BUILD] {description}")
    print(f"   Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   [ERROR] Error: {e}")
        if e.stdout:
            print(f"   Stdout: {e.stdout}")
        if e.stderr:
            print(f"   Stderr: {e.stderr}")
        return False

def check_dependencies():
    """Check and install build dependencies."""
    print("[CHECK] Checking build dependencies...")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"   [OK] PyInstaller {PyInstaller.__version__} is available")
    except ImportError:
        print("   [BUILD] Installing PyInstaller...")
        if not run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], "Installing PyInstaller"):
            return False
    
    return True

def build_overlay():
    """Build the Rust overlay if available."""
    overlay_dir = Path("overlay")
    if not overlay_dir.exists():
        print("   [WARN] Overlay directory not found, skipping...")
        return True
    
    print("[RUST] Building Rust overlay...")
    if not run_command(["cargo", "build", "--release"], "Building Rust overlay"):
        print("   [WARN] Overlay build failed, continuing without it...")
        return False
    
    return True

def clean_build():
    """Clean previous build artifacts."""
    print("[CLEAN] Cleaning previous build artifacts...")
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"   Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Remove .spec cache files
    for spec_file in Path(".").glob("*.spec"):
        spec_cache = spec_file.with_suffix(".spec.bak")
        if spec_cache.exists():
            spec_cache.unlink()

def build_component(component):
    """Build a specific component (client or legacy only - server uses Docker)."""
    if component == "client":
        spec_file = "gaja_client.spec"
        exe_name = "GajaClient.exe" 
        description = "client component (plug-and-play with runtime dependencies)"
    elif component == "legacy":
        spec_file = "gaja.spec"
        exe_name = "Gaja.exe"
        description = "legacy unified component"
    else:
        print(f"[ERROR] Unknown component: {component}")
        print("[INFO] Server should be run via Docker: docker-compose up gaja-server-cpu")
        return False
    
    print(f"[BUILD] Building {description} using PyInstaller...")
    
    if not os.path.exists(spec_file):
        print(f"   [ERROR] Spec file {spec_file} not found!")
        return False
    
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", spec_file]
    
    if not run_command(cmd, f"Building {description}"):
        return False
    
    # Check if the EXE was created
    exe_path = Path(f"dist/{exe_name}")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"   [OK] {description.capitalize()} built successfully: {exe_path} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"   [ERROR] EXE not found at expected location: {exe_path}")
        return False

def verify_architecture():
    """Verify that the client-server architecture components exist."""
    print("[CHECK] Verifying client-server architecture...")
    
    required_components = {
        "server/server_main.py": "Server main module",
        "client/client_main.py": "Client main module", 
        "main.py": "Unified entry point"
    }
    
    missing_components = []
    for component, description in required_components.items():
        if not os.path.exists(component):
            missing_components.append(f"{description} ({component})")
            print(f"   [ERROR] Missing: {description} ({component})")
        else:
            print(f"   [OK] Found: {description}")
    
    if missing_components:
        print(f"[ERROR] Architecture verification failed. Missing components:")
        for component in missing_components:
            print(f"   - {component}")
        return False
    
    print("[OK] Architecture verification successful!")
    return True

def main():
    """Main build process - builds CLIENT as EXE (server runs in Docker)."""
    parser = argparse.ArgumentParser(description='Build GAJA Assistant Client EXE (server runs in Docker)')
    parser.add_argument('--component', choices=['client', 'legacy'], 
                       default='client', help='Component to build (server runs in Docker)')
    parser.add_argument('--skip-overlay', action='store_true', 
                       help='Skip building Rust overlay')
    parser.add_argument('--skip-verification', action='store_true',
                       help='Skip architecture verification')
    
    args = parser.parse_args()
    
    print("[START] GAJA Assistant Build Process - Client EXE (Server via Docker)")
    print("=" * 60)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"[INFO] Working directory: {os.getcwd()}")
    
    # Verify architecture unless skipped
    if not args.skip_verification:
        if not verify_architecture():
            print("[ERROR] Architecture verification failed!")
            return 1
    
    # Check dependencies
    if not check_dependencies():
        print("[ERROR] Dependency check failed!")
        return 1
    
    # Clean previous builds
    clean_build()
    
    # Build overlay (optional)
    if not args.skip_overlay:
        build_overlay()    # Build components based on selection
    success = True
    
    if args.component == 'client':
        print("\n[CLIENT] Building PLUG-AND-PLAY CLIENT EXE...")
        print("[INFO] Client will download ML dependencies at first run")
        print("[INFO] Server should be run via Docker: docker-compose up gaja-server-cpu")
        success = build_component('client')
    elif args.component == 'legacy':
        print("\n[LEGACY] Building LEGACY unified component...")
        print("[WARN] Legacy mode includes both client and server in EXE")
        success = build_component('legacy')
    
    if not success:
        print("[ERROR] Build failed!")
        return 1
    
    print("=" * 60)
    print("[SUCCESS] Build completed successfully!")
    
    # Show results
    if args.component == 'client':
        client_exe = Path("dist/GajaClient.exe")
        if client_exe.exists():
            print(f"   [CLIENT] Client EXE: {client_exe} ({client_exe.stat().st_size / (1024*1024):.1f} MB)")
    
    if args.component == 'legacy':
        legacy_exe = Path("dist/Gaja.exe")
        if legacy_exe.exists():
            print(f"   [LEGACY] Legacy EXE: {legacy_exe} ({legacy_exe.stat().st_size / (1024*1024):.1f} MB)")
    
    print("\n[USAGE] How to run:")
    if args.component == 'client':
        print("   1. Start server: docker-compose up gaja-server-cpu")
        print("   2. Run client: GajaClient.exe")
        print("   3. Client will connect to server at ws://localhost:8001/ws/")
    if args.component == 'legacy':
        print("   Legacy unified: Gaja.exe (includes both client and server)")
    
    print("\n[DOCKER] Server management:")
    print("   Start server: docker-compose up gaja-server-cpu")
    print("   Stop server:  docker-compose down")
    print("   View logs:    docker-compose logs -f gaja-server-cpu")
    print("   Rebuild:      docker-compose build gaja-server-cpu")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
GAJA Assistant - System Management Script
Unified script for managing both client build and server Docker operations.
"""

import argparse
import subprocess
import sys


def run_command(cmd, description="", shell=False):
    """Run a command and handle errors gracefully."""
    print(f"[EXEC] {description}")
    print(f"       Running: {' '.join(cmd) if not shell else cmd}")

    try:
        if shell:
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, shell=True
            )
        else:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        if result.stdout:
            print(f"       Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"       [ERROR] Command failed: {e}")
        if e.stdout:
            print(f"       Stdout: {e.stdout}")
        if e.stderr:
            print(f"       Stderr: {e.stderr}")
        return False


def build_client():
    """Build plug-and-play client EXE with runtime dependency management."""
    print("[CLIENT] Building plug-and-play client EXE...")
    print("[INFO] Client will download ML dependencies at first run")
    return run_command(
        [sys.executable, "build.py", "--component", "client"], "Building client"
    )


def docker_build_server():
    """Build server Docker image."""
    print("[DOCKER] Building server Docker image...")
    return run_command(
        ["docker-compose", "build", "gaja-server-cpu"], "Building Docker image"
    )


def docker_start_server():
    """Start server in Docker."""
    print("[DOCKER] Starting server...")
    return run_command(
        ["docker-compose", "up", "-d", "gaja-server-cpu"], "Starting server"
    )


def docker_stop_server():
    """Stop server Docker container."""
    print("[DOCKER] Stopping server...")
    return run_command(["docker-compose", "down"], "Stopping server")


def docker_logs_server():
    """Show server logs."""
    print("[DOCKER] Showing server logs...")
    return run_command(
        ["docker-compose", "logs", "-f", "gaja-server-cpu"], "Server logs"
    )


def docker_status():
    """Show Docker container status."""
    print("[DOCKER] Checking server status...")
    return run_command(["docker-compose", "ps"], "Container status")


def test_system():
    """Test the complete system."""
    print("[TEST] Running system tests...")
    return run_command([sys.executable, "test_build_system.py"], "System tests")


def full_setup():
    """Complete setup: build client and start server."""
    print("[SETUP] Complete system setup...")

    # Build client
    if not build_client():
        print("[ERROR] Client build failed!")
        return False

    # Build and start server
    if not docker_build_server():
        print("[ERROR] Server Docker build failed!")
        return False

    if not docker_start_server():
        print("[ERROR] Server startup failed!")
        return False

    print("[SUCCESS] System setup complete!")
    print("           Client: dist/GajaClient.exe")
    print("           Server: http://localhost:8001")
    print("           WebSocket: ws://localhost:8001/ws/")
    return True


def main():
    """Main management interface."""
    parser = argparse.ArgumentParser(description="GAJA Assistant System Management")
    parser.add_argument(
        "action",
        choices=[
            "build-client",
            "build-server",
            "start-server",
            "stop-server",
            "logs",
            "status",
            "test",
            "setup",
            "help",
        ],
        help="Action to perform",
    )

    args = parser.parse_args()

    print("[START] GAJA Assistant System Management")
    print("=" * 50)

    success = True

    if args.action == "build-client":
        success = build_client()
    elif args.action == "build-server":
        success = docker_build_server()
    elif args.action == "start-server":
        success = docker_start_server()
    elif args.action == "stop-server":
        success = docker_stop_server()
    elif args.action == "logs":
        success = docker_logs_server()
    elif args.action == "status":
        success = docker_status()
    elif args.action == "test":
        success = test_system()
    elif args.action == "setup":
        success = full_setup()
    elif args.action == "help":
        print_help()
        return 0

    if success:
        print("[SUCCESS] Operation completed successfully!")
        return 0
    else:
        print("[ERROR] Operation failed!")
        return 1


def print_help():
    """Print detailed help information."""
    print(
        """
GAJA Assistant System Management

Available actions:

Client Management:
  build-client     Build client as EXE file

Server Management (Docker):
  build-server     Build server Docker image
  start-server     Start server container
  stop-server      Stop server container
  logs             Show server logs (real-time)
  status           Show container status

System Management:
  setup            Complete setup (build client + start server)
  test             Run system tests
  help             Show this help

Examples:
  python manage.py setup              # Complete setup
  python manage.py build-client       # Build only client
  python manage.py start-server       # Start only server
  python manage.py logs               # Monitor server logs
  python manage.py status             # Check server status

Workflow:
  1. python manage.py setup           # First time setup
  2. dist/GajaClient.exe              # Run client
  3. python manage.py logs            # Monitor if needed
  4. python manage.py stop-server     # Stop when done
"""
    )


if __name__ == "__main__":
    sys.exit(main())

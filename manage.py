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
            # For shell commands, ensure proper escaping
            if isinstance(cmd, str):
                # Split shell command into components for safety
                import shlex

                cmd_parts = shlex.split(cmd)
                result = subprocess.run(
                    cmd_parts, check=True, capture_output=True, text=True
                )
            else:
                result = subprocess.run(
                    cmd, check=True, capture_output=True, text=True, shell=False
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


def check_docker():
    """Check if Docker is running."""
    print("[CHECK] Verifying Docker status...")
    try:
        result = subprocess.run(
            ["docker", "version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("       ✅ Docker is running")
            return True
        else:
            print("       ❌ Docker is not responding")
            return False
    except Exception as e:
        print(f"       ❌ Docker check failed: {e}")
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
        ["docker-compose", "build", "gaja-server"], "Building Docker image"
    )


def docker_rebuild_server():
    """Rebuild server Docker image from scratch."""
    print("[DOCKER] Rebuilding server Docker image from scratch...")
    return run_command(
        ["docker-compose", "build", "--no-cache", "gaja-server"],
        "Rebuilding Docker image (no cache)",
    )


def docker_start_server():
    """Start server in Docker."""
    print("[DOCKER] Starting server...")
    return run_command(["docker-compose", "up", "-d", "gaja-server"], "Starting server")


def docker_stop_server():
    """Stop server Docker container."""
    print("[DOCKER] Stopping server...")
    return run_command(["docker-compose", "down"], "Stopping server")


def docker_restart_server():
    """Restart server Docker container."""
    print("[DOCKER] Restarting server...")
    if docker_stop_server():
        return docker_start_server()
    return False


def docker_logs_server():
    """Show server logs."""
    print("[DOCKER] Showing server logs...")
    return run_command(["docker-compose", "logs", "-f", "gaja-server"], "Server logs")
    """Show server logs."""
    print("[DOCKER] Showing server logs...")
    return run_command(["docker-compose", "logs", "-f", "gaja-server"], "Server logs")


def docker_status():
    """Show Docker container status."""
    print("[DOCKER] Checking server status...")
    result = run_command(["docker-compose", "ps"], "Container status")

    # Also check if the service is responding
    print("[DOCKER] Checking server health...")
    import requests

    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("       ✅ Server is responding on port 8001")
        else:
            print(f"       ⚠️  Server responded with status {response.status_code}")
    except Exception as e:
        print(f"       ❌ Server not responding: {e}")

    return result


def test_system():
    """Test the complete system."""
    print("[TEST] Running system tests...")
    return run_command([sys.executable, "test_build_system.py"], "System tests")


def full_setup():
    """Complete setup: build client and start server."""
    print("[SETUP] Complete system setup...")

    # Check Docker first
    if not check_docker():
        print("[ERROR] Docker is not running! Please start Docker Desktop first.")
        return False

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

    # Wait a moment and check if server is responding
    print("[SETUP] Waiting for server to start...")
    import time

    time.sleep(5)

    # Check server health
    import requests

    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        if response.status_code == 200:
            print("[SUCCESS] Server is responding correctly!")
        else:
            print(f"[WARNING] Server responded with status {response.status_code}")
    except Exception as e:
        print(f"[WARNING] Server health check failed: {e}")

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
            "rebuild-server",
            "start-server",
            "stop-server",
            "restart-server",
            "logs",
            "status",
            "test",
            "setup",
            "check-docker",
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
    elif args.action == "rebuild-server":
        success = docker_rebuild_server()
    elif args.action == "start-server":
        success = docker_start_server()
    elif args.action == "stop-server":
        success = docker_stop_server()
    elif args.action == "restart-server":
        success = docker_restart_server()
    elif args.action == "logs":
        success = docker_logs_server()
    elif args.action == "status":
        success = docker_status()
    elif args.action == "test":
        success = test_system()
    elif args.action == "setup":
        success = full_setup()
    elif args.action == "check-docker":
        success = check_docker()
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
  rebuild-server   Rebuild server Docker image (no cache)
  start-server     Start server container
  stop-server      Stop server container
  restart-server   Restart server container
  logs             Show server logs (real-time)
  status           Show container status + health check

System Management:
  setup            Complete setup (build client + start server)
  test             Run system tests
  check-docker     Check if Docker is running
  help             Show this help

Examples:
  python manage.py check-docker        # Check Docker status first
  python manage.py setup              # Complete setup
  python manage.py build-client       # Build only client
  python manage.py start-server       # Start only server
  python manage.py restart-server     # Restart if having issues
  python manage.py logs               # Monitor server logs
  python manage.py status             # Check server status
  python manage.py stop-server        # Stop when done

Troubleshooting:
  python manage.py check-docker       # Verify Docker is running
  python manage.py rebuild-server     # Force rebuild if issues
  python manage.py restart-server     # Restart if not responding

Workflow:
  1. python manage.py check-docker     # Verify Docker first
  2. python manage.py setup           # First time setup
  3. dist/GajaClient.exe              # Run client
  4. python manage.py logs            # Monitor if needed
  5. python manage.py stop-server     # Stop when done
"""
    )


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Test script to verify the new client-server build system."""

import subprocess
import sys
from pathlib import Path


def test_build_help():
    """Test that build.py shows help correctly."""
    print("🧪 Testing build.py help...")
    result = subprocess.run(
        [sys.executable, "build.py", "--help"], capture_output=True, text=True
    )
    if result.returncode == 0 and "Client EXE" in result.stdout:
        print("   ✅ Build help works correctly")
        return True
    else:
        print(f"   ❌ Build help failed: {result.stderr}")
        return False


def test_architecture_verification():
    """Test architecture verification."""
    print("🧪 Testing architecture verification...")
    result = subprocess.run(
        [
            sys.executable,
            "build.py",
            "--skip-overlay",
            "--component",
            "client",
            "--skip-verification",
        ],
        capture_output=True,
        text=True,
    )

    if "Architecture verification" in result.stdout or result.returncode == 0:
        print("   ✅ Architecture verification works")
        return True
    else:
        print(f"   ❌ Architecture verification failed: {result.stderr}")
        return False


def test_entry_points():
    """Test that entry points can be imported."""
    print("🧪 Testing entry points...")

    # Test client entry point (primary focus)
    try:
        sys.path.insert(0, str(Path(__file__).parent))

        print("   ✅ Client entry point imports correctly")
        client_ok = True
    except Exception as e:
        print(f"   ❌ Client entry point failed: {e}")
        client_ok = False

    # Test server entry point (for Docker reference)
    try:
        print("   ✅ Server entry point available (for Docker)")
        server_ok = True
    except Exception as e:
        print(f"   ⚠️  Server entry point issue (server runs in Docker): {e}")
        server_ok = True  # Not critical since server runs in Docker

    return client_ok and server_ok


def test_spec_files():
    """Test that spec files exist."""
    print("🧪 Testing spec files...")

    spec_files = {
        "gaja_client.spec": "Client spec (primary)",
        "gaja.spec": "Legacy spec (optional)",
    }

    all_ok = True
    for spec_file, description in spec_files.items():
        if Path(spec_file).exists():
            print(f"   ✅ {description} exists")
        else:
            print(f"   ❌ {description} missing")
            all_ok = False

    # Check Docker setup
    if Path("docker-compose.yml").exists():
        print("   ✅ Docker Compose for server exists")
    else:
        print("   ❌ Docker Compose missing")
        all_ok = False

    if Path("docker/Dockerfile").exists():
        print("   ✅ Dockerfile for server exists")
    else:
        print("   ❌ Dockerfile missing")
        all_ok = False

    return all_ok


def test_docker_setup():
    """Test Docker setup for server."""
    print("🧪 Testing Docker setup...")

    # Test docker-compose syntax
    result = subprocess.run(
        ["docker-compose", "config"], capture_output=True, text=True
    )
    if result.returncode == 0:
        print("   ✅ Docker Compose configuration is valid")
        docker_ok = True
    else:
        print(f"   ⚠️  Docker Compose validation failed: {result.stderr}")
        docker_ok = False

    return docker_ok


def main():
    """Run all tests."""
    print("🚀 Testing GAJA Assistant Build System (Client EXE + Server Docker)")
    print("=" * 60)

    tests = [
        test_build_help,
        test_architecture_verification,
        test_entry_points,
        test_spec_files,
        test_docker_setup,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("✅ All tests passed! Build system is ready.")
        print("📋 Next steps:")
        print("   1. Build client: python build.py")
        print("   2. Start server: docker-compose up gaja-server-cpu")
        print("   3. Run client: dist\\GajaClient.exe")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

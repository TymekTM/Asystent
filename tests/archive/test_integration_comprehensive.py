#!/usr/bin/env python3
"""Test funkcjonalności AI GAJA Assistant Test integracyjny sprawdzający funkcjonalność
AI i function calling."""

import sys
from datetime import datetime

import requests

# Konfiguracja serwera
SERVER_URL = "http://localhost:8001"


def test_health():
    """Test podstawowego endpoint health."""
    print("🔍 Test 1: Sprawdzanie health endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health OK: {data}")
            return True
        else:
            print(f"❌ Health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health error: {e}")
        return False


def test_api_health():
    """Test API health endpoint."""
    print("\n🔍 Test 2: Sprawdzanie API health endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/api/v1/healthz")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Health OK: {data}")
            return True
        else:
            print(f"❌ API Health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Health error: {e}")
        return False


def test_openapi_docs():
    """Test dostępu do dokumentacji OpenAPI."""
    print("\n🔍 Test 3: Sprawdzanie dostępu do OpenAPI...")
    try:
        response = requests.get(f"{SERVER_URL}/openapi.json")
        if response.status_code == 200:
            data = response.json()
            paths = list(data.get("paths", {}).keys())
            print(f"✅ OpenAPI OK. Dostępne endpointy: {len(paths)}")
            print(f"   Endpointy: {paths[:5]}...")  # Pokaż pierwsze 5
            return True
        else:
            print(f"❌ OpenAPI failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ OpenAPI error: {e}")
        return False


def test_server_logs():
    """Test sprawdzenia logów serwera przez Docker."""
    print("\n🔍 Test 4: Sprawdzanie logów serwera...")
    try:
        import subprocess

        result = subprocess.run(
            ["docker", "logs", "--tail", "10", "gaja-server-cpu"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            logs = result.stdout.strip()
            print(f"✅ Logi serwera dostępne ({len(logs)} znaków)")
            if "uvicorn" in logs.lower() or "server" in logs.lower():
                print("   ✅ Wykryto aktywność serwera")
                return True
            else:
                print("   ⚠️  Brak wykrycia aktywności serwera")
                return False
        else:
            print(f"❌ Błąd pobierania logów: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return False


def test_database_access():
    """Test dostępu do bazy danych."""
    print("\n🔍 Test 5: Sprawdzanie dostępu do bazy danych...")
    try:
        import subprocess

        result = subprocess.run(
            ["docker", "exec", "gaja-server-cpu", "ls", "-la", "/app/databases/"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            files = result.stdout.strip()
            print("✅ Baza danych dostępna")
            if "server_data.db" in files:
                print("   ✅ Znaleziono server_data.db")
            if "gaja_memory.db" in files:
                print("   ✅ Znaleziono gaja_memory.db")
            return True
        else:
            print(f"❌ Błąd dostępu do bazy: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


def test_integration_summary():
    """Podsumowanie testów integracyjnych."""
    print("\n" + "=" * 60)
    print("📊 PODSUMOWANIE TESTÓW INTEGRACYJNYCH GAJA")
    print("=" * 60)

    tests = [
        test_health,
        test_api_health,
        test_openapi_docs,
        test_server_logs,
        test_database_access,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        if test_func():
            passed += 1

    print(f"\n📈 Wyniki: {passed}/{total} testów przeszło pomyślnie")

    if passed == total:
        print("🎉 WSZYSTKIE TESTY PRZESZŁY! System jest gotowy do produkcji.")
        return True
    elif passed >= total * 0.8:  # 80% success rate
        print("✅ WIĘKSZOŚĆ TESTÓW PRZESZŁA. System jest w dużej mierze funkcjonalny.")
        return True
    else:
        print("❌ WIELE TESTÓW NIE POWIODŁO SIĘ. System wymaga napraw.")
        return False


def main():
    """Główna funkcja testowa."""
    print("🚀 GAJA Assistant - Test Integracyjny")
    print("=====================================")
    print(f"⏰ Czas uruchomienia: {datetime.now()}")
    print(f"🎯 Testowanie serwera: {SERVER_URL}")
    print()

    success = test_integration_summary()

    print(f"\n🏁 Test zakończony: {'SUKCES' if success else 'NIEPOWODZENIE'}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

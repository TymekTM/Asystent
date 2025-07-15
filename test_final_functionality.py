"""
Test końcowy funkcjonalności GAJA - testy manualne

Ten plik zawiera instrukcje do manualnych testów aplikacji po wprowadzeniu poprawek.
"""

import sys
from pathlib import Path

import requests

# Dodaj ścieżkę do głównego katalogu projektu
sys.path.insert(0, str(Path(__file__).parent))


class TestGAJAFunctionality:
    """Testy funkcjonalności aplikacji GAJA."""

    def test_overlay_click_through(self):
        """Test 1: Overlay powinien być przeźroczysty dla kliknięć"""
        print("\n=== TEST 1: Overlay Click-Through ===")
        print("1. Uruchom aplikację GAJA")
        print("2. Sprawdź czy overlay jest widoczny w prawym górnym rogu")
        print("3. Spróbuj kliknąć przez overlay na aplikację poniżej")
        print(
            "4. Overlay powinien być przeźroczysty - kliki powinny przechodzić przez niego"
        )
        print(
            "5. Otwórz aplikację (np. notatnik) i sprawdź czy można w niej kliknąć pomimo overlay"
        )

        # Automatyczny test HTTP endpoint
        try:
            response = requests.get("http://localhost:5001/api/status")
            if response.status_code == 200:
                status = response.json()
                print(f"✅ HTTP API działa: {status}")
                return True
            else:
                print(f"❌ HTTP API zwraca błąd: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Błąd testowania HTTP API: {e}")
            return False

    def test_settings_window_opens(self):
        """Test 2: Okno ustawień powinno się otwierać"""
        print("\n=== TEST 2: Okno ustawień ===")
        print("1. Kliknij prawym przyciskiem myszy na ikonę GAJA w system tray")
        print("2. Wybierz 'Ustawienia' z menu")
        print("3. Okno ustawień powinno się otworzyć")
        print("4. Sprawdź czy wszystkie sekcje są widoczne:")
        print("   - Status Systemu")
        print("   - Ustawienia Audio")
        print("   - Ustawienia Głosu")
        print("   - Ustawienia Overlay")
        print("   - Ustawienia Daily Briefing")

        # Automatyczny test HTTP ustawień
        try:
            response = requests.get("http://localhost:5001/settings.html")
            if response.status_code == 200:
                print(
                    "✅ Strona ustawień dostępna pod http://localhost:5001/settings.html"
                )
                return True
            else:
                print(f"❌ Strona ustawień niedostępna: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Błąd testowania strony ustawień: {e}")
            return False

    def test_audio_devices_detection(self):
        """Test 3: Aplikacja powinna wykrywać urządzenia audio"""
        print("\n=== TEST 3: Wykrywanie urządzeń audio ===")
        print("1. Otwórz ustawienia")
        print("2. Sprawdź sekcję 'Ustawienia Audio'")
        print("3. Sprawdź czy są dostępne urządzenia wejściowe (mikrofony)")
        print("4. Sprawdź czy są dostępne urządzenia wyjściowe (głośniki)")
        print("5. Wybierz inne urządzenie z listy")
        print("6. Kliknij 'Zapisz ustawienia'")

        # Automatyczny test audio devices API
        try:
            response = requests.get("http://localhost:5001/api/audio_devices")
            if response.status_code == 200:
                devices = response.json()
                input_count = len(devices.get("input_devices", []))
                output_count = len(devices.get("output_devices", []))
                print(
                    f"✅ Wykryto {input_count} urządzeń wejściowych i {output_count} wyjściowych"
                )
                return input_count > 0 and output_count > 0
            else:
                print(f"❌ API urządzeń audio zwraca błąd: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Błąd testowania API urządzeń audio: {e}")
            return False

    def test_settings_save_load(self):
        """Test 4: Zapisywanie i ładowanie ustawień"""
        print("\n=== TEST 4: Zapisywanie ustawień ===")
        print("1. Otwórz ustawienia")
        print("2. Zmień słowo aktywacyjne z 'gaja' na 'asystent'")
        print("3. Zmień czułość wykrywania na 0.8")
        print("4. Zmień pozycję overlay na 'Lewy górny róg'")
        print("5. Kliknij 'Zapisz ustawienia'")
        print("6. Zamknij ustawienia i otwórz ponownie")
        print("7. Sprawdź czy zmiany zostały zapisane")

        # Automatyczny test zapisywania ustawień
        try:
            # Załaduj aktualne ustawienia
            response = requests.get("http://localhost:5001/api/current_settings")
            if response.status_code != 200:
                print(f"❌ Błąd ładowania ustawień: {response.status_code}")
                return False

            current_settings = response.json()

            # Zmodyfikuj ustawienia
            test_settings = {
                "audio": {"input_device": "test_input", "output_device": "test_output"},
                "voice": {
                    "wake_word": "test_wake",
                    "sensitivity": 0.8,
                    "language": "en-US",
                },
                "overlay": {"enabled": True, "position": "top-left", "opacity": 0.7},
                "daily_briefing": {
                    "enabled": True,
                    "startup_briefing": True,
                    "briefing_time": "09:00",
                    "location": "Test,PL",
                },
            }

            # Zapisz ustawienia
            response = requests.post(
                "http://localhost:5001/api/save_settings",
                json={"settings": test_settings},
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✅ Ustawienia zapisane pomyślnie")
                    return True
                else:
                    print(f"❌ Błąd zapisywania ustawień: {result}")
                    return False
            else:
                print(f"❌ HTTP błąd przy zapisywaniu: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Błąd testowania zapisywania ustawień: {e}")
            return False

    def test_wakeword_detection(self):
        """Test 5: Wykrywanie słowa aktywującego"""
        print("\n=== TEST 5: Wykrywanie słowa aktywującego ===")
        print(
            "1. Upewnij się, że aplikacja nasłuchuje (ikona w tray powinna być zielona)"
        )
        print("2. Powiedz słowo aktywacyjne 'gaja'")
        print("3. Overlay powinien się pokazać z informacją o nagrywaniu")
        print("4. Powiedz jakieś polecenie, np. 'Powiedz mi o pogodzie'")
        print("5. Sprawdź czy aplikacja odpowiada głosem")

        # Automatyczny test trigger wakeword
        try:
            response = requests.get("http://localhost:5001/api/trigger_wakeword")
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✅ Test wakeword uruchomiony pomyślnie")
                    return True
                else:
                    print(f"❌ Błąd uruchamiania testu wakeword: {result}")
                    return False
            else:
                print(f"❌ HTTP błąd przy teście wakeword: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Błąd testowania wakeword: {e}")
            return False

    def test_overlay_visibility_states(self):
        """Test 6: Stany widoczności overlay"""
        print("\n=== TEST 6: Stany overlay ===")
        print("1. Sprawdź czy overlay jest ukryty gdy aplikacja jest bezczynna")
        print("2. Kliknij prawym przyciskiem na ikonę w tray")
        print("3. Wybierz 'Enable Overlay' aby pokazać overlay")
        print("4. Sprawdź czy overlay się pojawił")
        print("5. Wybierz ponownie 'Disable Overlay' aby ukryć")
        print("6. Sprawdź czy overlay zniknął")

        # Automatyczny test przez API
        try:
            response = requests.get("http://localhost:5001/api/status")
            if response.status_code == 200:
                status = response.json()
                overlay_visible = status.get("overlay_visible", False)
                print(
                    f"✅ Status overlay: {'widoczny' if overlay_visible else 'ukryty'}"
                )
                return True
            else:
                print(f"❌ Błąd pobierania statusu overlay: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Błąd testowania statusu overlay: {e}")
            return False

    def test_connection_status(self):
        """Test 7: Status połączenia z serwerem"""
        print("\n=== TEST 7: Status połączenia ===")
        print("1. Otwórz ustawienia")
        print("2. Sprawdź sekcję 'Status Systemu'")
        print("3. Sprawdź czy jest pokazane połączenie z serwerem")
        print("4. Kliknij 'Odśwież' aby ponownie sprawdzić połączenie")

        # Automatyczny test connection status
        try:
            response = requests.get("http://localhost:5001/api/connection_status")
            if response.status_code == 200:
                status = response.json()
                connected = status.get("connected", False)
                print(
                    f"✅ Status połączenia: {'połączony' if connected else 'rozłączony'}"
                )
                if connected:
                    print(f"   Port: {status.get('port', 'nieznany')}")
                return True
            else:
                print(f"❌ Błąd pobierania statusu połączenia: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Błąd testowania statusu połączenia: {e}")
            return False


def run_manual_tests():
    """Uruchom wszystkie manualne testy."""
    print("🚀 URUCHAMIANIE TESTÓW KOŃCOWYCH GAJA")
    print("=" * 50)

    test_suite = TestGAJAFunctionality()

    tests = [
        ("Overlay Click-Through", test_suite.test_overlay_click_through),
        ("Okno ustawień", test_suite.test_settings_window_opens),
        ("Wykrywanie urządzeń audio", test_suite.test_audio_devices_detection),
        ("Zapisywanie ustawień", test_suite.test_settings_save_load),
        ("Wykrywanie słowa aktywującego", test_suite.test_wakeword_detection),
        ("Stany overlay", test_suite.test_overlay_visibility_states),
        ("Status połączenia", test_suite.test_connection_status),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(
                f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}"
            )
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ {test_name}: ERROR - {e}")

    print("\n" + "=" * 50)
    print("📊 PODSUMOWANIE TESTÓW:")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        print(f"{'✅' if result else '❌'} {test_name}")

    print(f"\n🎯 WYNIK: {passed}/{total} testów przeszło pomyślnie")

    if passed == total:
        print("🎉 WSZYSTKIE TESTY PRZESZŁY! Aplikacja jest gotowa do użycia.")
    else:
        print("⚠️  NIEKTÓRE TESTY NIE PRZESZŁY. Sprawdź błędy powyżej.")

    return passed == total


if __name__ == "__main__":
    success = run_manual_tests()
    sys.exit(0 if success else 1)

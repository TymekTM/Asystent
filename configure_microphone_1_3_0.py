#!/usr/bin/env python3
"""
GAJA Microphone Configuration Tool - Version 1.3.0
Narzędzie do konfiguracji mikrofonu wejściowego dla asystenta GAJA.
"""

import json
import sys
from pathlib import Path


def load_config():
    """Wczytaj główną konfigurację z config.json."""
    config_path = Path("config.json")
    if not config_path.exists():
        print("❌ Błąd: Nie znaleziono pliku config.json")
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Błąd wczytywania config.json: {e}")
        return None


def save_config(config):
    """Zapisz konfigurację do config.json."""
    try:
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Błąd zapisywania config.json: {e}")
        return False


def test_microphone(device_id):
    """Testuj mikrofon przez 3 sekundy i pokaż poziomy audio."""
    print(f"🔊 Testowanie mikrofonu ID {device_id}...")
    print("💡 Mów coś przez 3 sekundy...")

    try:

        import numpy as np
        import sounddevice as sd

        duration = 3  # sekundy
        sample_rate = 16000

        print("🎤 Rozpoczynam nagrywanie...")
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=device_id,
            dtype="float32",
        )
        sd.wait()  # Czekaj na zakończenie nagrywania

        # Analiza poziomów audio
        rms = np.sqrt(np.mean(audio_data**2))
        max_amplitude = np.max(np.abs(audio_data))

        print("📊 Wyniki testu:")
        print(f"   RMS: {rms:.6f}")
        print(f"   Max amplituda: {max_amplitude:.4f}")

        if rms > 0.001:
            print("✅ Mikrofon działa poprawnie - wykryto sygnał audio")
        elif rms > 0.0001:
            print(
                "⚠️  Mikrofon działa, ale sygnał jest słaby - sprawdź ustawienia mikrofonu"
            )
        else:
            print("❌ Brak sygnału z mikrofonu - sprawdź połączenie i ustawienia")

        return True

    except Exception as e:
        print(f"❌ Błąd podczas testowania mikrofonu: {e}")
        return False


def list_devices():
    """Wyświetl listę dostępnych urządzeń audio."""
    print("🎵 Dostępne urządzenia audio:")
    print("=" * 50)
    try:
        import sounddevice as sd

        devices = sd.query_devices()

        print("\n📱 URZĄDZENIA WEJŚCIOWE (mikrofony):")
        print("-" * 40)
        input_devices = []
        for i, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                status = "✅ Domyślne" if i == sd.default.device[0] else "  "
                print(f"{status} ID {i:2d}: {device['name']}")
                input_devices.append((i, device["name"]))

        print("\n🔊 URZĄDZENIA WYJŚCIOWE (głośniki):")
        print("-" * 40)
        output_devices = []
        for i, device in enumerate(devices):
            if device["max_output_channels"] > 0:
                status = "✅ Domyślne" if i == sd.default.device[1] else "  "
                print(f"{status} ID {i:2d}: {device['name']}")
                output_devices.append((i, device["name"]))

        print(
            f"\n💡 Znaleziono {len(input_devices)} mikrofonów i {len(output_devices)} głośników"
        )
        print(
            "📋 Skopiuj ID wybranego mikrofonu i użyj: python configure_microphone_1_3_0.py set <ID>"
        )

    except Exception as e:
        print(f"❌ Błąd podczas listowania urządzeń: {e}")


def set_microphone(device_id):
    """Ustaw mikrofon w konfiguracji."""
    config = load_config()
    if not config:
        return False

    # Aktualizuj MIC_DEVICE_ID w głównej konfiguracji
    config["MIC_DEVICE_ID"] = device_id

    if save_config(config):
        print(f"✅ Mikrofon ustawiony na ID: {device_id}")
        return True
    else:
        return False


def show_status():
    """Pokaż aktualny status konfiguracji mikrofonu."""
    print("🎵 GAJA Microphone Configuration Tool - Version 1.3.0")
    print("=" * 60)
    print("📊 Current microphone settings:")
    print("-" * 30)

    config = load_config()
    if not config:
        return

    print("\nMain Config:")
    print("  File: config.json")
    print(f"  mic_device_id: {config.get('MIC_DEVICE_ID', 'None')}")
    print(f"  speaker_device_id: {config.get('SPEAKER_DEVICE_ID', 'None')}")
    print(f"  wake_word: {config.get('WAKE_WORD', 'None')}")
    print(
        f"  wake_word_sensitivity: {config.get('WAKE_WORD_SENSITIVITY_THRESHOLD', 'None')}"
    )

    mic_id = config.get("MIC_DEVICE_ID")
    if mic_id is not None:
        print(f"\n✅ Mikrophone configured with device ID: {mic_id}")

        # Spróbuj pokazać nazwę urządzenia
        try:
            import sounddevice as sd

            device_info = sd.query_devices(mic_id)
            print(f"📱 Device name: {device_info['name']}")
        except:
            print("📱 Device name: Could not retrieve")
    else:
        print("\n⚠️  No microphone device configured")


def test_wakeword():
    """Test wakeword detection with current configuration."""
    print("🎤 Testing wakeword detection...")
    config = load_config()
    if not config:
        return

    mic_id = config.get("MIC_DEVICE_ID")
    if mic_id is None:
        print("❌ No microphone configured. Use 'set' command first.")
        return

    print("📊 Configuration:")
    print(f"   Microphone ID: {mic_id}")
    print(f"   Wake word: {config.get('WAKE_WORD', 'gaja')}")
    print(f"   Sensitivity: {config.get('WAKE_WORD_SENSITIVITY_THRESHOLD', 0.35)}")
    print()
    print("💡 To test wakeword detection, run the main assistant:")
    print("   python main.py")
    print("   Then say the wake word to test detection.")


def main():
    if len(sys.argv) < 2:
        print("🎵 GAJA Microphone Configuration Tool - Version 1.3.0")
        print("=" * 60)
        print("Usage:")
        print(
            "  python configure_microphone_1_3_0.py list       - Lista urządzeń audio"
        )
        print("  python configure_microphone_1_3_0.py test <ID>  - Test mikrofonu")
        print("  python configure_microphone_1_3_0.py set <ID>   - Ustaw mikrofon")
        print("  python configure_microphone_1_3_0.py status     - Pokaż status")
        print(
            "  python configure_microphone_1_3_0.py wakeword   - Test wakeword detection"
        )
        print()
        print("Przykład:")
        print("  python configure_microphone_1_3_0.py list")
        print("  python configure_microphone_1_3_0.py test 15")
        print("  python configure_microphone_1_3_0.py set 15")
        return

    command = sys.argv[1].lower()

    if command == "list":
        list_devices()
    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ Błąd: Podaj ID urządzenia do testu")
            print("Przykład: python configure_microphone_1_3_0.py test 15")
            return
        try:
            device_id = int(sys.argv[2])
            test_microphone(device_id)
        except ValueError:
            print("❌ Błąd: ID urządzenia musi być liczbą")
    elif command == "set":
        if len(sys.argv) < 3:
            print("❌ Błąd: Podaj ID urządzenia do ustawienia")
            print("Przykład: python configure_microphone_1_3_0.py set 15")
            return
        try:
            device_id = int(sys.argv[2])
            set_microphone(device_id)
        except ValueError:
            print("❌ Błąd: ID urządzenia musi być liczbą")
    elif command == "status":
        show_status()
    elif command == "wakeword":
        test_wakeword()
    else:
        print(f"❌ Nieznana komenda: {command}")
        print("Dostępne komendy: list, test, set, status, wakeword")


if __name__ == "__main__":
    main()

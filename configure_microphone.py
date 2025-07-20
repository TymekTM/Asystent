#!/usr/bin/env python3
"""Microphone configuration tool for GAJA Assistant.

This tool helps you:
1. List available audio input devices
2. Test microphone devices
3. Update microphone settings in all configuration files
"""

import json
import sys
from pathlib import Path
from typing import Optional


def list_audio_devices() -> list[dict]:
    """List all available audio input devices."""
    try:
        import sounddevice as sd

        print("🎤 Available Audio Input Devices:")
        print("=" * 50)

        devices = sd.query_devices()
        default_input = sd.default.device[0] if sd.default.device else None

        input_devices = []

        for i, device in enumerate(devices):
            if device.get("max_input_channels", 0) > 0:  # Input device
                is_default = i == default_input
                status = " (DEFAULT)" if is_default else ""
                print(f"ID {i:3d}: {device['name']}{status}")
                print(
                    f"         Channels: {device['max_input_channels']}, Sample Rate: {device['default_samplerate']}"
                )

                input_devices.append(
                    {
                        "id": i,
                        "name": device["name"],
                        "is_default": is_default,
                        "channels": device["max_input_channels"],
                        "sample_rate": device["default_samplerate"],
                    }
                )

        print(f"\nFound {len(input_devices)} input devices")
        if default_input is not None:
            print(f"Current system default: ID {default_input}")

        return input_devices

    except ImportError:
        print("❌ sounddevice not available - install with: pip install sounddevice")
        return []
    except Exception as e:
        print(f"❌ Error listing audio devices: {e}")
        return []


def test_microphone(device_id: int) -> bool:
    """Test recording from a specific microphone device."""
    try:
        import numpy as np
        import sounddevice as sd

        print(f"\n🎤 Testing microphone ID {device_id}...")
        print("Recording 3 seconds... Please speak into the microphone!")

        # Record 3 seconds of audio
        duration = 3
        sample_rate = 16000

        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=device_id,
        )
        sd.wait()  # Wait until recording is finished

        # Analyze the audio
        max_amplitude = np.max(np.abs(audio_data))
        rms_level = np.sqrt(np.mean(audio_data**2))

        print("✅ Recording completed!")
        print(f"   Max amplitude: {max_amplitude:.4f}")
        print(f"   RMS level: {rms_level:.4f}")

        if max_amplitude < 0.001:
            print("❌ Very low signal - check microphone connection")
            return False
        elif max_amplitude > 0.05:
            print("✅ Excellent signal level!")
            return True
        elif max_amplitude > 0.01:
            print("✅ Good signal level")
            return True
        else:
            print("⚠️  Low signal - might work but consider adjusting levels")
            return True

    except Exception as e:
        print(f"❌ Error testing device {device_id}: {e}")
        return False


def load_config(file_path: Path) -> dict | None:
    """Load JSON configuration file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Config file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {file_path}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None


def save_config(file_path: Path, config: dict) -> bool:
    """Save JSON configuration file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving {file_path}: {e}")
        return False


def get_current_microphone_settings() -> dict:
    """Get current microphone settings from all config files."""
    settings = {}

    # Main config.json
    main_config_path = Path("config.json")
    main_config = load_config(main_config_path)
    if main_config:
        settings["main_config"] = {
            "file": str(main_config_path),
            "mic_device_id": main_config.get("MIC_DEVICE_ID"),
            "speaker_device_id": main_config.get("SPEAKER_DEVICE_ID"),
        }

    # Client config.json
    client_config_path = Path("client/client_config.json")
    client_config = load_config(client_config_path)
    if client_config:
        settings["client_config"] = {
            "file": str(client_config_path),
            "wakeword_device_id": client_config.get("wakeword", {}).get("device_id"),
            "whisper_device_id": client_config.get("whisper", {}).get("device_id"),
            "audio_input_device": client_config.get("audio", {}).get("input_device"),
            "audio_output_device": client_config.get("audio", {}).get("output_device"),
        }

    return settings


def update_microphone_settings(device_id: int) -> bool:
    """Update microphone device ID in all configuration files."""
    success = True

    print(f"\n🔧 Updating microphone settings to device ID {device_id}...")

    # Update main config.json
    main_config_path = Path("config.json")
    main_config = load_config(main_config_path)
    if main_config:
        main_config["MIC_DEVICE_ID"] = device_id
        if save_config(main_config_path, main_config):
            print(f"✅ Updated {main_config_path}")
        else:
            success = False
    else:
        print(f"⚠️  Skipped {main_config_path} (not found)")

    # Update client config.json
    client_config_path = Path("client/client_config.json")
    client_config = load_config(client_config_path)
    if client_config:
        # Update all microphone-related settings
        if "wakeword" not in client_config:
            client_config["wakeword"] = {}
        client_config["wakeword"]["device_id"] = device_id

        if "whisper" not in client_config:
            client_config["whisper"] = {}
        client_config["whisper"]["device_id"] = device_id

        if "audio" not in client_config:
            client_config["audio"] = {}
        client_config["audio"]["input_device"] = device_id

        if save_config(client_config_path, client_config):
            print(f"✅ Updated {client_config_path}")
        else:
            success = False
    else:
        print(f"⚠️  Skipped {client_config_path} (not found)")

    return success


def main():
    """Main configuration tool."""
    print("🎵 GAJA Microphone Configuration Tool")
    print("=" * 50)

    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  python configure_microphone.py list                    - List all devices"
        )
        print(
            "  python configure_microphone.py test <device_id>        - Test specific device"
        )
        print(
            "  python configure_microphone.py set <device_id>         - Set microphone device"
        )
        print(
            "  python configure_microphone.py status                  - Show current settings"
        )
        return

    command = sys.argv[1].lower()

    if command == "list":
        devices = list_audio_devices()
        if devices:
            print(
                "\n💡 To test a device: python configure_microphone.py test <device_id>"
            )
            print("💡 To set a device: python configure_microphone.py set <device_id>")

    elif command == "test":
        if len(sys.argv) < 3:
            print(
                "❌ Please specify device ID: python configure_microphone.py test <device_id>"
            )
            return

        try:
            device_id = int(sys.argv[2])
            if test_microphone(device_id):
                print(f"\n✅ Device {device_id} works well!")
                print(
                    f"💡 To use this device: python configure_microphone.py set {device_id}"
                )
            else:
                print(f"\n❌ Device {device_id} has issues")
        except ValueError:
            print("❌ Device ID must be a number")

    elif command == "set":
        if len(sys.argv) < 3:
            print(
                "❌ Please specify device ID: python configure_microphone.py set <device_id>"
            )
            return

        try:
            device_id = int(sys.argv[2])

            # First test the device
            print(f"Testing device {device_id} before setting...")
            if not test_microphone(device_id):
                response = input("\n⚠️  Device test failed. Continue anyway? (y/N): ")
                if response.lower() != "y":
                    print("❌ Cancelled")
                    return

            # Update configurations
            if update_microphone_settings(device_id):
                print(
                    f"\n✅ Successfully configured microphone to device ID {device_id}"
                )
                print("🔄 Restart GAJA client to apply changes")
            else:
                print("\n❌ Failed to update some configuration files")

        except ValueError:
            print("❌ Device ID must be a number")

    elif command == "status":
        print("📊 Current microphone settings:")
        print("-" * 30)

        settings = get_current_microphone_settings()

        for config_name, config_data in settings.items():
            print(f"\n{config_name.replace('_', ' ').title()}:")
            print(f"  File: {config_data['file']}")
            for key, value in config_data.items():
                if key != "file":
                    print(f"  {key}: {value}")

        # Check for inconsistencies
        device_ids = []
        for config_data in settings.values():
            for key, value in config_data.items():
                if (
                    "device" in key.lower()
                    and "input" in key.lower()
                    and value is not None
                ):
                    device_ids.append(value)

        unique_device_ids = set(device_ids)
        if len(unique_device_ids) > 1:
            print(f"\n⚠️  Inconsistent microphone settings found: {unique_device_ids}")
            print("💡 Use 'python configure_microphone.py set <device_id>' to fix")
        elif len(unique_device_ids) == 1:
            print(f"\n✅ All configurations use device ID: {list(unique_device_ids)[0]}")
        else:
            print("\n⚠️  No microphone device configured")

    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python configure_microphone.py' for help")


if __name__ == "__main__":
    main()

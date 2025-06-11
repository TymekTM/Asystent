import argparse
import importlib
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "client" / "configs" / "user_modes.json"


def set_mode(mode: str) -> None:
    data = {"current_mode": mode}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_integrator():
    import mode_integrator
    return importlib.reload(mode_integrator).user_integrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Test user mode selection")
    parser.add_argument("--mode", choices=["poor_man", "paid"], help="Set mode before testing")
    args = parser.parse_args()

    if args.mode:
        set_mode(args.mode)

    integrator = load_integrator()
    print(f"Current mode: {integrator.mode}")
    print(f"TTS module: {integrator.tts_module.__class__.__name__}")
    print(f"ASR module: {integrator.asr_module.__class__.__name__}")


if __name__ == "__main__":
    main()

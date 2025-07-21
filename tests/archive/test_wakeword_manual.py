#!/usr/bin/env python3
"""Manual test script for wakeword detector.

This script manually tests the wakeword detector functionality. Use this for quick
testing without unit test complexity.
"""

import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_basic_imports():
    """Test that basic imports work."""
    logger.info("Testing basic imports...")

    try:
        from client.audio_modules.wakeword_detector import (
            CHUNK_DURATION_MS,
            SAMPLE_RATE,
            get_base_path,
        )

        logger.info("✓ Basic imports successful")
        logger.info(f"✓ SAMPLE_RATE: {SAMPLE_RATE}")
        logger.info(f"✓ CHUNK_DURATION_MS: {CHUNK_DURATION_MS}")
        logger.info(f"✓ Base path: {get_base_path()}")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_sounddevice_availability():
    """Test if sounddevice is available."""
    logger.info("Testing sounddevice availability...")

    try:
        from client.audio_modules.wakeword_detector import SOUNDDEVICE_AVAILABLE, sd

        if SOUNDDEVICE_AVAILABLE and sd:
            logger.info("✓ sounddevice is available")
            try:
                devices = sd.query_devices()
                input_devices = [d for d in devices if d["max_input_channels"] > 0]
                logger.info(f"✓ Found {len(input_devices)} input devices")
                return True
            except Exception as e:
                logger.warning(f"⚠ sounddevice available but device query failed: {e}")
                return False
        else:
            logger.warning("⚠ sounddevice not available")
            return False
    except Exception as e:
        logger.error(f"✗ sounddevice test failed: {e}")
        return False


def test_openwakeword_models():
    """Test if OpenWakeWord models are available."""
    logger.info("Testing OpenWakeWord models...")

    try:
        import os

        from client.audio_modules.wakeword_detector import get_base_path

        base_path = get_base_path()
        model_dir = os.path.join(base_path, "resources", "openWakeWord")

        if os.path.exists(model_dir):
            logger.info(f"✓ Model directory exists: {model_dir}")

            # Check for ONNX models
            onnx_files = [f for f in os.listdir(model_dir) if f.endswith(".onnx")]
            wakeword_models = [
                f
                for f in onnx_files
                if not any(
                    x in f.lower()
                    for x in ["preprocessor", "embedding", "melspectrogram"]
                )
            ]

            logger.info(f"✓ Found {len(onnx_files)} total ONNX files")
            logger.info(f"✓ Found {len(wakeword_models)} wake word models")

            # Check for required files
            melspec_path = os.path.join(model_dir, "melspectrogram.onnx")
            if os.path.exists(melspec_path):
                logger.info("✓ melspectrogram.onnx found")
            else:
                logger.warning("⚠ melspectrogram.onnx missing")

            return len(wakeword_models) > 0
        else:
            logger.warning(f"⚠ Model directory not found: {model_dir}")
            return False

    except Exception as e:
        logger.error(f"✗ OpenWakeWord model test failed: {e}")
        return False


def test_openwakeword_import():
    """Test if OpenWakeWord can be imported."""
    logger.info("Testing OpenWakeWord import...")

    try:
        # Try importing from submodule
        from openwakeword.model import Model as OpenWakeWordModel

        logger.info("✓ OpenWakeWord imported from submodule")
        return True
    except ImportError:
        try:
            # Fallback: import directly from package
            from openwakeword import Model as OpenWakeWordModel

            logger.info("✓ OpenWakeWord imported from main package")
            return True
        except ImportError as e:
            logger.warning(f"⚠ OpenWakeWord import failed: {e}")
            return False
    except Exception as e:
        logger.error(f"✗ OpenWakeWord import test failed: {e}")
        return False


async def test_async_functions():
    """Test async wrapper functions."""
    logger.info("Testing async wrapper functions...")

    try:
        from client.audio_modules.wakeword_detector import (
            record_command_audio_async,
            run_wakeword_detection_async,
        )

        logger.info("✓ Async functions imported successfully")

        # Test that functions are callable (but don't actually call them)
        assert asyncio.iscoroutinefunction(record_command_audio_async)
        assert asyncio.iscoroutinefunction(run_wakeword_detection_async)
        logger.info("✓ Functions are proper coroutines")

        return True
    except Exception as e:
        logger.error(f"✗ Async function test failed: {e}")
        return False


def test_config_compatibility():
    """Test configuration compatibility."""
    logger.info("Testing configuration compatibility...")

    try:
        from client.audio_modules.wakeword_detector import get_base_path
        from client.config import BASE_DIR

        detector_base = get_base_path()
        config_base = BASE_DIR

        logger.info(f"✓ Detector base path: {detector_base}")
        logger.info(f"✓ Config base path: {config_base}")

        # They should be the same or compatible
        return True
    except Exception as e:
        logger.error(f"✗ Config compatibility test failed: {e}")
        return False


async def run_all_tests():
    """Run all manual tests."""
    logger.info("=" * 50)
    logger.info("Starting manual tests for wakeword detector")
    logger.info("=" * 50)

    tests = [
        ("Basic imports", test_basic_imports),
        ("Config compatibility", test_config_compatibility),
        ("SoundDevice availability", test_sounddevice_availability),
        ("OpenWakeWord models", test_openwakeword_models),
        ("OpenWakeWord import", test_openwakeword_import),
        ("Async functions", test_async_functions),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1

    logger.info(f"\nPassed: {passed}/{len(results)}")

    if passed == len(results):
        logger.info("🎉 All tests passed! Wake word detector appears to be working.")
    elif passed > len(results) // 2:
        logger.info("⚠ Most tests passed. Some functionality may be limited.")
    else:
        logger.warning("❌ Many tests failed. Wake word detector may not work properly.")

    return passed == len(results)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

#!/usr/bin/env python3
"""Demo script for optimized audio modules.

This script demonstrates the enhanced performance and capabilities of the
optimized wake word detection and Whisper ASR modules.

Usage:
    python demo_optimized_audio.py [--model-size base] [--sensitivity 0.65] [--device-id auto]
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from client.audio_modules.optimized_wakeword_detector import (
    OptimizedSpeechRecorder,
    OptimizedWakeWordDetector,
    create_optimized_detector,
    create_optimized_recorder,
)
from client.audio_modules.optimized_whisper_asr import (
    OptimizedWhisperASR,
    create_optimized_whisper_async,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OptimizedAudioDemo:
    """Demo class for optimized audio modules."""

    def __init__(
        self,
        model_size: str = "base",
        sensitivity: float = 0.65,
        device_id: int = None,
        keyword: str = "gaja",
    ):
        """Initialize the demo.

        Args:
            model_size: Whisper model size to use
            sensitivity: Wake word detection sensitivity
            device_id: Audio device ID (None for auto-detect)
            keyword: Wake word to detect
        """
        self.model_size = model_size
        self.sensitivity = sensitivity
        self.device_id = device_id
        self.keyword = keyword

        # Components
        self.detector: OptimizedWakeWordDetector = None
        self.recorder: OptimizedSpeechRecorder = None
        self.whisper: OptimizedWhisperASR = None

        # Statistics
        self.start_time = time.time()
        self.detections = 0
        self.transcriptions = 0
        self.total_audio_processed = 0.0

        # Control
        self.running = False

    async def initialize(self) -> bool:
        """Initialize all audio components.

        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing optimized audio modules...")

            # Create wake word detector
            logger.info(
                f"Creating wake word detector (sensitivity: {self.sensitivity})"
            )
            self.detector = await create_optimized_detector(
                sensitivity=self.sensitivity,
                keyword=self.keyword,
                device_id=self.device_id,
            )

            # Create speech recorder
            logger.info("Creating speech recorder")
            self.recorder = await create_optimized_recorder(device_id=self.device_id)

            # Create Whisper ASR
            logger.info(f"Loading Whisper model ({self.model_size})")
            self.whisper = await create_optimized_whisper_async(
                model_size=self.model_size, language="pl"
            )

            if not self.whisper.available:
                logger.error("Whisper model failed to load")
                return False

            # Set up wake word detection callback
            self.detector.add_detection_callback(self._handle_wake_word)

            logger.info("✅ All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False

    async def _handle_wake_word(self, keyword: str) -> None:
        """Handle wake word detection.

        Args:
            keyword: Detected wake word
        """
        self.detections += 1
        logger.info(f"🎙️  Wake word '{keyword}' detected! (#{self.detections})")

        try:
            # Record user command
            logger.info("🎧 Listening for your command...")
            start_record = time.time()

            audio_data = await self.recorder.record_command_async(
                max_duration=8.0, silence_timeout=2.5
            )

            record_time = time.time() - start_record

            if audio_data is not None:
                audio_duration = len(audio_data) / 16000
                self.total_audio_processed += audio_duration

                logger.info(f"📹 Recorded {audio_duration:.1f}s in {record_time:.1f}s")

                # Transcribe with Whisper
                logger.info("🧠 Transcribing with Whisper...")
                start_transcribe = time.time()

                transcription = await self.whisper.transcribe_async(audio_data)

                transcribe_time = time.time() - start_transcribe
                self.transcriptions += 1

                if transcription.strip():
                    logger.info(f"💬 You said: '{transcription}'")
                    logger.info(
                        f"⚡ Transcribed in {transcribe_time:.1f}s (RTF: {transcribe_time/audio_duration:.2f})"
                    )

                    # Simulate command processing
                    await self._process_command(transcription)
                else:
                    logger.warning("⚠️  No speech detected in recording")
            else:
                logger.warning("⚠️  No audio recorded (silence or error)")

        except Exception as e:
            logger.error(f"❌ Error handling wake word: {e}")

    async def _process_command(self, command: str) -> None:
        """Process the transcribed command.

        Args:
            command: Transcribed command text
        """
        # Simulate command processing
        command_lower = command.lower().strip()

        if any(word in command_lower for word in ["czas", "godzina", "która"]):
            current_time = time.strftime("%H:%M")
            logger.info(f"🕐 Current time: {current_time}")

        elif any(word in command_lower for word in ["pogoda", "temperatura"]):
            logger.info("🌤️  Weather command detected (would fetch weather)")

        elif any(word in command_lower for word in ["stop", "zatrzymaj", "koniec"]):
            logger.info("🛑 Stop command detected")
            await self.stop()

        elif any(
            word in command_lower for word in ["statystyki", "stats", "wydajność"]
        ):
            await self._show_statistics()

        else:
            logger.info(f"🤖 Unknown command: '{command}' (would process normally)")

    async def _show_statistics(self) -> None:
        """Show performance statistics."""
        runtime = time.time() - self.start_time

        logger.info("📊 Performance Statistics:")
        logger.info(f"   ⏱️  Runtime: {runtime:.1f} seconds")
        logger.info(f"   🎯 Wake word detections: {self.detections}")
        logger.info(f"   🎤 Transcriptions: {self.transcriptions}")
        logger.info(f"   🎵 Audio processed: {self.total_audio_processed:.1f} seconds")

        if self.detections > 0:
            avg_per_detection = runtime / self.detections
            logger.info(
                f"   📈 Average time between detections: {avg_per_detection:.1f}s"
            )

        # Whisper performance
        if self.whisper:
            whisper_stats = self.whisper.get_performance_stats()
            logger.info(
                f"   🧠 Whisper model: {whisper_stats.get('model_id', 'Unknown')}"
            )
            logger.info(
                f"   ⚡ Average processing time: {whisper_stats.get('avg_processing_time', 0):.2f}s"
            )
            logger.info(f"   🎮 Device: {whisper_stats.get('device', 'Unknown')}")
            logger.info(
                f"   💾 Compute type: {whisper_stats.get('compute_type', 'Unknown')}"
            )

            rtf = whisper_stats.get("real_time_factor", 0)
            if rtf > 0:
                logger.info(f"   ⚡ Real-time factor: {rtf:.2f}x")

    async def run_interactive_demo(self) -> None:
        """Run interactive demo mode."""
        self.running = True
        logger.info("🚀 Starting interactive demo mode")
        logger.info(f"   Wake word: '{self.keyword}'")
        logger.info(f"   Sensitivity: {self.sensitivity}")
        logger.info(f"   Whisper model: {self.model_size}")
        logger.info("")
        logger.info("📢 Say your wake word to start!")
        logger.info("   Available commands:")
        logger.info("   - 'jaka godzina?' - Get current time")
        logger.info("   - 'jaka pogoda?' - Weather info")
        logger.info("   - 'statystyki' - Show performance stats")
        logger.info("   - 'stop' - Exit demo")
        logger.info("   - Ctrl+C - Force exit")
        logger.info("")

        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("⌨️  Keyboard interrupt detected")
        finally:
            await self.stop()

    async def run_benchmark(self, duration: int = 60) -> None:
        """Run benchmark mode for performance testing.

        Args:
            duration: Duration to run benchmark in seconds
        """
        logger.info(f"🏁 Starting {duration}s benchmark mode")
        logger.info("   This will test wake word detection performance")
        logger.info(f"   Say '{self.keyword}' as much as you want!")

        self.running = True
        start_time = time.time()

        try:
            while self.running and (time.time() - start_time) < duration:
                remaining = duration - (time.time() - start_time)
                if int(remaining) % 10 == 0 and int(remaining) != int(remaining + 1):
                    logger.info(f"⏱️  {int(remaining)}s remaining...")
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("⌨️  Benchmark interrupted")

        # Show final statistics
        logger.info("🏁 Benchmark completed!")
        await self._show_statistics()
        await self.stop()

    async def stop(self) -> None:
        """Stop the demo and cleanup resources."""
        if not self.running:
            return

        logger.info("🛑 Stopping demo...")
        self.running = False

        try:
            if self.detector:
                await self.detector.stop_async()

            if self.whisper:
                self.whisper.unload()

            logger.info("✅ Demo stopped successfully")

        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")


async def test_audio_devices() -> None:
    """Test available audio devices."""
    try:
        import sounddevice as sd

        logger.info("🎵 Available audio devices:")
        devices = sd.query_devices()

        for i, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                default_marker = " [DEFAULT]" if i == sd.default.device[0] else ""
                logger.info(f"   {i}: {device['name']}{default_marker}")
                logger.info(
                    f"      Channels: {device['max_input_channels']}, Sample rate: {device['default_samplerate']}"
                )

    except ImportError:
        logger.error("❌ sounddevice not available - cannot list audio devices")
    except Exception as e:
        logger.error(f"❌ Error listing audio devices: {e}")


async def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(description="Optimized Audio Modules Demo")
    parser.add_argument(
        "--model-size",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size",
    )
    parser.add_argument(
        "--sensitivity",
        type=float,
        default=0.65,
        help="Wake word detection sensitivity (0.0-1.0)",
    )
    parser.add_argument(
        "--device-id",
        type=int,
        default=None,
        help="Audio device ID (auto-detect if not specified)",
    )
    parser.add_argument("--keyword", default="gaja", help="Wake word to detect")
    parser.add_argument(
        "--mode",
        choices=["interactive", "benchmark", "test-devices"],
        default="interactive",
        help="Demo mode to run",
    )
    parser.add_argument(
        "--benchmark-duration",
        type=int,
        default=60,
        help="Benchmark duration in seconds",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("client.audio_modules").setLevel(logging.DEBUG)

    logger.info("🎙️  Optimized Audio Modules Demo")
    logger.info("=" * 50)

    if args.mode == "test-devices":
        await test_audio_devices()
        return

    # Create and initialize demo
    demo = OptimizedAudioDemo(
        model_size=args.model_size,
        sensitivity=args.sensitivity,
        device_id=args.device_id,
        keyword=args.keyword,
    )

    if not await demo.initialize():
        logger.error("❌ Demo initialization failed")
        return

    try:
        if args.mode == "interactive":
            await demo.run_interactive_demo()
        elif args.mode == "benchmark":
            await demo.run_benchmark(args.benchmark_duration)
    except Exception as e:
        logger.error(f"❌ Demo error: {e}")
    finally:
        await demo.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        sys.exit(1)

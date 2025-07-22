"""Tests for wakeword_detector module.

Tests the wake word detection functionality with proper mocking to avoid requiring
actual audio hardware during testing.
"""

import asyncio
import os
import sys
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies before importing the module
with patch.dict(
    "sys.modules",
    {
        "config": MagicMock(BASE_DIR="/test/base"),
        "sounddevice": MagicMock(),
        "openwakeword": MagicMock(),
        "openwakeword.model": MagicMock(),
    },
):
    from client.audio_modules.wakeword_detector import (
        CHUNK_DURATION_MS,
        CHUNK_SAMPLES,
        MIN_COMMAND_AUDIO_CHUNKS,
        SAMPLE_RATE,
        VAD_SILENCE_AMPLITUDE_THRESHOLD,
        get_base_path,
        record_command_audio,
        record_command_audio_async,
        run_wakeword_detection,
        run_wakeword_detection_async,
    )


class TestWakewordDetector:
    """Test suite for wakeword detector functionality."""

    def test_constants_defined(self):
        """Test that all required constants are properly defined."""
        assert SAMPLE_RATE == 16000
        assert CHUNK_DURATION_MS == 50
        assert CHUNK_SAMPLES == int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)
        assert MIN_COMMAND_AUDIO_CHUNKS == 40
        assert VAD_SILENCE_AMPLITUDE_THRESHOLD == 0.01

    def test_get_base_path_development(self):
        """Test get_base_path in development mode."""
        with patch("sys.frozen", False, create=True):
            base_path = get_base_path()
            assert isinstance(base_path, str)
            assert len(base_path) > 0

    def test_get_base_path_frozen(self):
        """Test get_base_path in frozen/bundled mode."""
        with patch("sys.frozen", True, create=True):
            with patch("client.audio_modules.wakeword_detector.BASE_DIR", "/test/base"):
                base_path = get_base_path()
                assert base_path == "/test/base"

    @patch("client.audio_modules.wakeword_detector.SOUNDDEVICE_AVAILABLE", False)
    @patch("client.audio_modules.wakeword_detector.play_beep")
    def test_record_command_audio_no_sounddevice(self, mock_play_beep):
        """Test record_command_audio when sounddevice is not available."""
        stop_event = threading.Event()
        result = record_command_audio(0, 2000, stop_event)
        assert result is None
        mock_play_beep.assert_called_once_with("error", loop=False)

    @patch("client.audio_modules.wakeword_detector.SOUNDDEVICE_AVAILABLE", True)
    @patch("client.audio_modules.wakeword_detector.sd")
    @patch("client.audio_modules.wakeword_detector.play_beep")
    def test_record_command_audio_success(self, mock_play_beep, mock_sd):
        """Test successful command audio recording."""
        # Mock audio stream
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=None)

        # Create sample audio data that will trigger voice detection
        sample_audio = np.ones((CHUNK_SAMPLES, 1), dtype=np.float32) * 0.1
        # Mock stream.read to return proper tuple (audio_data, overflowed)
        mock_stream.read.return_value = (sample_audio, False)

        mock_sd.InputStream.return_value = mock_stream
        # Mock PortAudioError as a proper exception class
        mock_sd.PortAudioError = Exception

        stop_event = threading.Event()

        # Set stop event after some time to prevent infinite loop
        def set_stop_after_delay():
            time.sleep(0.1)
            stop_event.set()

        threading.Thread(target=set_stop_after_delay, daemon=True).start()

        result = record_command_audio(0, 100, stop_event)  # Short silence threshold

        # Should have recorded some audio
        assert result is not None
        assert isinstance(result, np.ndarray)

    @patch("client.audio_modules.wakeword_detector.SOUNDDEVICE_AVAILABLE", True)
    @patch("client.audio_modules.wakeword_detector.sd")
    @patch("client.audio_modules.wakeword_detector.play_beep")
    def test_record_command_audio_silence_detection(self, mock_play_beep, mock_sd):
        """Test command audio recording with silence detection."""
        # Mock audio stream
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=None)

        # Create audio sequence: some voice, then silence
        voice_audio = np.ones((CHUNK_SAMPLES, 1), dtype=np.float32) * 0.1
        silence_audio = np.zeros((CHUNK_SAMPLES, 1), dtype=np.float32)

        # Return voice first, then silence to trigger VAD
        audio_sequence = [
            (voice_audio, False) for _ in range(MIN_COMMAND_AUDIO_CHUNKS)
        ] + [
            (silence_audio, False) for _ in range(10)  # Enough silence to trigger stop
        ]

        mock_stream.read.side_effect = audio_sequence
        mock_sd.InputStream.return_value = mock_stream
        # Mock PortAudioError as a proper exception class
        mock_sd.PortAudioError = Exception

        stop_event = threading.Event()
        result = record_command_audio(0, 200, stop_event)  # 200ms silence threshold

        # Should have recorded audio and detected silence
        assert result is not None
        assert isinstance(result, np.ndarray)

    @pytest.mark.asyncio
    async def test_record_command_audio_async(self):
        """Test async wrapper for record_command_audio."""
        with patch(
            "client.audio_modules.wakeword_detector.record_command_audio"
        ) as mock_record:
            mock_record.return_value = np.array([1, 2, 3])

            stop_event = threading.Event()
            result = await record_command_audio_async(0, 2000, stop_event)

            assert np.array_equal(result, np.array([1, 2, 3]))
            mock_record.assert_called_once_with(0, 2000, stop_event)

    @patch("client.audio_modules.wakeword_detector.SOUNDDEVICE_AVAILABLE", False)
    @patch("client.audio_modules.wakeword_detector.play_beep")
    def test_run_wakeword_detection_no_sounddevice(self, mock_play_beep):
        """Test run_wakeword_detection when sounddevice is not available."""
        result = run_wakeword_detection(
            mic_device_id=0,
            stt_silence_threshold_ms=2000,
            wake_word_config_name="test",
            tts_module=None,
            process_query_callback_async=None,
            async_event_loop=None,
            oww_sensitivity_threshold=0.6,
            whisper_asr_instance=None,
            manual_listen_trigger_event=threading.Event(),
            stop_detector_event=threading.Event(),
        )

        assert result is None
        mock_play_beep.assert_called_once_with("error", loop=False)

    @patch("client.audio_modules.wakeword_detector.SOUNDDEVICE_AVAILABLE", True)
    def test_run_wakeword_detection_no_openwakeword(self):
        """Test run_wakeword_detection when OpenWakeWord is not available."""
        with patch(
            "builtins.__import__",
            side_effect=ImportError("No module named 'openwakeword'"),
        ):
            result = run_wakeword_detection(
                mic_device_id=0,
                stt_silence_threshold_ms=2000,
                wake_word_config_name="test",
                tts_module=None,
                process_query_callback_async=None,
                async_event_loop=None,
                oww_sensitivity_threshold=0.6,
                whisper_asr_instance=None,
                manual_listen_trigger_event=threading.Event(),
                stop_detector_event=threading.Event(),
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_run_wakeword_detection_async(self):
        """Test async wrapper for run_wakeword_detection."""
        with patch(
            "client.audio_modules.wakeword_detector.run_wakeword_detection"
        ) as mock_run:
            mock_run.return_value = None

            stop_event = threading.Event()
            manual_event = threading.Event()

            result = await run_wakeword_detection_async(
                mic_device_id=0,
                stt_silence_threshold_ms=2000,
                wake_word_config_name="test",
                tts_module=None,
                process_query_callback_async=None,
                async_event_loop=None,
                oww_sensitivity_threshold=0.6,
                whisper_asr_instance=None,
                manual_listen_trigger_event=manual_event,
                stop_detector_event=stop_event,
            )

            assert result is None
            mock_run.assert_called_once()

    @patch("client.audio_modules.wakeword_detector.SOUNDDEVICE_AVAILABLE", True)
    @patch("client.audio_modules.wakeword_detector.sd")
    @patch("os.path.exists")
    def test_run_wakeword_detection_no_model_dir(self, mock_exists, mock_sd):
        """Test run_wakeword_detection when model directory doesn't exist."""
        mock_exists.return_value = False

        # Mock OpenWakeWord import to succeed
        mock_model = MagicMock()
        with patch("builtins.__import__") as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == "openwakeword.model":
                    mock_module = MagicMock()
                    mock_module.Model = mock_model
                    return mock_module
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            result = run_wakeword_detection(
                mic_device_id=0,
                stt_silence_threshold_ms=2000,
                wake_word_config_name="test",
                tts_module=None,
                process_query_callback_async=None,
                async_event_loop=None,
                oww_sensitivity_threshold=0.6,
                whisper_asr_instance=None,
                manual_listen_trigger_event=threading.Event(),
                stop_detector_event=threading.Event(),
            )

            assert result is None

    def test_vad_parameters_validity(self):
        """Test that VAD parameters are within reasonable ranges."""
        # VAD silence threshold should be reasonable for float32 audio
        assert 0.001 <= VAD_SILENCE_AMPLITUDE_THRESHOLD <= 0.1

        # Chunk duration should be reasonable for real-time processing
        assert 10 <= CHUNK_DURATION_MS <= 100

        # Minimum command audio should be enough for meaningful speech
        assert MIN_COMMAND_AUDIO_CHUNKS >= 20  # At least 1 second at 50ms chunks

    @patch("client.audio_modules.wakeword_detector.logger")
    def test_logging_functionality(self, mock_logger):
        """Test that proper logging occurs in various scenarios."""
        with patch(
            "client.audio_modules.wakeword_detector.SOUNDDEVICE_AVAILABLE", False
        ):
            with patch("client.audio_modules.wakeword_detector.play_beep"):
                record_command_audio(0, 2000, threading.Event())

                # Check that error was logged
                mock_logger.error.assert_called_with(
                    "SoundDevice not available - cannot record command audio"
                )


class TestWakewordDetectorIntegration:
    """Integration tests for wakeword detector that test the full pipeline."""

    @pytest.mark.asyncio
    @patch("client.audio_modules.wakeword_detector.SOUNDDEVICE_AVAILABLE", True)
    @patch("client.audio_modules.wakeword_detector.sd")
    @patch("os.path.exists")
    @patch("os.listdir")
    async def test_manual_trigger_flow(self, mock_listdir, mock_exists, mock_sd):
        """Test the manual trigger flow end-to-end."""
        # Setup mocks
        mock_exists.return_value = True
        mock_listdir.return_value = ["test.onnx", "melspectrogram.onnx"]

        # Mock OpenWakeWord model
        mock_model_instance = MagicMock()
        mock_model_instance.expected_frame_length = 1280
        mock_model_instance.predict.return_value = {"test": 0.5}
        mock_model_instance.reset = MagicMock()

        mock_model_class = MagicMock(return_value=mock_model_instance)

        # Mock audio stream
        mock_stream = MagicMock()
        mock_stream.closed = False
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=None)
        mock_sd.InputStream.return_value = mock_stream

        # Mock query devices
        mock_device = {"max_input_channels": 1, "name": "Test Mic"}
        mock_sd.query_devices.return_value = [mock_device]

        # Mock callback
        process_callback = AsyncMock()

        # Mock TTS module
        mock_tts = MagicMock()

        # Mock Whisper ASR
        mock_whisper = MagicMock()
        mock_whisper.transcribe.return_value = "test query"

        # Create events
        manual_event = threading.Event()
        stop_event = threading.Event()

        # Import and patch OpenWakeWord
        with patch("builtins.__import__") as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == "openwakeword.model":
                    mock_module = MagicMock()
                    mock_module.Model = mock_model_class
                    return mock_module
                elif name == "openwakeword":
                    mock_module = MagicMock()
                    mock_module.Model = mock_model_class
                    return mock_module
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            # Patch record_command_audio to return test data
            with patch(
                "client.audio_modules.wakeword_detector.record_command_audio"
            ) as mock_record:
                mock_record.return_value = np.array([0.1, 0.2, 0.3])

                with patch("client.audio_modules.wakeword_detector.play_beep"):
                    # Set manual trigger and then stop after short delay
                    def trigger_and_stop():
                        time.sleep(0.1)
                        manual_event.set()
                        time.sleep(0.1)
                        stop_event.set()

                    threading.Thread(target=trigger_and_stop, daemon=True).start()

                    # Run the detection
                    result = await run_wakeword_detection_async(
                        mic_device_id=0,
                        stt_silence_threshold_ms=2000,
                        wake_word_config_name="test",
                        tts_module=mock_tts,
                        process_query_callback_async=process_callback,
                        async_event_loop=asyncio.get_event_loop(),
                        oww_sensitivity_threshold=0.6,
                        whisper_asr_instance=mock_whisper,
                        manual_listen_trigger_event=manual_event,
                        stop_detector_event=stop_event,
                    )

                    # Should complete without error
                    assert result is None

                    # Give some time for async operations to complete
                    await asyncio.sleep(0.2)


if __name__ == "__main__":
    pytest.main([__file__])

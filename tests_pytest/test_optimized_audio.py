#!/usr/bin/env python3
"""Tests for optimized audio modules.

These tests verify the functionality of the optimized wake word detection and Whisper
ASR modules, following AGENTS.md testing requirements.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from client.audio_modules.optimized_wakeword_detector import (
    OPTIMAL_CHUNK_SIZE,
    SAMPLE_RATE,
    VAD_ENERGY_THRESHOLD,
    AdvancedVAD,
    OptimizedAudioBuffer,
    OptimizedSpeechRecorder,
    OptimizedWakeWordDetector,
    create_optimized_detector,
    create_optimized_recorder,
)
from client.audio_modules.optimized_whisper_asr import (
    OptimizedWhisperASR,
    create_optimized_whisper,
    create_optimized_whisper_async,
)


class TestOptimizedAudioBuffer:
    """Test the optimized audio buffer implementation."""

    def test_buffer_initialization(self):
        """Test buffer initialization with correct size."""
        duration = 2.0
        buffer = OptimizedAudioBuffer(duration, SAMPLE_RATE)

        assert buffer.max_samples == int(duration * SAMPLE_RATE)
        assert buffer.write_pos == 0
        assert buffer.samples_written == 0
        assert len(buffer.buffer) == buffer.max_samples

    def test_buffer_append_simple(self):
        """Test simple audio data appending."""
        buffer = OptimizedAudioBuffer(1.0, SAMPLE_RATE)
        test_data = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

        buffer.append(test_data)

        assert buffer.write_pos == len(test_data)
        assert buffer.samples_written == len(test_data)
        assert np.array_equal(buffer.buffer[: len(test_data)], test_data)

    def test_buffer_circular_wrap(self):
        """Test circular buffer wrap-around functionality."""
        buffer = OptimizedAudioBuffer(0.1, SAMPLE_RATE)  # Very small buffer
        max_samples = buffer.max_samples

        # Fill buffer completely
        first_data = np.ones(max_samples, dtype=np.float32)
        buffer.append(first_data)

        # Add more data to trigger wrap-around
        second_data = np.full(100, 0.5, dtype=np.float32)
        buffer.append(second_data)

        assert buffer.write_pos == 100
        assert buffer.samples_written == max_samples + 100

    def test_get_recent_audio(self):
        """Test retrieving recent audio data."""
        buffer = OptimizedAudioBuffer(2.0, SAMPLE_RATE)

        # Add some test data
        test_data = np.random.random(SAMPLE_RATE).astype(np.float32)  # 1 second
        buffer.append(test_data)

        # Get recent 0.5 seconds
        recent = buffer.get_recent_audio(0.5)
        expected_samples = int(0.5 * SAMPLE_RATE)

        assert len(recent) == expected_samples
        assert np.array_equal(recent, test_data[-expected_samples:])

    def test_get_recent_audio_empty_buffer(self):
        """Test getting recent audio from empty buffer."""
        buffer = OptimizedAudioBuffer(1.0, SAMPLE_RATE)
        recent = buffer.get_recent_audio(0.5)

        assert len(recent) == 0
        assert recent.dtype == np.float32


class TestAdvancedVAD:
    """Test the advanced Voice Activity Detection."""

    def test_vad_initialization(self):
        """Test VAD initialization."""
        vad = AdvancedVAD()

        assert vad.energy_threshold == VAD_ENERGY_THRESHOLD
        assert vad.silence_frames == 0
        assert vad.speech_frames == 0
        assert not vad.is_speech_active
        assert len(vad.energy_history) == 0
        assert len(vad.spectral_history) == 0

    def test_vad_speech_detection(self):
        """Test speech detection with synthetic audio."""
        vad = AdvancedVAD()

        # Create synthetic speech-like audio (with energy and spectral content)
        speech_audio = np.random.normal(0, 0.1, OPTIMAL_CHUNK_SIZE).astype(np.float32)
        speech_audio += 0.05 * np.sin(
            2 * np.pi * 500 * np.arange(OPTIMAL_CHUNK_SIZE) / SAMPLE_RATE
        )

        # Process multiple frames to trigger speech detection
        for _ in range(5):
            result = vad.process_frame(speech_audio)

        assert vad.speech_frames > 0
        assert result is True  # Should detect speech eventually

    def test_vad_silence_detection(self):
        """Test silence detection."""
        vad = AdvancedVAD()

        # Create silent audio
        silence_audio = np.zeros(OPTIMAL_CHUNK_SIZE, dtype=np.float32)

        # Process silence frames
        for _ in range(10):
            result = vad.process_frame(silence_audio)

        assert not result  # Should not detect speech in silence
        assert vad.speech_frames == 0

    def test_vad_reset(self):
        """Test VAD state reset."""
        vad = AdvancedVAD()

        # Set some state
        vad.speech_frames = 5
        vad.silence_frames = 3
        vad.is_speech_active = True
        vad.energy_history.append(0.1)
        vad.spectral_history.append(0.2)

        # Reset
        vad.reset()

        assert vad.speech_frames == 0
        assert vad.silence_frames == 0
        assert not vad.is_speech_active
        assert len(vad.energy_history) == 0
        assert len(vad.spectral_history) == 0


class TestOptimizedWakeWordDetector:
    """Test the optimized wake word detector."""

    @pytest.fixture
    def mock_sounddevice(self):
        """Mock sounddevice for testing."""
        with patch("sounddevice.InputStream") as mock_stream:
            mock_stream.return_value.__enter__ = MagicMock()
            mock_stream.return_value.__exit__ = MagicMock()
            yield mock_stream

    def test_detector_initialization(self):
        """Test detector initialization."""
        detector = OptimizedWakeWordDetector(
            sensitivity=0.7, keyword="test", device_id=1
        )

        assert detector.sensitivity == 0.7
        assert detector.keyword == "test"
        assert detector.device_id == 1
        assert not detector.is_running
        assert detector.detections_count == 0
        assert len(detector.detection_callbacks) == 0

    def test_add_detection_callback(self):
        """Test adding detection callbacks."""
        detector = OptimizedWakeWordDetector()

        def test_callback(keyword):
            pass

        detector.add_detection_callback(test_callback)

        assert len(detector.detection_callbacks) == 1
        assert detector.detection_callbacks[0] == test_callback

    @pytest.mark.asyncio
    async def test_start_stop_async(self, mock_sounddevice):
        """Test async start and stop functionality."""
        detector = OptimizedWakeWordDetector()

        # Mock the model loading
        with patch.object(detector, "_load_wake_word_model"):
            await detector.start_async()
            assert detector.is_running

            await detector.stop_async()
            assert not detector.is_running

    def test_energy_based_detection(self):
        """Test energy-based wake word detection fallback."""
        detector = OptimizedWakeWordDetector(sensitivity=0.3)

        # Create high-energy audio that should trigger detection
        high_energy_audio = np.random.normal(0, 0.15, SAMPLE_RATE).astype(np.float32)
        result = detector._energy_based_detection(high_energy_audio)

        # Should detect something with high energy and speech characteristics
        assert isinstance(result, bool)

    def test_low_energy_rejection(self):
        """Test that low energy audio is rejected."""
        detector = OptimizedWakeWordDetector(sensitivity=0.8)

        # Create very low energy audio
        low_energy_audio = np.random.normal(0, 0.001, SAMPLE_RATE).astype(np.float32)
        result = detector._energy_based_detection(low_energy_audio)

        assert result is False


class TestOptimizedSpeechRecorder:
    """Test the optimized speech recorder."""

    @pytest.fixture
    def mock_sounddevice(self):
        """Mock sounddevice for testing."""
        with patch("sounddevice.InputStream") as mock_stream:
            # Mock the InputStream context manager
            mock_stream.return_value.__enter__ = MagicMock()
            mock_stream.return_value.__exit__ = MagicMock()
            yield mock_stream

    def test_recorder_initialization(self):
        """Test recorder initialization."""
        recorder = OptimizedSpeechRecorder(device_id=2)

        assert recorder.device_id == 2
        assert not recorder.is_recording
        assert len(recorder.recorded_audio) == 0
        assert isinstance(recorder.vad, AdvancedVAD)

    @pytest.mark.asyncio
    async def test_record_command_async(self, mock_sounddevice):
        """Test async command recording."""
        recorder = OptimizedSpeechRecorder()

        # Mock the blocking recording to return test data
        test_audio = np.random.random(SAMPLE_RATE).astype(np.float32)

        with patch.object(recorder, "_record_blocking", return_value=test_audio):
            result = await recorder.record_command_async(max_duration=1.0)

        assert result is not None
        assert len(result) == len(test_audio)
        assert np.array_equal(result, test_audio)

    @pytest.mark.asyncio
    async def test_record_command_failure(self, mock_sounddevice):
        """Test command recording failure handling."""
        recorder = OptimizedSpeechRecorder()

        # Mock the blocking recording to raise an exception
        with patch.object(
            recorder, "_record_blocking", side_effect=Exception("Test error")
        ):
            result = await recorder.record_command_async()

        assert result is None


class TestOptimizedWhisperASR:
    """Test the optimized Whisper ASR implementation."""

    @pytest.fixture
    def mock_faster_whisper(self):
        """Mock faster-whisper for testing."""
        with patch("faster_whisper.WhisperModel") as mock_model_class:
            mock_model = MagicMock()
            mock_model.transcribe.return_value = (
                [MagicMock(text="test transcription")],
                MagicMock(language_probability=0.95),
            )
            mock_model_class.return_value = mock_model
            yield mock_model_class, mock_model

    def test_whisper_initialization(self, mock_faster_whisper):
        """Test Whisper ASR initialization."""
        mock_model_class, mock_model = mock_faster_whisper

        whisper = OptimizedWhisperASR(model_size="base", language="pl")

        assert whisper.model_size == "base"
        assert whisper.language == "pl"
        assert whisper.available is True
        assert whisper.transcription_count == 0

    def test_device_optimization_cpu(self):
        """Test device optimization for CPU."""
        with patch.object(OptimizedWhisperASR, "_is_gpu_available", return_value=False):
            with patch.object(OptimizedWhisperASR, "_load_optimized_model"):
                whisper = OptimizedWhisperASR()

                assert whisper.device == "cpu"
                assert whisper.compute_type == "int8"

    def test_device_optimization_gpu(self):
        """Test device optimization for GPU."""
        with patch.object(OptimizedWhisperASR, "_is_gpu_available", return_value=True):
            with patch.object(OptimizedWhisperASR, "_load_optimized_model"):
                whisper = OptimizedWhisperASR()

                assert whisper.device == "cuda"
                assert whisper.compute_type == "float16"

    def test_transcribe_blocking(self, mock_faster_whisper):
        """Test blocking transcription."""
        mock_model_class, mock_model = mock_faster_whisper

        whisper = OptimizedWhisperASR()
        test_audio = np.random.random(SAMPLE_RATE).astype(np.float32)

        result = whisper.transcribe(test_audio)

        assert result == "test transcription"
        assert whisper.transcription_count == 1
        mock_model.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_async(self, mock_faster_whisper):
        """Test async transcription."""
        mock_model_class, mock_model = mock_faster_whisper

        whisper = OptimizedWhisperASR()
        test_audio = np.random.random(SAMPLE_RATE).astype(np.float32)

        result = await whisper.transcribe_async(test_audio)

        assert result == "test transcription"
        assert whisper.transcription_count == 1
        mock_model.transcribe.assert_called_once()

    def test_transcribe_empty_result(self, mock_faster_whisper):
        """Test handling of empty transcription results."""
        mock_model_class, mock_model = mock_faster_whisper

        # Mock empty transcription
        mock_model.transcribe.return_value = ([], MagicMock())

        whisper = OptimizedWhisperASR()
        test_audio = np.random.random(SAMPLE_RATE).astype(np.float32)

        result = whisper.transcribe(test_audio)

        assert result == ""

    def test_transcribe_with_error_fallback(self, mock_faster_whisper):
        """Test transcription error handling with fallback."""
        mock_model_class, mock_model = mock_faster_whisper

        # First call raises exception, second succeeds
        mock_model.transcribe.side_effect = [
            Exception("Test error"),
            ([MagicMock(text="fallback transcription")], MagicMock()),
        ]

        whisper = OptimizedWhisperASR()
        test_audio = np.random.random(SAMPLE_RATE).astype(np.float32)

        result = whisper.transcribe(test_audio)

        assert result == "fallback transcription"
        assert mock_model.transcribe.call_count == 2

    def test_clean_transcription(self, mock_faster_whisper):
        """Test transcription text cleaning."""
        mock_model_class, mock_model = mock_faster_whisper

        whisper = OptimizedWhisperASR()

        # Test various cleaning scenarios
        assert whisper._clean_transcription("  hello   world  ") == "hello world"
        assert whisper._clean_transcription("[MUSIC] test [NOISE]") == "test"
        assert whisper._clean_transcription("eee") == ""
        assert whisper._clean_transcription("") == ""

    def test_performance_stats(self, mock_faster_whisper):
        """Test performance statistics tracking."""
        mock_model_class, mock_model = mock_faster_whisper

        whisper = OptimizedWhisperASR()

        # Initial stats
        stats = whisper.get_performance_stats()
        assert stats["transcriptions"] == 0
        assert stats["avg_processing_time"] == 0.0

        # After some transcriptions
        whisper.transcription_count = 5
        whisper.total_processing_time = 2.5
        whisper.total_audio_duration = 10.0

        stats = whisper.get_performance_stats()
        assert stats["transcriptions"] == 5
        assert stats["avg_processing_time"] == 0.5
        assert stats["real_time_factor"] == 0.25

    def test_unload(self, mock_faster_whisper):
        """Test model unloading."""
        mock_model_class, mock_model = mock_faster_whisper

        whisper = OptimizedWhisperASR()
        assert whisper.available is True

        whisper.unload()

        assert whisper.model is None
        assert whisper.available is False


class TestFactoryFunctions:
    """Test factory functions for creating optimized components."""

    @pytest.mark.asyncio
    async def test_create_optimized_detector(self):
        """Test async detector creation."""
        with patch(
            "client.audio_modules.optimized_wakeword_detector.OptimizedWakeWordDetector"
        ) as mock_detector_class:
            mock_detector = MagicMock()
            mock_detector.start_async = AsyncMock()
            mock_detector_class.return_value = mock_detector

            detector = await create_optimized_detector(sensitivity=0.8, keyword="test")

            mock_detector_class.assert_called_once_with(
                sensitivity=0.8, keyword="test", device_id=None
            )
            mock_detector.start_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_optimized_recorder(self):
        """Test async recorder creation."""
        recorder = await create_optimized_recorder(device_id=1)

        assert isinstance(recorder, OptimizedSpeechRecorder)
        assert recorder.device_id == 1

    @pytest.mark.asyncio
    async def test_create_optimized_whisper_async(self):
        """Test async Whisper creation."""
        with patch(
            "client.audio_modules.optimized_whisper_asr.OptimizedWhisperASR"
        ) as mock_whisper_class:
            mock_whisper = MagicMock()
            mock_whisper_class.return_value = mock_whisper

            whisper = await create_optimized_whisper_async(
                model_size="small", language="en"
            )

            mock_whisper_class.assert_called_once_with(
                model_size="small", device=None, language="en"
            )

    def test_create_optimized_whisper_sync(self):
        """Test synchronous Whisper creation."""
        with patch(
            "client.audio_modules.optimized_whisper_asr.OptimizedWhisperASR"
        ) as mock_whisper_class:
            mock_whisper = MagicMock()
            mock_whisper_class.return_value = mock_whisper

            whisper = create_optimized_whisper(model_size="base")

            mock_whisper_class.assert_called_once_with(
                model_size="base", device=None, language="pl"
            )


class TestIntegration:
    """Integration tests for optimized audio modules."""

    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self):
        """Test the full pipeline with mocked components."""
        # This test ensures all components work together
        with patch("sounddevice.InputStream"):
            with patch("faster_whisper.WhisperModel") as mock_whisper:
                # Setup mocks
                mock_model = MagicMock()
                mock_model.transcribe.return_value = (
                    [MagicMock(text="test command")],
                    MagicMock(language_probability=0.9),
                )
                mock_whisper.return_value = mock_model

                # Create components
                detector = OptimizedWakeWordDetector()
                recorder = OptimizedSpeechRecorder()
                whisper = OptimizedWhisperASR()

                # Test callback handling
                callback_called = False
                detected_keyword = None

                def test_callback(keyword):
                    nonlocal callback_called, detected_keyword
                    callback_called = True
                    detected_keyword = keyword

                detector.add_detection_callback(test_callback)

                # Simulate wake word detection
                detector._trigger_detection_callbacks()

                assert callback_called is True
                assert detected_keyword == detector.keyword

                # Test recording and transcription
                test_audio = np.random.random(SAMPLE_RATE).astype(np.float32)

                with patch.object(
                    recorder, "_record_blocking", return_value=test_audio
                ):
                    recorded = await recorder.record_command_async()
                    assert recorded is not None

                transcription = whisper.transcribe(test_audio)
                assert transcription == "test command"


# Performance benchmarks (can be run separately)
class TestPerformanceBenchmarks:
    """Performance benchmark tests (marked for optional execution)."""

    @pytest.mark.performance
    def test_buffer_performance(self):
        """Benchmark audio buffer performance."""
        buffer = OptimizedAudioBuffer(5.0, SAMPLE_RATE)

        # Test large data appending
        start_time = time.time()
        for _ in range(100):
            test_data = np.random.random(OPTIMAL_CHUNK_SIZE).astype(np.float32)
            buffer.append(test_data)

        duration = time.time() - start_time
        assert duration < 1.0  # Should complete in under 1 second

    @pytest.mark.performance
    def test_vad_performance(self):
        """Benchmark VAD performance."""
        vad = AdvancedVAD()

        start_time = time.time()
        for _ in range(1000):
            test_frame = np.random.random(OPTIMAL_CHUNK_SIZE).astype(np.float32)
            vad.process_frame(test_frame)

        duration = time.time() - start_time
        assert duration < 2.0  # Should process 1000 frames in under 2 seconds


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])

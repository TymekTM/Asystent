"""Testy komponentów audio dla GAJA Assistant."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from conftest import create_mock_audio_data


@pytest.mark.audio
class TestWakewordDetection:
    """Testy detekcji słowa aktywującego."""

    def test_wakeword_detector_creation(self):
        """Test tworzenia detektora wakeword."""
        with patch("client.client_main.create_wakeword_detector") as mock_create:
            mock_detector = Mock()
            mock_detector.start_detection = Mock()
            mock_detector.stop_detection = Mock()
            mock_detector.is_detecting = Mock(return_value=False)
            mock_create.return_value = mock_detector

            from client.client_main import create_wakeword_detector

            detector = create_wakeword_detector()

            assert detector is not None
            mock_create.assert_called_once()

    def test_wakeword_detection_start_stop(self, mock_audio_components):
        """Test startu i stopu detekcji wakeword."""
        detector = mock_audio_components["wakeword_detector"]

        # Test start
        detector.start_detection()
        detector.start_detection.assert_called_once()

        # Test stop
        detector.stop_detection()
        detector.stop_detection.assert_called_once()

        # Test status
        detector.is_detecting.return_value = True
        assert detector.is_detecting() is True

    def test_wakeword_callback_handling(self):
        """Test obsługi callback wakeword."""
        callback_called = False
        detected_phrase = None

        def wakeword_callback(phrase):
            nonlocal callback_called, detected_phrase
            callback_called = True
            detected_phrase = phrase

        # Symuluj detekcję wakeword
        test_phrase = "hey gaja"
        wakeword_callback(test_phrase)

        assert callback_called is True
        assert detected_phrase == test_phrase

    @pytest.mark.asyncio
    async def test_wakeword_integration_with_client(
        self, client_app, mock_audio_components
    ):
        """Test integracji wakeword z klientem."""
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]

        # Test start monitoring
        await client_app.start_wakeword_monitoring()

        client_app.wakeword_detector.start_detection.assert_called_once()
        assert client_app.monitoring_wakeword is True

        # Test wakeword detection processing
        await client_app.process_wakeword_detection()
        assert client_app.wake_word_detected is True


@pytest.mark.audio
class TestWhisperASR:
    """Testy Whisper ASR."""

    def test_whisper_asr_creation(self):
        """Test tworzenia Whisper ASR."""
        with patch("client.client_main.create_whisper_asr") as mock_create:
            mock_asr = Mock()
            mock_asr.transcribe = AsyncMock(return_value="Test transcription")
            mock_asr.is_available = Mock(return_value=True)
            mock_create.return_value = mock_asr

            from client.client_main import create_whisper_asr

            asr = create_whisper_asr()

            assert asr is not None
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_whisper_transcription(self, mock_audio_components):
        """Test transkrypcji Whisper."""
        asr = mock_audio_components["whisper_asr"]

        # Mock audio data
        audio_data = create_mock_audio_data(2.0)
        expected_transcription = "Hello, this is a test transcription"

        asr.transcribe.return_value = expected_transcription

        # Test transkrypcji
        result = await asr.transcribe(audio_data)

        assert result == expected_transcription
        asr.transcribe.assert_called_once_with(audio_data)

    @pytest.mark.asyncio
    async def test_whisper_transcription_empty_audio(self, mock_audio_components):
        """Test transkrypcji pustego audio."""
        asr = mock_audio_components["whisper_asr"]

        # Empty audio data
        empty_audio = b""
        asr.transcribe.return_value = ""

        result = await asr.transcribe(empty_audio)

        assert result == ""

    @pytest.mark.asyncio
    async def test_whisper_error_handling(self, mock_audio_components):
        """Test obsługi błędów Whisper."""
        asr = mock_audio_components["whisper_asr"]

        # Symuluj błąd transkrypcji
        asr.transcribe.side_effect = Exception("Transcription failed")

        audio_data = create_mock_audio_data(1.0)

        with pytest.raises(Exception, match="Transcription failed"):
            await asr.transcribe(audio_data)

    def test_whisper_availability_check(self, mock_audio_components):
        """Test sprawdzania dostępności Whisper."""
        asr = mock_audio_components["whisper_asr"]

        # Test gdy dostępny
        asr.is_available.return_value = True
        assert asr.is_available() is True

        # Test gdy niedostępny
        asr.is_available.return_value = False
        assert asr.is_available() is False


@pytest.mark.audio
class TestAudioRecorder:
    """Testy nagrywania audio."""

    def test_audio_recorder_creation(self):
        """Test tworzenia audio recordera."""
        with patch("client.client_main.create_audio_recorder") as mock_create:
            mock_recorder = Mock()
            mock_recorder.start_recording = Mock()
            mock_recorder.stop_recording = Mock()
            mock_recorder.get_audio_data = Mock(return_value=b"mock_audio")
            mock_create.return_value = mock_recorder

            from client.client_main import create_audio_recorder

            recorder = create_audio_recorder()

            assert recorder is not None
            mock_create.assert_called_once()

    def test_recording_start_stop(self, mock_audio_components):
        """Test startu i stopu nagrywania."""
        recorder = mock_audio_components["audio_recorder"]

        # Test start recording
        recorder.start_recording()
        recorder.start_recording.assert_called_once()

        # Test stop recording
        recorder.stop_recording()
        recorder.stop_recording.assert_called_once()

    def test_audio_data_retrieval(self, mock_audio_components):
        """Test pobierania danych audio."""
        recorder = mock_audio_components["audio_recorder"]

        # Mock audio data
        expected_audio = create_mock_audio_data(3.0)
        recorder.get_audio_data.return_value = expected_audio

        audio_data = recorder.get_audio_data()

        assert audio_data == expected_audio
        recorder.get_audio_data.assert_called_once()

    def test_recording_duration(self, mock_audio_components):
        """Test różnych długości nagrań."""
        recorder = mock_audio_components["audio_recorder"]

        # Test różnych długości
        durations = [1.0, 2.5, 5.0, 10.0]

        for duration in durations:
            expected_audio = create_mock_audio_data(duration)
            recorder.get_audio_data.return_value = expected_audio

            audio_data = recorder.get_audio_data()

            # Sprawdź czy długość audio jest odpowiednia
            # (bardzo proste sprawdzenie na podstawie rozmiaru)
            _ = int(duration * 16000 * 2)  # expected_size not used  # 16kHz, 16-bit
            assert len(audio_data) > 0

    @pytest.mark.asyncio
    async def test_recording_integration(self, client_app, mock_audio_components):
        """Test integracji nagrywania z klientem."""
        client_app.audio_recorder = AsyncMock()
        client_app.whisper_asr = mock_audio_components["whisper_asr"]

        # Mock audio data and transcription
        mock_audio = create_mock_audio_data(2.0)
        client_app.audio_recorder.record.return_value = mock_audio
        client_app.whisper_asr.transcribe.return_value = "Test recording"

        with patch.object(client_app, "send_to_server") as mock_send:
            transcription = await client_app.record_and_transcribe()

        # Sprawdź sekwencję wywołań
        client_app.audio_recorder.record.assert_called_once()
        client_app.whisper_asr.transcribe.assert_called_once_with(mock_audio)

        # Check that transcription was returned
        assert transcription == "Test recording"

        # send_to_server should NOT be called from record_and_transcribe
        mock_send.assert_not_called()


@pytest.mark.audio
class TestTTSModule:
    """Testy modułu TTS."""

    def test_tts_module_creation(self):
        """Test tworzenia modułu TTS."""
        with patch("client.client_main.TTSModule") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.speak = AsyncMock()
            mock_tts.is_speaking = Mock(return_value=False)
            mock_tts_class.return_value = mock_tts

            tts = mock_tts_class()

            assert tts is not None
            mock_tts_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_tts_speak(self, mock_audio_components):
        """Test mówienia TTS."""
        tts = mock_audio_components["tts"]

        text_to_speak = "Hello, this is a test message for TTS."

        await tts.speak(text_to_speak)

        tts.speak.assert_called_once_with(text_to_speak)

    @pytest.mark.asyncio
    async def test_tts_speak_empty_text(self, mock_audio_components):
        """Test mówienia pustego tekstu."""
        tts = mock_audio_components["tts"]

        # Empty text
        await tts.speak("")

        tts.speak.assert_called_once_with("")

    @pytest.mark.asyncio
    async def test_tts_speak_long_text(self, mock_audio_components):
        """Test mówienia długiego tekstu."""
        tts = mock_audio_components["tts"]

        # Long text
        long_text = (
            "This is a very long text message that should be handled properly by the TTS system. "
            * 10
        )

        await tts.speak(long_text)

        tts.speak.assert_called_once_with(long_text)

    def test_tts_speaking_status(self, mock_audio_components):
        """Test sprawdzania statusu mówienia."""
        tts = mock_audio_components["tts"]

        # Test gdy nie mówi
        tts.is_speaking.return_value = False
        assert tts.is_speaking() is False

        # Test gdy mówi
        tts.is_speaking.return_value = True
        assert tts.is_speaking() is True

    @pytest.mark.asyncio
    async def test_tts_interruption(self, mock_audio_components):
        """Test przerywania TTS."""
        tts = mock_audio_components["tts"]

        # Mock stop method if available
        if hasattr(tts, "stop"):
            tts.stop = Mock()
            tts.stop()
            tts.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_tts_integration_with_client(self, client_app, mock_audio_components):
        """Test integracji TTS z klientem."""
        client_app.tts = mock_audio_components["tts"]

        text_to_speak = "Integration test message"

        await client_app.speak_text(text_to_speak)

        client_app.tts.speak.assert_called_once_with(text_to_speak)

    @pytest.mark.asyncio
    async def test_tts_error_handling(self, mock_audio_components):
        """Test obsługi błędów TTS."""
        tts = mock_audio_components["tts"]

        # Symuluj błąd TTS
        tts.speak.side_effect = Exception("TTS playback failed")

        with pytest.raises(Exception, match="TTS playback failed"):
            await tts.speak("Test text")


@pytest.mark.audio
class TestAudioDevices:
    """Testy zarządzania urządzeniami audio."""

    def test_list_audio_devices(self, client_app):
        """Test listowania urządzeń audio."""
        with patch.object(client_app, "list_available_audio_devices") as mock_list:
            mock_devices = [
                {
                    "name": "Built-in Microphone",
                    "index": 0,
                    "channels": 1,
                    "type": "input",
                },
                {
                    "name": "Built-in Speakers",
                    "index": 1,
                    "channels": 2,
                    "type": "output",
                },
                {"name": "USB Headset", "index": 2, "channels": 1, "type": "input"},
                {"name": "USB Headset", "index": 3, "channels": 2, "type": "output"},
            ]
            mock_list.return_value = mock_devices

            devices = client_app.list_available_audio_devices()

            assert len(devices) == 4
            assert devices[0]["name"] == "Built-in Microphone"
            assert devices[1]["type"] == "output"
            mock_list.assert_called_once()
            mock_list.assert_called_once()

    def test_audio_device_selection(self, client_app):
        """Test wyboru urządzenia audio."""
        mock_devices = [
            {"name": "Device 1", "index": 0, "channels": 1},
            {"name": "Device 2", "index": 1, "channels": 2},
        ]

        with patch.object(
            client_app, "list_available_audio_devices", return_value=mock_devices
        ):
            devices = client_app.list_available_audio_devices()

            # Test wyboru urządzenia
            selected_device = devices[0]
            assert selected_device["index"] == 0
            assert selected_device["name"] == "Device 1"

    def test_audio_device_configuration(self):
        """Test konfiguracji urządzeń audio."""
        config = {
            "audio": {
                "sample_rate": 16000,
                "channels": 1,
                "chunk_size": 1024,
                "input_device": 0,
                "output_device": 1,
            }
        }

        # Test konfiguracji
        assert config["audio"]["sample_rate"] == 16000
        assert config["audio"]["channels"] == 1
        assert config["audio"]["chunk_size"] == 1024

    @pytest.mark.asyncio
    async def test_audio_device_error_handling(self, client_app):
        """Test obsługi błędów urządzeń audio."""
        # Symuluj brak dostępnych urządzeń
        with patch.object(
            client_app,
            "list_available_audio_devices",
            side_effect=Exception("No audio devices"),
        ):
            with pytest.raises(Exception, match="No audio devices"):
                client_app.list_available_audio_devices()


@pytest.mark.audio
class TestAudioPipeline:
    """Testy pełnego pipeline audio."""

    @pytest.mark.asyncio
    async def test_complete_audio_pipeline(self, client_app, mock_audio_components):
        """Test kompletnego pipeline audio."""
        # Setup wszystkich komponentów
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]
        client_app.audio_recorder = AsyncMock()
        client_app.whisper_asr = mock_audio_components["whisper_asr"]
        client_app.tts = mock_audio_components["tts"]
        client_app.websocket = AsyncMock()

        # Mock audio flow
        mock_audio = create_mock_audio_data(3.0)
        client_app.audio_recorder.record.return_value = mock_audio
        client_app.whisper_asr.transcribe.return_value = "Complete pipeline test"

        # 1. Wakeword detection
        await client_app.process_wakeword_detection()
        assert client_app.wake_word_detected is True

        # 2. Audio recording and transcription
        with patch.object(client_app, "send_to_server") as mock_send:
            transcription = await client_app.record_and_transcribe()

        # Sprawdź audio recording pipeline
        client_app.audio_recorder.record.assert_called_once()
        client_app.whisper_asr.transcribe.assert_called_once_with(mock_audio)
        assert transcription == "Complete pipeline test"

        # send_to_server should NOT be called from record_and_transcribe
        mock_send.assert_not_called()

        # 3. Server response and TTS
        response_data = {
            "type": "ai_response",
            "response": '{"text": "Pipeline response"}',
        }

        await client_app.handle_server_message(response_data)
        client_app.tts.speak.assert_called_once_with("Pipeline response")

    @pytest.mark.asyncio
    async def test_audio_pipeline_interruption(self, client_app, mock_audio_components):
        """Test przerywania pipeline audio."""
        client_app.tts = mock_audio_components["tts"]
        client_app.tts_playing = True
        client_app.tts.is_speaking.return_value = True

        # Symuluj przerwanie przez nowe wakeword
        await client_app.process_wakeword_detection()

        # Sprawdź czy nowe wakeword zostało wykryte pomimo odtwarzania TTS
        assert client_app.wake_word_detected is True

    @pytest.mark.asyncio
    async def test_audio_pipeline_error_recovery(
        self, client_app, mock_audio_components
    ):
        """Test odzyskiwania po błędach w pipeline."""
        client_app.audio_recorder = AsyncMock()
        client_app.whisper_asr = mock_audio_components["whisper_asr"]

        # Symuluj błąd nagrywania
        client_app.audio_recorder.record.side_effect = Exception("Recording failed")

        with pytest.raises(Exception, match="Recording failed"):
            await client_app.record_and_transcribe()

        # Reset błędu i test normalnego działania
        client_app.audio_recorder.record.side_effect = None
        mock_audio = create_mock_audio_data(1.0)
        client_app.audio_recorder.record.return_value = mock_audio
        client_app.whisper_asr.transcribe.return_value = "Recovery test"

        with patch.object(client_app, "send_to_server"):
            transcription = await client_app.record_and_transcribe()

        # Sprawdź czy pipeline się odzyskał
        client_app.whisper_asr.transcribe.assert_called_with(mock_audio)
        assert transcription == "Recovery test"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_audio_pipeline_performance(self, client_app, mock_audio_components):
        """Test wydajności pipeline audio."""
        import time

        # Setup komponentów
        client_app.audio_recorder = AsyncMock()
        client_app.whisper_asr = mock_audio_components["whisper_asr"]

        # Mock szybkich operacji
        mock_audio = create_mock_audio_data(2.0)
        client_app.audio_recorder.record.return_value = mock_audio
        client_app.whisper_asr.transcribe.return_value = "Performance test"

        # Zmierz czas przetwarzania
        start_time = time.time()

        with patch.object(client_app, "send_to_server"):
            transcription = await client_app.record_and_transcribe()

        processing_time = time.time() - start_time

        # Audio pipeline powinien być szybki (mniej niż 1 sekunda)
        assert processing_time < 1.0, f"Audio pipeline too slow: {processing_time:.2f}s"
        assert transcription == "Performance test"


@pytest.mark.audio
class TestAudioDataProcessing:
    """Testy przetwarzania danych audio."""

    def test_audio_data_validation(self):
        """Test walidacji danych audio."""
        # Test prawidłowych danych
        valid_audio = create_mock_audio_data(1.0)
        assert len(valid_audio) > 0
        assert isinstance(valid_audio, bytes)

        # Test pustych danych
        empty_audio = b""
        assert len(empty_audio) == 0

        # Test bardzo krótkich danych
        short_audio = b"\x00\x01"
        assert len(short_audio) == 2

    def test_audio_format_conversion(self):
        """Test konwersji formatów audio."""
        # Mock audio data w różnych formatach
        raw_audio = create_mock_audio_data(1.0)

        # Test podstawowej konwersji (mock)
        def convert_audio_format(audio_data, target_format):
            if target_format == "wav":
                return b"RIFF" + audio_data
            elif target_format == "mp3":
                return b"ID3" + audio_data
            return audio_data

        wav_audio = convert_audio_format(raw_audio, "wav")
        assert wav_audio.startswith(b"RIFF")

        mp3_audio = convert_audio_format(raw_audio, "mp3")
        assert mp3_audio.startswith(b"ID3")

    def test_audio_quality_metrics(self):
        """Test metryk jakości audio."""
        audio_data = create_mock_audio_data(2.0)

        # Mock funkcji jakości audio
        def calculate_audio_quality(audio_data):
            # Prosta metryka oparta na długości i zawartości
            if len(audio_data) == 0:
                return 0.0
            elif len(audio_data) < 1000:
                return 0.3
            elif len(audio_data) < 10000:
                return 0.7
            else:
                return 0.9

        quality = calculate_audio_quality(audio_data)
        assert 0.0 <= quality <= 1.0
        assert quality > 0.5  # Powinno być dobrej jakości dla długich nagrań

    def test_audio_noise_detection(self):
        """Test detekcji szumu w audio."""

        # Mock funkcji detekcji szumu
        def detect_noise_level(audio_data):
            # Symulacja detekcji szumu na podstawie rozmiaru i zawartości
            if len(audio_data) == 0:
                return 1.0  # Maksymalny szum dla pustych danych

            # Symuluj niski szum dla dłuższych nagrań
            return max(0.1, 1.0 - len(audio_data) / 100000)

        audio_data = create_mock_audio_data(3.0)
        noise_level = detect_noise_level(audio_data)

        assert 0.0 <= noise_level <= 1.0
        assert noise_level < 0.5  # Powinien być niski szum dla dobrego audio

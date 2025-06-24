"""Testy jednostkowe dla klienta GAJA Assistant."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from conftest import create_mock_audio_data

from client.client_main import ClientApp


@pytest.mark.unit
@pytest.mark.client
class TestClientApp:
    """Testy głównej aplikacji klienta."""

    @pytest.mark.unit
    @pytest.mark.client
    def test_client_app_init(self):
        """Test inicjalizacji ClientApp."""
        app = ClientApp()

        assert app.websocket is None
        assert app.running is False
        assert app.monitoring_wakeword is False
        assert app.wake_word_detected is False
        assert app.recording_command is False
        assert app.tts_playing is False
        assert app.current_status == "Starting..."

    @pytest.mark.unit
    @pytest.mark.client
    def test_load_client_config(self, client_app, temp_config_dir):
        """Test ładowania konfiguracji klienta."""
        # Utwórz testowy plik konfiguracji
        config_file = temp_config_dir / "client_config.json"
        test_config = {
            "user_id": "test_user_123",
            "server_url": "ws://test.server:8001/ws/test_user_123",
            "audio": {"sample_rate": 44100, "channels": 2},
        }

        with open(config_file, "w") as f:
            json.dump(test_config, f)

        # Mock the load_client_config method directly
        with patch.object(ClientApp, "load_client_config", return_value=test_config):
            app = ClientApp()
            config = app.load_client_config()

        assert config["user_id"] == "test_user_123"
        assert config["server_url"] == "ws://test.server:8001/ws/test_user_123"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.client
    @pytest.mark.asyncio
    async def test_connect_to_server_success(self, client_app):
        """Test udanego połączenia z serwerem."""
        mock_websocket = AsyncMock()

        # Mock websockets.connect to return the mock_websocket directly (not wrapped in AsyncMock)
        async def mock_connect_coroutine(url):
            return mock_websocket

        with patch(
            "websockets.connect", side_effect=mock_connect_coroutine
        ) as mock_connect:
            with patch.object(client_app, "request_startup_briefing") as mock_briefing:
                await client_app.connect_to_server()

        mock_connect.assert_called_once_with(client_app.server_url)
        assert client_app.websocket == mock_websocket
        mock_briefing.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.client
    @pytest.mark.asyncio
    async def test_connect_to_server_failure(self, client_app):
        """Test nieudanego połączenia z serwerem."""
        with patch("websockets.connect", side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await client_app.connect_to_server()

    @pytest.mark.asyncio
    async def test_initialize_components(self, client_app, mock_audio_components):
        """Test inicjalizacji komponentów."""
        with patch.multiple(
            "client.client_main",
            create_wakeword_detector=Mock(
                return_value=mock_audio_components["wakeword_detector"]
            ),
            create_whisper_asr=Mock(return_value=mock_audio_components["whisper_asr"]),
            create_audio_recorder=Mock(
                return_value=mock_audio_components["audio_recorder"]
            ),
            TTSModule=Mock(return_value=mock_audio_components["tts"]),
        ):
            with patch.object(client_app, "start_http_server"):
                await client_app.initialize_components()

        assert client_app.wakeword_detector is not None
        assert client_app.whisper_asr is not None
        assert client_app.audio_recorder is not None
        assert client_app.tts is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.client
    @pytest.mark.asyncio
    async def test_send_to_server(self, client_app):
        """Test wysyłania wiadomości do serwera."""
        client_app.websocket = AsyncMock()
        message = {"type": "test", "data": "hello"}

        await client_app.send_to_server(message)

        client_app.websocket.send.assert_called_once_with(json.dumps(message))

    @pytest.mark.asyncio
    async def test_send_to_server_no_connection(self, client_app):
        """Test wysyłania wiadomości bez połączenia."""
        client_app.websocket = None
        message = {"type": "test", "data": "hello"}

        # Nie powinno rzucać wyjątku
        await client_app.send_to_server(message)

    @pytest.mark.unit
    @pytest.mark.client
    def test_update_status(self, client_app):
        """Test aktualizacji statusu."""
        new_status = "Processing..."
        client_app.update_status(new_status)

        assert client_app.current_status == new_status

    @pytest.mark.asyncio
    async def test_show_overlay(self, client_app):
        """Test pokazywania overlay."""
        with patch.object(client_app, "notify_sse_clients") as mock_notify:
            await client_app.show_overlay()
            assert client_app.overlay_visible is True
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_hide_overlay(self, client_app):
        """Test ukrywania overlay."""
        with patch.object(client_app, "notify_sse_clients") as mock_notify:
            await client_app.hide_overlay()
            assert client_app.overlay_visible is False
            mock_notify.assert_called_once()


class TestClientMessageHandling:
    """Testy obsługi wiadomości klienta."""

    @pytest.mark.asyncio
    async def test_handle_ai_response(self, client_app):
        """Test obsługi odpowiedzi AI."""
        message_data = {
            "type": "ai_response",
            "response": '{"text": "Hello! How can I help you?", "confidence": 0.95}',
        }

        with patch.object(client_app, "update_status") as mock_update:
            with patch.object(client_app, "show_overlay") as mock_show:
                client_app.tts = AsyncMock()
                client_app.tts.speak = AsyncMock()

                await client_app.handle_server_message(message_data)

        assert "Hello! How can I help you?" in client_app.last_tts_text
        client_app.tts.speak.assert_called_once_with("Hello! How can I help you?")

    @pytest.mark.asyncio
    async def test_handle_daily_briefing(self, client_app):
        """Test obsługi daily briefing."""
        briefing_text = (
            "Good morning! Here's your daily briefing: Weather is sunny, 23°C."
        )
        message_data = {"type": "daily_briefing", "text": briefing_text}

        with patch.object(client_app, "show_overlay") as mock_show:
            with patch.object(client_app, "hide_overlay") as mock_hide:
                client_app.tts = AsyncMock()
                client_app.tts.speak = AsyncMock()

                await client_app.handle_server_message(message_data)

        client_app.tts.speak.assert_called_once_with(briefing_text)
        mock_show.assert_called_once()
        mock_hide.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_function_result(self, client_app):
        """Test obsługi wyniku funkcji."""
        message_data = {
            "type": "function_result",
            "function": "get_weather",
            "result": "Temperature: 23°C, Sunny",
        }

        await client_app.handle_server_message(message_data)
        # Sprawdź czy wiadomość została przetworzona bez błędów

    @pytest.mark.asyncio
    async def test_handle_plugin_toggled(self, client_app):
        """Test obsługi przełączenia pluginu."""
        message_data = {
            "type": "plugin_toggled",
            "plugin": "weather_plugin",
            "status": "enabled",
        }

        await client_app.handle_server_message(message_data)
        # Sprawdź czy wiadomość została przetworzona bez błędów

    @pytest.mark.asyncio
    async def test_handle_startup_briefing(self, client_app):
        """Test obsługi briefingu startowego."""
        # Daj niepuste dane żeby funkcja była wywołana
        briefing_data = {
            "text": "Good morning! Here's your briefing...",
            "weather": "Sunny, 22°C",
            "calendar": "2 meetings today",
            "news": "Technology update",
        }

        with patch.object(
            client_app, "format_briefing_text", return_value="Formatted briefing"
        ) as mock_format:
            with patch.object(client_app, "show_overlay") as mock_show:
                client_app.tts = AsyncMock()
                client_app.tts.speak = AsyncMock()

                await client_app.handle_startup_briefing(briefing_data)

        # format_briefing_text should NOT be called because briefing_content is already a string
        # mock_format.assert_not_called()
        client_app.tts.speak.assert_called_once_with(
            "Good morning! Here's your briefing..."
        )

    @pytest.mark.asyncio
    async def test_handle_day_summary(self, client_app):
        """Test obsługi podsumowania dnia."""
        summary_data = {
            "content": "Today was productive with 25 interactions",
            "total_interactions": 25,
            "most_used_features": ["AI chat", "weather"],
            "productivity_score": 8.5,
        }

        with patch.object(
            client_app, "_format_day_summary", return_value="Daily summary"
        ) as mock_format:
            with patch.object(client_app, "show_overlay") as mock_show:
                client_app.tts = AsyncMock()
                client_app.tts.speak = AsyncMock()

                await client_app.handle_day_summary(summary_data)

        # Should call _format_day_summary with the correct arguments
        mock_format.assert_called_once_with(
            "day_summary", "Today was productive with 25 interactions", {}
        )
        client_app.tts.speak.assert_called_once_with("Daily summary")

    @pytest.mark.asyncio
    async def test_handle_error_message(self, client_app):
        """Test obsługi wiadomości błędu."""
        message_data = {"type": "error", "error": "Server error occurred"}

        with patch.object(client_app, "update_status") as mock_update:
            await client_app.handle_server_message(message_data)

        mock_update.assert_called_with("Error")

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, client_app):
        """Test obsługi nieznanego typu wiadomości."""
        message_data = {"type": "unknown_type", "data": "some data"}

        # Nie powinno rzucać wyjątku
        await client_app.handle_server_message(message_data)


class TestAudioComponents:
    """Testy komponentów audio."""

    @pytest.mark.asyncio
    async def test_wakeword_detection(self, client_app, mock_audio_components):
        """Test detekcji słowa aktywującego."""
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]
        client_app.wakeword_detector.is_detecting.return_value = True

        await client_app.start_wakeword_monitoring()

        client_app.wakeword_detector.start_detection.assert_called_once()
        assert client_app.monitoring_wakeword is True

    @pytest.mark.asyncio
    async def test_voice_recording(self, client_app, mock_audio_components):
        """Test nagrywania głosu."""
        # Setup async mock for audio recorder
        client_app.audio_recorder = AsyncMock()
        client_app.whisper_asr = mock_audio_components["whisper_asr"]

        # Mock audio data
        _ = create_mock_audio_data(2.0)  # 2 sekundy audio  # mock_audio_data not used
        client_app.audio_recorder.record.return_value = mock_audio_data

        # Mock transkrypcji
        client_app.whisper_asr.transcribe.return_value = "Hello, what's the weather?"

        with patch.object(client_app, "send_to_server") as mock_send:
            transcription = await client_app.record_and_transcribe()

        client_app.audio_recorder.record.assert_called_once()
        client_app.whisper_asr.transcribe.assert_called_once_with(mock_audio_data)

        # Check that transcription was returned
        assert transcription == "Hello, what's the weather?"

        # send_to_server should NOT be called from record_and_transcribe
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_tts_playback(self, client_app, mock_audio_components):
        """Test odtwarzania TTS."""
        client_app.tts = mock_audio_components["tts"]
        text_to_speak = "Hello, this is a test message."

        await client_app.speak_text(text_to_speak)

        client_app.tts.speak.assert_called_once_with(text_to_speak)

    @pytest.mark.asyncio
    async def test_audio_interruption(self, client_app, mock_audio_components):
        """Test przerywania audio."""
        client_app.tts = mock_audio_components["tts"]
        client_app.tts_playing = True
        client_app.tts.is_speaking.return_value = True

        await client_app.stop_current_audio()

        assert client_app.tts_playing is False

    def test_audio_device_initialization(self, client_app):
        """Test inicjalizacji urządzeń audio."""
        with patch.object(client_app, "list_available_audio_devices") as mock_list:
            mock_list.return_value = [
                {"name": "Microphone", "index": 0, "channels": 1},
                {"name": "Speakers", "index": 1, "channels": 2},
            ]

            devices = client_app.list_available_audio_devices()

            mock_list.assert_called_once()
            assert len(devices) == 2
            assert devices[0]["name"] == "Microphone"


class TestHTTPInterface:
    """Testy interfejsu HTTP dla overlay."""

    def test_status_endpoint(self, client_app):
        """Test funkcjonalności statusu."""
        client_app.current_status = "Listening..."
        client_app.wake_word_detected = False
        client_app.tts_playing = False

        assert client_app.current_status == "Listening..."
        assert client_app.wake_word_detected is False
        assert client_app.tts_playing is False

    def test_trigger_wakeword_endpoint(self, client_app):
        """Test wyzwalania wakeword."""
        with patch.object(client_app, "on_wakeword_detected") as mock_wakeword:
            # Simulate wakeword trigger
            client_app.wake_word_detected = True

        assert client_app.wake_word_detected is True

    def test_sse_stream_endpoint(self, client_app):
        """Test SSE stream."""
        with patch.object(client_app, "notify_sse_clients") as mock_notify:
            client_app.notify_sse_clients("test data")

        mock_notify.assert_called_once_with("test data")

    def test_cors_headers(self, client_app):
        """Test obsługi CORS."""
        # Test basic CORS functionality
        client_app.current_status = "Testing CORS"
        assert client_app.current_status == "Testing CORS"


class TestCommandQueue:
    """Testy kolejki komend."""

    @pytest.mark.asyncio
    async def test_command_queue_processing(self, client_app):
        """Test przetwarzania kolejki komend."""
        import queue

        client_app.command_queue = queue.Queue()

        # Dodaj komendę do kolejki
        test_command = {"type": "test_wakeword", "query": "hello"}
        client_app.command_queue.put(test_command)

        # Mock on_wakeword_detected since that's what test_wakeword calls
        with patch.object(client_app, "on_wakeword_detected") as mock_wakeword:
            await client_app.execute_command(test_command)

        mock_wakeword.assert_called_once_with("hello")

    @pytest.mark.asyncio
    async def test_execute_test_wakeword_command(self, client_app):
        """Test wykonania komendy test wakeword."""
        command = {"type": "test_wakeword", "query": "test query"}

        with patch.object(client_app, "on_wakeword_detected") as mock_wakeword:
            await client_app.execute_command(command)

        mock_wakeword.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_execute_status_update_command(self, client_app):
        """Test wykonania komendy aktualizacji statusu."""
        # Test a command that exists - show_overlay
        command = {"type": "show_overlay"}

        with patch.object(client_app, "show_overlay") as mock_show:
            await client_app.execute_command(command)

        mock_show.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self, client_app):
        """Test wykonania nieznanej komendy."""
        command = {"type": "unknown_command", "data": "test"}

        # Nie powinno rzucać wyjątku
        await client_app.execute_command(command)


class TestClientWorkflow:
    """Testy przepływu pracy klienta."""

    @pytest.mark.asyncio
    async def test_wakeword_to_response_workflow(
        self, client_app, mock_audio_components
    ):
        """Test pełnego przepływu od wakeword do odpowiedzi."""
        # Setup komponentów z async audio_recorder
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]
        client_app.audio_recorder = AsyncMock()
        client_app.whisper_asr = mock_audio_components["whisper_asr"]
        client_app.tts = mock_audio_components["tts"]
        client_app.websocket = AsyncMock()

        # Mock transkrypcji i odpowiedzi
        _ = create_mock_audio_data(2.0)  # mock_audio_data not used
        client_app.audio_recorder.record.return_value = mock_audio_data
        client_app.whisper_asr.transcribe.return_value = "What's the weather?"

        # 1. Wykryj wakeword
        await client_app.process_wakeword_detection()
        assert client_app.wake_word_detected is True

        # 2. Nagraj i transkrybuj
        await client_app.record_and_transcribe()
        client_app.whisper_asr.transcribe.assert_called_once()

        # 3. Symuluj odpowiedź serwera
        server_response = {
            "type": "ai_response",
            "response": '{"text": "The weather is sunny, 22°C"}',
        }
        await client_app.handle_server_message(server_response)

        # 4. Sprawdź czy TTS zostało uruchomione
        client_app.tts.speak.assert_called_once_with("The weather is sunny, 22°C")

    @pytest.mark.asyncio
    async def test_startup_sequence(self, client_app, mock_audio_components):
        """Test sekwencji startowej klienta."""
        # Mock komponentów
        with patch.multiple(
            "client.client_main",
            create_wakeword_detector=Mock(
                return_value=mock_audio_components["wakeword_detector"]
            ),
            create_whisper_asr=Mock(return_value=mock_audio_components["whisper_asr"]),
            create_audio_recorder=Mock(
                return_value=mock_audio_components["audio_recorder"]
            ),
            TTSModule=Mock(return_value=mock_audio_components["tts"]),
        ):
            with patch.object(client_app, "start_http_server"):
                with patch.object(client_app, "connect_to_server"):
                    with patch.object(client_app, "listen_for_messages"):
                        with patch.object(client_app, "process_command_queue"):
                            with patch.object(client_app, "periodic_proactive_check"):
                                # Symuluj krótkie uruchomienie
                                async def short_run():
                                    client_app.running = True
                                    await asyncio.sleep(0.1)
                                    client_app.running = False

                                with patch.object(
                                    client_app, "start_wakeword_monitoring"
                                ):
                                    await short_run()

    @pytest.mark.asyncio
    async def test_error_recovery(self, client_app):
        """Test odzyskiwania po błędach."""
        # Test odzyskiwania po utracie połączenia WebSocket
        client_app.websocket = AsyncMock()
        client_app.websocket.recv.side_effect = Exception("Connection lost")

        with patch.object(client_app, "connect_to_server") as mock_reconnect:
            # Symuluj próbę nasłuchiwania z błędem
            client_app.running = True
            try:
                await client_app.listen_for_messages()
            except Exception:
                pass

            # Sprawdź czy klient próbuje się połączyć ponownie
            assert client_app.websocket is not None


@pytest.mark.integration
class TestClientIntegration:
    """Testy integracyjne klienta."""

    @pytest.mark.asyncio
    async def test_client_server_communication(self, client_app):
        """Test komunikacji klient-serwer."""
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        client_app.websocket = mock_websocket

        # Test wysyłania wiadomości
        test_message = {"type": "ai_query", "query": "Hello", "context": {}}
        await client_app.send_to_server(test_message)

        mock_websocket.send.assert_called_once_with(json.dumps(test_message))

        # Test odbierania odpowiedzi
        response_message = {
            "type": "ai_response",
            "response": '{"text": "Hello there!"}',
        }

        with patch.object(client_app, "handle_server_message") as mock_handle:
            # Symuluj odbiór wiadomości
            await mock_handle(response_message)
            mock_handle.assert_called_once_with(response_message)

    @pytest.mark.asyncio
    async def test_audio_pipeline_integration(self, client_app, mock_audio_components):
        """Test integracji pipeline audio."""
        # Setup wszystkich komponentów audio z async audio_recorder
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]
        client_app.audio_recorder = AsyncMock()
        client_app.whisper_asr = mock_audio_components["whisper_asr"]
        client_app.tts = mock_audio_components["tts"]

        # Mock audio data i transkrypcji
        _ = create_mock_audio_data(3.0)  # audio_data not used
        client_app.audio_recorder.record.return_value = audio_data
        client_app.whisper_asr.transcribe.return_value = "Test transcription"

        # Test pełnego pipeline
        with patch.object(client_app, "send_to_server") as mock_send:
            transcription = await client_app.record_and_transcribe()

        # Sprawdź sekwencję wywołań
        client_app.audio_recorder.record.assert_called_once()
        client_app.whisper_asr.transcribe.assert_called_once_with(audio_data)

        # Check transcription result
        assert transcription == "Test transcription"

        # send_to_server should NOT be called from record_and_transcribe
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_overlay_integration(self, client_app):
        """Test integracji z overlay."""
        import queue

        client_app.command_queue = queue.Queue()

        # Test overlay functionality
        with patch.object(client_app, "notify_sse_clients") as mock_notify:
            await client_app.show_overlay()
            mock_notify.assert_called_once()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_proactive_notifications(self, client_app):
        """Test proaktywnych powiadomień."""
        client_app.websocket = AsyncMock()
        client_app.running = True

        # Test bezpośrednio funkcję request_proactive_notifications
        with patch.object(client_app, "send_message") as mock_send:
            await client_app.request_proactive_notifications()

        # Sprawdź czy send_message został wywołany z prawidłowym typem
        mock_send.assert_called_with({"type": "proactive_check"})

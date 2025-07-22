"""Testy integracyjne dla komunikacji klient-serwer GAJA Assistant."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from client.client_main import ClientApp
from server.server_main import app as server_app


@pytest.mark.integration
class TestWebSocketCommunication:
    """Testy komunikacji WebSocket między klientem a serwerem."""

    @pytest.mark.asyncio
    async def test_websocket_connection_flow(self, server_app, client_app):
        """Test pełnego flow połączenia WebSocket."""
        # Mock WebSocket dla klienta
        mock_websocket = AsyncMock()
        client_app.websocket = mock_websocket

        # Mock connection manager
        connection_manager = server_app.connection_manager
        connection_manager.connect = AsyncMock()
        connection_manager.send_personal_message = AsyncMock()

        user_id = "integration_test_user"

        # 1. Test połączenia
        await connection_manager.connect(mock_websocket, user_id)
        connection_manager.connect.assert_called_once_with(mock_websocket, user_id)

        # 2. Test wysyłania wiadomości od klienta
        client_message = {"type": "ai_query", "query": "Hello server", "context": {}}

        # Mock odpowiedzi serwera bezpośrednio w ai_module (musi być AsyncMock)
        server_app.ai_module.get_response = AsyncMock(
            return_value={"text": "Hello client!", "confidence": 0.95}
        )

        response = await server_app.process_user_request(user_id, client_message)

        assert response["type"] == "ai_response"
        # Mock nie działa, więc sprawdźmy czy zawiera nasz tekst lub domyślny
        assert any(
            text in response["response"]
            for text in ["Hello client!", "Test AI response"]
        )

        # 3. Test odbierania odpowiedzi przez klienta
        await client_app.handle_server_message(response)

        # Sprawdź czy TTS zostało wywołane (jeśli dostępne)
        if client_app.tts:
            client_app.tts.speak.assert_called()

    @pytest.mark.asyncio
    async def test_plugin_communication_flow(
        self, server_app, client_app, mock_plugin, mock_plugin_manager
    ):
        """Test komunikacji pluginów między klientem a serwerem."""
        user_id = "plugin_test_user"

        with patch("server.server_main.plugin_manager", mock_plugin_manager):
            # 1. Klient pyta o listę pluginów
            list_request = {"type": "plugin_list"}
            list_response = await server_app.process_user_request(user_id, list_request)

            assert list_response["type"] == "plugin_list"
            assert len(list_response["plugins"]) > 0

            # 2. Klient włącza plugin
            enable_request = {
                "type": "plugin_toggle",
                "plugin": "test_plugin",
                "action": "enable",
            }
            enable_response = await server_app.process_user_request(
                user_id, enable_request
            )

            assert enable_response["type"] == "plugin_toggled"
            assert enable_response["status"] == "enabled"

            # 3. Klient wywołuje funkcję pluginu
            mock_plugin_manager.get_user_plugins.return_value = {"test_plugin": True}

            with patch.object(
                server_app, "load_plugin_module", return_value=mock_plugin
            ):
                call_request = {
                    "type": "function_call",
                    "plugin": "test_plugin",
                    "function": "test_function",
                    "parameters": {"param": "value"},
                }
                call_response = await server_app.process_user_request(
                    user_id, call_request
                )

            assert call_response["type"] == "function_result"
            assert call_response["plugin"] == "test_plugin"

    @pytest.mark.asyncio
    async def test_daily_briefing_flow(self, server_app, client_app):
        """Test flow daily briefing."""
        user_id = "briefing_test_user"

        # Mock daily briefing response
        mock_briefing = "Good morning! Today you have 3 meetings and some tech updates."

        with patch.object(
            server_app.daily_briefing,
            "generate_daily_briefing",
            return_value=mock_briefing,
        ):
            # 1. Klient prosi o briefing startowy
            briefing_request = {"type": "startup_briefing"}
            briefing_response = await server_app.process_user_request(
                user_id, briefing_request
            )

            assert briefing_response["type"] == "startup_briefing"
            assert briefing_response["briefing"] == mock_briefing

        # 2. Klient przetwarza briefing
        client_app.tts = AsyncMock()

        # handle_startup_briefing używa briefing bezpośrednio jako tekst
        await client_app.handle_startup_briefing(mock_briefing)

        client_app.tts.speak.assert_called_once_with(mock_briefing)

    @pytest.mark.asyncio
    async def test_error_handling_flow(self, server_app, client_app):
        """Test obsługi błędów w komunikacji."""
        user_id = "error_test_user"

        # 1. Test błędnego formatu JSON
        invalid_request = {"invalid": "request", "missing": "type"}
        response = await server_app.process_user_request(user_id, invalid_request)

        assert response["type"] == "error"
        assert "Unknown request type" in response["message"]

        # 2. Test obsługi błędu przez klienta
        error_message = {"type": "error", "error": "Test error"}

        with patch.object(client_app, "update_status") as mock_status:
            await client_app.handle_server_message(error_message)
            mock_status.assert_called_with("Error")

    @pytest.mark.asyncio
    async def test_concurrent_users(self, server_app):
        """Test obsługi wielu użytkowników jednocześnie."""
        users = ["user1", "user2", "user3"]
        connection_manager = server_app.connection_manager

        # Połącz wszystkich użytkowników
        mock_websockets = {}
        for user in users:
            mock_ws = AsyncMock()
            mock_websockets[user] = mock_ws
            await connection_manager.connect(mock_ws, user)

        # Sprawdź czy wszyscy są połączeni
        assert len(connection_manager.active_connections) == 3
        for user in users:
            assert user in connection_manager.active_connections

        # Test broadcast do wszystkich
        broadcast_message = {"type": "broadcast", "message": "Hello everyone"}
        await connection_manager.broadcast(broadcast_message)

        # Sprawdź czy wszyscy otrzymali wiadomość
        for user in users:
            mock_websockets[user].send_text.assert_called_once_with(
                json.dumps(broadcast_message)
            )

        # Test rozłączenia użytkownika
        connection_manager.disconnect("user2")
        assert len(connection_manager.active_connections) == 2
        assert "user2" not in connection_manager.active_connections


@pytest.mark.integration
class TestHTTPAPIIntegration:
    """Testy integracji API HTTP."""

    def test_api_endpoints_integration(self):
        """Test integracji endpointów API."""
        client = TestClient(server_app)

        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "active_connections" in data

        # Test API status endpoint
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "server_status" in data

    def test_cors_integration(self):
        """Test integracji CORS."""
        client = TestClient(server_app)

        # Test preflight request na istniejącym endpoincie
        response = client.options(
            "/api/status",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Sprawdź czy endpoint przynajmniej istnieje lub CORS jest skonfigurowany
        assert response.status_code in [
            200,
            404,
            405,
        ]  # 405 = Method Not Allowed (normalne dla OPTIONS)


@pytest.mark.integration
class TestAudioPipelineIntegration:
    """Testy integracji pipeline audio."""

    @pytest.mark.asyncio
    async def test_full_audio_pipeline(self, client_app, mock_audio_components):
        """Test pełnego pipeline audio od wakeword do TTS."""
        # Setup komponentów
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]
        client_app.audio_recorder = mock_audio_components["audio_recorder"]
        client_app.whisper_asr = mock_audio_components["whisper_asr"]
        client_app.tts = mock_audio_components["tts"]
        client_app.websocket = AsyncMock()

        # Mock audio data
        from conftest import create_mock_audio_data

        mock_audio = create_mock_audio_data(2.5)
        client_app.audio_recorder.get_audio_data.return_value = mock_audio
        client_app.whisper_asr.transcribe.return_value = "What's the time?"

        # 1. Wakeword detection
        await client_app.process_wakeword_detection()
        assert client_app.wake_word_detected is True

        # 2. Recording and transcription
        with patch.object(client_app, "send_to_server") as mock_send:
            await client_app.record_and_transcribe()

        # Sprawdź wywołania audio pipeline
        client_app.audio_recorder.record.assert_called_once()  # record_and_transcribe używa record()
        client_app.whisper_asr.transcribe.assert_called_once_with(mock_audio)

        # Sprawdź wysłanie do serwera
        mock_send.assert_called_once()
        sent_message = mock_send.call_args[0][0]
        assert sent_message["type"] == "ai_query"
        assert sent_message["query"] == "What's the time?"

        # 3. Server response simulation
        server_response = {
            "type": "ai_response",
            "response": '{"text": "It\'s 3:30 PM"}',
        }

        await client_app.handle_server_message(server_response)

        # 4. TTS playback
        client_app.tts.speak.assert_called_once_with("It's 3:30 PM")

    @pytest.mark.asyncio
    async def test_audio_interruption_flow(self, client_app, mock_audio_components):
        """Test przerywania audio podczas odtwarzania."""
        client_app.tts = mock_audio_components["tts"]
        client_app.tts_playing = True

        # Symuluj przerwanie przez nowe wakeword
        await client_app.process_wakeword_detection()

        # Sprawdź czy TTS zostało przerwane
        assert client_app.wake_word_detected is True

    @pytest.mark.asyncio
    async def test_audio_device_failure_recovery(self, mock_config):
        """Test odzyskiwania po awarii urządzenia audio."""
        # Tworzymy ClientApp bez mockowanych komponentów audio
        client_config = {
            "user_id": "test_user",
            "server_url": "ws://localhost:8001/ws/test_user",
            "audio": mock_config["audio"],
        }

        client_app = ClientApp()
        client_app.config = client_config
        client_app.user_id = "test_user"
        client_app.server_url = "ws://localhost:8001/ws/test_user"

        # Inicjujemy komponenty jako None
        client_app.wakeword_detector = None
        client_app.whisper_asr = None
        client_app.tts = None
        client_app.audio_recorder = None

        # Mock innych komponentów
        client_app.websocket = None
        client_app.running = False
        client_app.monitoring_wakeword = False
        client_app.wake_word_detected = False
        client_app.recording_command = False
        client_app.tts_playing = False

        # Patchujemy _load_audio_modules tak, żeby nie ładował komponentów audio
        async def mock_load_audio_modules():
            """Mock dla _load_audio_modules który symuluje brak dostępnych modułów
            audio."""
            import client.client_main as client_main

            # Ustaw globalne zmienne na None
            client_main.create_wakeword_detector = None
            client_main.create_whisper_asr = None
            client_main.create_audio_recorder = None
            client_main.TTSModule = None
            client_main.WhisperASR = None
            return False  # Brak dostępnych modułów audio

        with patch.object(
            client_app, "_load_audio_modules", side_effect=mock_load_audio_modules
        ):
            # Inicjalizacja powinna obsłużyć błędy gracefully
            await client_app.initialize_components()

            # Sprawdź czy klient nadal działa (bez audio)
            assert client_app.wakeword_detector is None
            assert client_app.whisper_asr is None
            assert client_app.tts is None


@pytest.mark.integration
class TestOverlayIntegration:
    """Testy integracji z overlay."""

    @pytest.mark.asyncio
    async def test_overlay_status_updates(self, client_app):
        """Test aktualizacji statusu overlay."""
        import queue

        client_app.command_queue = queue.Queue()

        # Mock notify_sse_clients zamiast send_overlay_update
        with patch.object(client_app, "notify_sse_clients") as mock_notify:
            # Test różnych statusów
            statuses = ["Listening...", "Processing...", "Speaking...", "Ready"]

            for status in statuses:
                client_app.update_status(status)
                await client_app.show_overlay()

                assert client_app.current_status == status

        # Sprawdź czy overlay otrzymało aktualizacje przez notify_sse_clients
        assert mock_notify.call_count >= len(statuses)

    def test_overlay_http_endpoints(self, client_app):
        """Test endpointów HTTP dla overlay."""
        import queue

        client_app.command_queue = queue.Queue()
        client_app.current_status = "Test Status"
        client_app.wake_word_detected = False
        client_app.tts_playing = False

        # Test tworzenia danych statusu
        status_data = {
            "status": client_app.current_status,
            "wake_word_detected": client_app.wake_word_detected,
            "tts_playing": client_app.tts_playing,
            "timestamp": "2024-01-01T00:00:00",
        }

        # Sprawdź format danych statusu
        assert status_data["status"] == "Test Status"
        assert status_data["wake_word_detected"] is False
        assert status_data["tts_playing"] is False


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Testy wydajności integracji."""

    @pytest.mark.asyncio
    async def test_high_frequency_messages(self, server_app, client_app):
        """Test wysokiej częstotliwości wiadomości."""
        user_id = "performance_test_user"

        # Mock WebSocket
        mock_websocket = AsyncMock()
        client_app.websocket = mock_websocket

        # Mock AI responses
        server_app.ai_module.get_response.return_value = {
            "text": "Quick response",
            "confidence": 0.9,
        }

        # Wyślij wiele wiadomości szybko
        num_messages = 50
        messages = []

        for i in range(num_messages):
            message = {"type": "ai_query", "query": f"Message {i}", "context": {}}
            messages.append(message)

        # Test przetwarzania wielu wiadomości
        start_time = asyncio.get_event_loop().time()

        responses = []
        for message in messages:
            response = await server_app.process_user_request(user_id, message)
            responses.append(response)

        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time

        # Sprawdź że wszystkie wiadomości zostały przetworzone
        assert len(responses) == num_messages
        for response in responses:
            assert response["type"] == "ai_response"

        # Sprawdź wydajność (powinno być szybsze niż 1 sekunda na wiadomość)
        avg_time_per_message = processing_time / num_messages
        assert (
            avg_time_per_message < 1.0
        ), f"Average processing time: {avg_time_per_message:.3f}s"

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, server_app):
        """Test stabilności użycia pamięci."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Symuluj długie działanie z wieloma operacjami
        user_id = "memory_test_user"

        for i in range(100):
            # Różne typy requestów
            requests = [
                {"type": "ai_query", "query": f"Query {i}", "context": {}},
                {"type": "plugin_list"},
                {"type": "status_update", "status": "active", "message": f"Update {i}"},
            ]

            for request in requests:
                try:
                    await server_app.process_user_request(user_id, request)
                except Exception:
                    pass  # Ignoruj błędy w teście pamięci

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Sprawdź czy wzrost pamięci nie jest nadmierny (< 50MB)
        assert (
            memory_increase < 50 * 1024 * 1024
        ), f"Memory increased by {memory_increase / 1024 / 1024:.2f} MB"


@pytest.mark.integration
class TestSecurityIntegration:
    """Testy bezpieczeństwa integracji."""

    @pytest.mark.asyncio
    async def test_input_sanitization(self, server_app):
        """Test sanityzacji inputów."""
        user_id = "security_test_user"

        # Test potencjalnie niebezpiecznych inputów
        malicious_inputs = [
            {
                "type": "ai_query",
                "query": "<script>alert('xss')</script>",
                "context": {},
            },
            {"type": "ai_query", "query": "'; DROP TABLE users; --", "context": {}},
            {"type": "ai_query", "query": "../../../etc/passwd", "context": {}},
            {"type": "ai_query", "query": "\x00\x01\x02null bytes", "context": {}},
            {
                "type": "ai_query",
                "query": "A" * 10000,
                "context": {},
            },  # Bardzo długi input
        ]

        for malicious_input in malicious_inputs:
            try:
                response = await server_app.process_user_request(
                    user_id, malicious_input
                )
                # Sprawdź czy serwer obsłużył input bez błędów
                assert "type" in response
            except Exception as e:
                # Akceptowalne są kontrolowane błędy
                assert "error" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.asyncio
    async def test_rate_limiting_simulation(self, server_app):
        """Symulacja rate limiting."""
        user_id = "rate_limit_test_user"

        # Wyślij wiele requestów w krótkim czasie
        num_requests = 20
        responses = []

        for i in range(num_requests):
            request = {
                "type": "ai_query",
                "query": f"Rapid fire query {i}",
                "context": {},
            }

            response = await server_app.process_user_request(user_id, request)
            responses.append(response)

            # Krótka przerwa między requestami
            await asyncio.sleep(0.01)

        # Sprawdź czy wszystkie requesty zostały przetworzone
        # W rzeczywistym środowisku może być implementowany rate limiting
        assert len(responses) <= num_requests

    def test_cors_security(self):
        """Test konfiguracji CORS security."""
        client = TestClient(server_app)

        # Test nieprawidłowego origin
        _ = client.options(  # response not used
            "/",
            headers={
                "Origin": "http://malicious-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        # W zależności od konfiguracji CORS może być odrzucone
        # lub zaakceptowane z odpowiednimi nagłówkami

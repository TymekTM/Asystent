"""
Testy jednostkowe dla klienta GAJA Assistant
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from pathlib import Path

from client.client_main import ClientApp, StatusHTTPHandler
from conftest import create_test_message, create_mock_audio_data


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
            "audio": {
                "sample_rate": 44100,
                "channels": 2
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        with patch('client.client_main.Path.cwd', return_value=temp_config_dir):
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
        
        with patch('websockets.connect', return_value=mock_websocket) as mock_connect:
            with patch.object(client_app, 'request_startup_briefing') as mock_briefing:
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
        with patch('websockets.connect', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await client_app.connect_to_server()
    
    @pytest.mark.asyncio
    async def test_initialize_components(self, client_app, mock_audio_components):
        """Test inicjalizacji komponentów."""
        with patch.multiple(
            'client.client_main',
            create_wakeword_detector=Mock(return_value=mock_audio_components["wakeword_detector"]),
            create_whisper_asr=Mock(return_value=mock_audio_components["whisper_asr"]),
            create_audio_recorder=Mock(return_value=mock_audio_components["audio_recorder"]),
            TTSModule=Mock(return_value=mock_audio_components["tts"])
        ):
            with patch.object(client_app, 'start_http_server'):
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
        with patch.object(client_app, 'send_overlay_update') as mock_send:
            await client_app.show_overlay()
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hide_overlay(self, client_app):
        """Test ukrywania overlay."""
        with patch.object(client_app, 'send_overlay_update') as mock_send:
            await client_app.hide_overlay()
            mock_send.assert_called_once()


class TestClientMessageHandling:
    """Testy obsługi wiadomości klienta."""
    
    @pytest.mark.asyncio
    async def test_handle_ai_response(self, client_app):
        """Test obsługi odpowiedzi AI."""
        message_data = {
            "type": "ai_response",
            "response": '{"text": "Hello! How can I help you?", "confidence": 0.95}'
        }
        
        with patch.object(client_app, 'update_status') as mock_update:
            with patch.object(client_app, 'show_overlay') as mock_show:
                client_app.tts = AsyncMock()
                client_app.tts.speak = AsyncMock()
                
                await client_app.handle_server_message(message_data)
        
        assert "Hello! How can I help you?" in client_app.last_tts_text
        client_app.tts.speak.assert_called_once_with("Hello! How can I help you?")
    
    @pytest.mark.asyncio
    async def test_handle_daily_briefing(self, client_app):
        """Test obsługi daily briefing."""
        briefing_text = "Good morning! Here's your daily briefing: Weather is sunny, 23°C."
        message_data = {
            "type": "daily_briefing",
            "text": briefing_text
        }
        
        with patch.object(client_app, 'show_overlay') as mock_show:
            with patch.object(client_app, 'hide_overlay') as mock_hide:
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
            "result": "Temperature: 23°C, Sunny"
        }
        
        await client_app.handle_server_message(message_data)
        # Sprawdź czy wiadomość została przetworzona bez błędów
    
    @pytest.mark.asyncio
    async def test_handle_plugin_toggled(self, client_app):
        """Test obsługi przełączenia pluginu."""
        message_data = {
            "type": "plugin_toggled",
            "plugin": "weather_plugin",
            "status": "enabled"
        }
        
        await client_app.handle_server_message(message_data)
        # Sprawdź czy wiadomość została przetworzona bez błędów
    
    @pytest.mark.asyncio
    async def test_handle_startup_briefing(self, client_app):
        """Test obsługi briefingu startowego."""
        briefing_data = {
            "weather": "Sunny, 22°C",
            "calendar": "2 meetings today",
            "news": "Technology update"
        }
        
        with patch.object(client_app, 'format_briefing_text', return_value="Formatted briefing") as mock_format:
            with patch.object(client_app, 'show_overlay') as mock_show:
                client_app.tts = AsyncMock()
                client_app.tts.speak = AsyncMock()
                
                await client_app.handle_startup_briefing(briefing_data)
        
        mock_format.assert_called_once_with(briefing_data)
        client_app.tts.speak.assert_called_once_with("Formatted briefing")
    
    @pytest.mark.asyncio
    async def test_handle_day_summary(self, client_app):
        """Test obsługi podsumowania dnia."""
        summary_data = {
            "total_interactions": 25,
            "most_used_features": ["AI chat", "weather"],
            "productivity_score": 8.5
        }
        
        with patch.object(client_app, 'format_summary_text', return_value="Daily summary") as mock_format:
            with patch.object(client_app, 'show_overlay') as mock_show:
                client_app.tts = AsyncMock()
                client_app.tts.speak = AsyncMock()
                
                await client_app.handle_day_summary(summary_data)
        
        mock_format.assert_called_once_with(summary_data)
        client_app.tts.speak.assert_called_once_with("Daily summary")
    
    @pytest.mark.asyncio
    async def test_handle_error_message(self, client_app):
        """Test obsługi wiadomości błędu."""
        message_data = {
            "type": "error",
            "error": "Server error occurred"
        }
        
        with patch.object(client_app, 'update_status') as mock_update:
            await client_app.handle_server_message(message_data)
            
        mock_update.assert_called_with("Error")
    
    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, client_app):
        """Test obsługi nieznanego typu wiadomości."""
        message_data = {
            "type": "unknown_type",
            "data": "some data"
        }
        
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
        client_app.audio_recorder = mock_audio_components["audio_recorder"]
        client_app.whisper_asr = mock_audio_components["whisper_asr"]
        
        # Mock audio data
        mock_audio_data = create_mock_audio_data(2.0)  # 2 sekundy audio
        client_app.audio_recorder.get_audio_data.return_value = mock_audio_data
        
        # Mock transkrypcji
        client_app.whisper_asr.transcribe.return_value = "Hello, what's the weather?"
        
        with patch.object(client_app, 'send_to_server') as mock_send:
            await client_app.record_and_transcribe()
        
        client_app.audio_recorder.start_recording.assert_called_once()
        client_app.audio_recorder.stop_recording.assert_called_once()
        client_app.whisper_asr.transcribe.assert_called_once()
        mock_send.assert_called_once()
    
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
        with patch('client.client_main.list_audio_devices') as mock_list:
            mock_list.return_value = [
                {"name": "Microphone", "index": 0, "channels": 1},
                {"name": "Speakers", "index": 1, "channels": 2}
            ]
            
            devices = client_app.list_available_audio_devices()
            
            assert len(devices) == 2
            assert devices[0]["name"] == "Microphone"


class TestHTTPInterface:
    """Testy interfejsu HTTP dla overlay."""
    
    def test_status_endpoint(self, client_app):
        """Test endpointu statusu."""
        handler = StatusHTTPHandler(client_app, None, None, None)
        
        # Mock request
        handler.path = "/status"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        
        client_app.current_status = "Listening..."
        client_app.wake_word_detected = False
        client_app.tts_playing = False
        
        handler.do_GET()
        
        handler.send_response.assert_called_with(200)
        handler.wfile.write.assert_called_once()
        
        # Sprawdź czy odpowiedź zawiera status
        written_data = handler.wfile.write.call_args[0][0]
        response_json = json.loads(written_data.decode())
        assert response_json["status"] == "Listening..."
        assert response_json["wake_word_detected"] is False
        assert response_json["tts_playing"] is False
    
    def test_trigger_wakeword_endpoint(self, client_app):
        """Test endpointu triggera wakeword."""
        handler = StatusHTTPHandler(client_app, None, None, None)
        
        # Mock request
        handler.path = "/trigger_wakeword?query=test%20query"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        
        client_app.wakeword_detector = Mock()
        client_app.command_queue = Mock()
        client_app.command_queue.put = Mock()
        
        handler.do_GET()
        
        handler.send_response.assert_called_with(200)
        client_app.command_queue.put.assert_called_once()
        
        # Sprawdź wywołanie komendy
        command = client_app.command_queue.put.call_args[0][0]
        assert command["type"] == "test_wakeword"
        assert command["query"] == "test query"
    
    def test_sse_stream_endpoint(self, client_app):
        """Test endpointu SSE stream."""
        handler = StatusHTTPHandler(client_app, None, None, None)
        
        # Mock request
        handler.path = "/status/stream"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        
        client_app.current_status = "Ready"
        
        handler.do_GET()
        
        handler.send_response.assert_called_with(200)
        assert any(call[0][0] == 'Content-Type' and 'text/event-stream' in call[0][1] 
                  for call in handler.send_header.call_args_list)
    
    def test_cors_headers(self, client_app):
        """Test nagłówków CORS."""
        handler = StatusHTTPHandler(client_app, None, None, None)
        
        # Mock request
        handler.path = "/status"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        
        handler.do_GET()
        
        # Sprawdź czy nagłówki CORS zostały dodane
        cors_calls = [call for call in handler.send_header.call_args_list 
                     if 'Access-Control-Allow-Origin' in call[0]]
        assert len(cors_calls) > 0


class TestCommandQueue:
    """Testy kolejki komend."""
    
    @pytest.mark.asyncio
    async def test_command_queue_processing(self, client_app):
        """Test przetwarzania kolejki komend."""
        import queue
        client_app.command_queue = queue.Queue()
        client_app.running = True
        
        # Dodaj komendę do kolejki
        test_command = {"type": "test_wakeword", "query": "hello"}
        client_app.command_queue.put(test_command)
        
        with patch.object(client_app, 'execute_command') as mock_execute:
            # Uruchom jeden cykl przetwarzania
            client_app.running = False  # Zatrzymaj po jednym cyklu
            await client_app.process_command_queue()
        
        mock_execute.assert_called_once_with(test_command)
    
    @pytest.mark.asyncio
    async def test_execute_test_wakeword_command(self, client_app):
        """Test wykonania komendy test wakeword."""
        command = {"type": "test_wakeword", "query": "test query"}
        
        with patch.object(client_app, 'process_wakeword_detection') as mock_process:
            await client_app.execute_command(command)
        
        mock_process.assert_called_once_with("test query")
    
    @pytest.mark.asyncio
    async def test_execute_status_update_command(self, client_app):
        """Test wykonania komendy aktualizacji statusu."""
        command = {"type": "status_update", "status": "New Status"}
        
        with patch.object(client_app, 'update_status') as mock_update:
            await client_app.execute_command(command)
        
        mock_update.assert_called_once_with("New Status")
    
    @pytest.mark.asyncio
    async def test_execute_unknown_command(self, client_app):
        """Test wykonania nieznanej komendy."""
        command = {"type": "unknown_command", "data": "test"}
        
        # Nie powinno rzucać wyjątku
        await client_app.execute_command(command)


class TestClientWorkflow:
    """Testy przepływu pracy klienta."""
    
    @pytest.mark.asyncio
    async def test_wakeword_to_response_workflow(self, client_app, mock_audio_components):
        """Test pełnego przepływu od wakeword do odpowiedzi."""
        # Setup komponentów
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]
        client_app.audio_recorder = mock_audio_components["audio_recorder"]
        client_app.whisper_asr = mock_audio_components["whisper_asr"]
        client_app.tts = mock_audio_components["tts"]
        client_app.websocket = AsyncMock()
        
        # Mock transkrypcji i odpowiedzi
        mock_audio_data = create_mock_audio_data(2.0)
        client_app.audio_recorder.get_audio_data.return_value = mock_audio_data
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
            "response": '{"text": "The weather is sunny, 22°C"}'
        }
        await client_app.handle_server_message(server_response)
        
        # 4. Sprawdź czy TTS zostało uruchomione
        client_app.tts.speak.assert_called_once_with("The weather is sunny, 22°C")
    
    @pytest.mark.asyncio
    async def test_startup_sequence(self, client_app, mock_audio_components):
        """Test sekwencji startowej klienta."""
        # Mock komponentów
        with patch.multiple(
            'client.client_main',
            create_wakeword_detector=Mock(return_value=mock_audio_components["wakeword_detector"]),
            create_whisper_asr=Mock(return_value=mock_audio_components["whisper_asr"]),
            create_audio_recorder=Mock(return_value=mock_audio_components["audio_recorder"]),
            TTSModule=Mock(return_value=mock_audio_components["tts"])
        ):
            with patch.object(client_app, 'start_http_server'):
                with patch.object(client_app, 'connect_to_server'):
                    with patch.object(client_app, 'listen_for_messages'):
                        with patch.object(client_app, 'process_command_queue'):
                            with patch.object(client_app, 'periodic_proactive_check'):
                                # Symuluj krótkie uruchomienie
                                async def short_run():
                                    client_app.running = True
                                    await asyncio.sleep(0.1)
                                    client_app.running = False
                                
                                with patch.object(client_app, 'start_wakeword_monitoring'):
                                    await short_run()
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, client_app):
        """Test odzyskiwania po błędach."""
        # Test odzyskiwania po utracie połączenia WebSocket
        client_app.websocket = AsyncMock()
        client_app.websocket.recv.side_effect = Exception("Connection lost")
        
        with patch.object(client_app, 'connect_to_server') as mock_reconnect:
            # Symuluj próbę nasłuchiwania z błędem
            client_app.running = True
            try:
                await client_app.listen_for_messages()
            except:
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
            "response": '{"text": "Hello there!"}'
        }
        
        with patch.object(client_app, 'handle_server_message') as mock_handle:
            # Symuluj odbiór wiadomości
            await mock_handle(response_message)
            mock_handle.assert_called_once_with(response_message)
    
    @pytest.mark.asyncio
    async def test_audio_pipeline_integration(self, client_app, mock_audio_components):
        """Test integracji pipeline audio."""
        # Setup wszystkich komponentów audio
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]
        client_app.audio_recorder = mock_audio_components["audio_recorder"]
        client_app.whisper_asr = mock_audio_components["whisper_asr"]
        client_app.tts = mock_audio_components["tts"]
        
        # Mock audio data i transkrypcji
        audio_data = create_mock_audio_data(3.0)
        client_app.audio_recorder.get_audio_data.return_value = audio_data
        client_app.whisper_asr.transcribe.return_value = "Test transcription"
        
        # Test pełnego pipeline
        with patch.object(client_app, 'send_to_server') as mock_send:
            await client_app.record_and_transcribe()
        
        # Sprawdź sekwencję wywołań
        client_app.audio_recorder.start_recording.assert_called_once()
        client_app.audio_recorder.stop_recording.assert_called_once()
        client_app.whisper_asr.transcribe.assert_called_once_with(audio_data)
        mock_send.assert_called_once()
        
        # Sprawdź wysłaną wiadomość
        sent_message = mock_send.call_args[0][0]
        assert sent_message["type"] == "ai_query"
        assert sent_message["query"] == "Test transcription"
    
    @pytest.mark.asyncio
    async def test_overlay_integration(self, client_app):
        """Test integracji z overlay."""
        import queue
        client_app.command_queue = queue.Queue()
        
        # Test HTTP server dla overlay
        with patch.object(client_app, 'start_http_server'):
            with patch.object(client_app, 'send_overlay_update') as mock_update:
                await client_app.show_overlay()
                mock_update.assert_called_once()
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_proactive_notifications(self, client_app):
        """Test proaktywnych powiadomień."""
        client_app.websocket = AsyncMock()
        
        with patch.object(client_app, 'send_to_server') as mock_send:
            await client_app.periodic_proactive_check()
        
        # Sprawdź czy wysłano request o powiadomienia
        mock_send.assert_called_once()
        sent_message = mock_send.call_args[0][0]
        assert sent_message["type"] == "get_proactive_notifications"

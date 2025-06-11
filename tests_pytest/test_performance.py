"""
Testy wydajności i obciążenia dla GAJA Assistant
"""

import asyncio
import json
import time
import pytest
import psutil
import os
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

from server.server_main import ServerApp, ConnectionManager
from client.client_main import ClientApp


@pytest.mark.slow
@pytest.mark.performance
class TestServerPerformance:
    """Testy wydajności serwera."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, server_app):
        """Test wydajności przy wielu jednoczesnych połączeniach."""
        connection_manager = server_app.connection_manager
        num_connections = 50
        
        # Utwórz mock WebSockets
        mock_websockets = []
        for i in range(num_connections):
            mock_ws = AsyncMock()
            mock_websockets.append(mock_ws)
        
        # Zmierz czas połączenia wszystkich klientów
        start_time = time.time()
        
        connect_tasks = []
        for i, mock_ws in enumerate(mock_websockets):
            task = connection_manager.connect(mock_ws, f"user_{i}")
            connect_tasks.append(task)
        
        await asyncio.gather(*connect_tasks)
        
        connect_time = time.time() - start_time
        
        # Sprawdź czy wszystkie połączenia zostały ustanowione
        assert len(connection_manager.active_connections) == num_connections
        
        # Sprawdź wydajność połączeń (powinno być szybsze niż 5 sekund)
        assert connect_time < 5.0, f"Connection time: {connect_time:.2f}s for {num_connections} users"
        
        # Test broadcast do wszystkich użytkowników
        message = {"type": "performance_test", "data": "broadcast"}
        
        broadcast_start = time.time()
        await connection_manager.broadcast(message)
        broadcast_time = time.time() - broadcast_start
        
        # Broadcast powinien być szybki nawet dla wielu użytkowników
        assert broadcast_time < 2.0, f"Broadcast time: {broadcast_time:.2f}s for {num_connections} users"
        
        # Sprawdź czy wszystkie WebSockets otrzymały wiadomość
        for mock_ws in mock_websockets:
            mock_ws.send_text.assert_called_once_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_high_frequency_requests(self, server_app):
        """Test wydajności przy wysokiej częstotliwości requestów."""
        user_id = "performance_user"
        num_requests = 100
        
        # Mock AI module dla szybkich odpowiedzi
        server_app.ai_module.get_response.return_value = {
            "text": "Quick response",
            "confidence": 0.9
        }
        
        # Utwórz wiele requestów
        requests = []
        for i in range(num_requests):
            request = {
                "type": "ai_query",
                "query": f"Performance test query {i}",
                "context": {"test_id": i}
            }
            requests.append(request)
        
        # Zmierz czas przetwarzania
        start_time = time.time()
        
        # Przetwórz wszystkie requesty sekwencyjnie
        responses = []
        for request in requests:
            response = await server_app.process_user_request(user_id, request)
            responses.append(response)
        
        processing_time = time.time() - start_time
        
        # Sprawdź wyniki
        assert len(responses) == num_requests
        for response in responses:
            assert response["type"] == "ai_response"
        
        # Sprawdź wydajność (średnio mniej niż 100ms na request)
        avg_time = processing_time / num_requests
        assert avg_time < 0.1, f"Average processing time: {avg_time:.3f}s per request"
        
        print(f"Processed {num_requests} requests in {processing_time:.2f}s")
        print(f"Average time per request: {avg_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_request_processing(self, server_app):
        """Test równoczesnego przetwarzania requestów."""
        num_users = 10
        requests_per_user = 20
        
        # Mock AI module
        server_app.ai_module.get_response.return_value = {
            "text": "Concurrent response",
            "confidence": 0.9
        }
        
        async def user_request_batch(user_id, num_requests):
            """Symuluj batch requestów od jednego użytkownika."""
            responses = []
            for i in range(num_requests):
                request = {
                    "type": "ai_query",
                    "query": f"User {user_id} query {i}",
                    "context": {}
                }
                response = await server_app.process_user_request(user_id, request)
                responses.append(response)
            return responses
        
        # Uruchom wszystkich użytkowników równocześnie
        start_time = time.time()
        
        user_tasks = []
        for user_i in range(num_users):
            user_id = f"concurrent_user_{user_i}"
            task = user_request_batch(user_id, requests_per_user)
            user_tasks.append(task)
        
        all_responses = await asyncio.gather(*user_tasks)
        
        concurrent_time = time.time() - start_time
        
        # Sprawdź wyniki
        total_requests = num_users * requests_per_user
        total_responses = sum(len(responses) for responses in all_responses)
        
        assert total_responses == total_requests
        
        # Sprawdź wydajność concurrent vs sequential
        print(f"Concurrent processing: {concurrent_time:.2f}s for {total_requests} requests")
        print(f"Requests per second: {total_requests / concurrent_time:.1f}")
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, server_app):
        """Test użycia pamięci pod obciążeniem."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Symuluj ciężkie obciążenie
        num_iterations = 50
        requests_per_iteration = 20
        
        memory_samples = [initial_memory]
        
        for iteration in range(num_iterations):
            # Utwórz batch requestów
            for i in range(requests_per_iteration):
                request = {
                    "type": "ai_query",
                    "query": f"Memory test iteration {iteration} request {i}" * 10,  # Długi tekst
                    "context": {"large_data": "x" * 1000}  # Duże dane kontekstowe
                }
                
                try:
                    await server_app.process_user_request(f"memory_user_{i}", request)
                except:
                    pass  # Ignoruj błędy dla testu pamięci
            
            # Próbuj wymusić garbage collection
            import gc
            gc.collect()
            
            # Pobierz użycie pamięci
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
            # Sprawdź czy pamięć nie rośnie nadmiernie
            memory_increase = current_memory - initial_memory
            if memory_increase > 200:  # 200MB limit
                pytest.fail(f"Memory usage increased by {memory_increase:.1f}MB after {iteration} iterations")
        
        final_memory = memory_samples[-1]
        max_memory = max(memory_samples)
        
        print(f"Initial memory: {initial_memory:.1f}MB")
        print(f"Final memory: {final_memory:.1f}MB")
        print(f"Max memory: {max_memory:.1f}MB")
        print(f"Memory increase: {final_memory - initial_memory:.1f}MB")
        
        # Sprawdź czy wzrost pamięci jest rozsądny
        assert final_memory - initial_memory < 100, "Memory increase too high"


@pytest.mark.slow
@pytest.mark.performance
class TestClientPerformance:
    """Testy wydajności klienta."""
    
    @pytest.mark.asyncio
    async def test_audio_processing_performance(self, client_app, mock_audio_components):
        """Test wydajności przetwarzania audio."""
        # Setup komponentów audio
        client_app.wakeword_detector = mock_audio_components["wakeword_detector"]
        client_app.audio_recorder = mock_audio_components["audio_recorder"]
        client_app.whisper_asr = mock_audio_components["whisper_asr"]
        client_app.tts = mock_audio_components["tts"]
        
        # Mock szybkiej transkrypcji
        client_app.whisper_asr.transcribe.return_value = "Fast transcription"
        
        from conftest import create_mock_audio_data
        
        # Test różnych długości audio
        audio_durations = [1.0, 2.0, 5.0, 10.0]  # sekundy
        
        for duration in audio_durations:
            mock_audio = create_mock_audio_data(duration)
            client_app.audio_recorder.get_audio_data.return_value = mock_audio
            
            # Zmierz czas przetwarzania
            start_time = time.time()
            
            with patch.object(client_app, 'send_to_server'):
                await client_app.record_and_transcribe()
            
            processing_time = time.time() - start_time
            
            # Sprawdź czy przetwarzanie jest szybsze niż real-time + buffer
            max_expected_time = duration + 2.0  # 2 sekundy buffer
            assert processing_time < max_expected_time, \
                f"Audio processing too slow: {processing_time:.2f}s for {duration}s audio"
            
            print(f"Audio {duration}s processed in {processing_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self, client_app):
        """Test przepustowości wiadomości WebSocket."""
        mock_websocket = AsyncMock()
        client_app.websocket = mock_websocket
        
        num_messages = 100
        messages = []
        
        # Utwórz wiadomości
        for i in range(num_messages):
            message = {
                "type": "ai_query",
                "query": f"Throughput test message {i}",
                "context": {"test_id": i}
            }
            messages.append(message)
        
        # Zmierz czas wysyłania
        start_time = time.time()
        
        for message in messages:
            await client_app.send_to_server(message)
        
        send_time = time.time() - start_time
        
        # Sprawdź przepustowość
        messages_per_second = num_messages / send_time
        
        # Powinno być możliwe wysłanie przynajmniej 100 wiadomości na sekundę
        assert messages_per_second > 100, f"Message throughput too low: {messages_per_second:.1f} msg/s"
        
        print(f"WebSocket throughput: {messages_per_second:.1f} messages/second")
    
    @pytest.mark.asyncio
    async def test_overlay_update_performance(self, client_app):
        """Test wydajności aktualizacji overlay."""
        import queue
        client_app.command_queue = queue.Queue()
        
        num_updates = 200
        
        with patch.object(client_app, 'send_overlay_update') as mock_update:
            start_time = time.time()
            
            # Wykonaj wiele szybkich aktualizacji statusu
            for i in range(num_updates):
                status = f"Status update {i}"
                client_app.update_status(status)
                await client_app.show_overlay()
            
            update_time = time.time() - start_time
        
        # Sprawdź wydajność aktualizacji
        updates_per_second = num_updates / update_time
        
        # Powinno być możliwe przynajmniej 50 aktualizacji na sekundę
        assert updates_per_second > 50, f"Overlay update rate too low: {updates_per_second:.1f} updates/s"
        
        print(f"Overlay update rate: {updates_per_second:.1f} updates/second")
    
    @pytest.mark.asyncio
    async def test_command_queue_performance(self, client_app):
        """Test wydajności kolejki komend."""
        import queue
        client_app.command_queue = queue.Queue()
        client_app.running = True
        
        num_commands = 500
        
        # Dodaj komendy do kolejki
        for i in range(num_commands):
            command = {
                "type": "status_update",
                "status": f"Command {i}"
            }
            client_app.command_queue.put(command)
        
        # Zmierz czas przetwarzania
        with patch.object(client_app, 'execute_command') as mock_execute:
            mock_execute.return_value = asyncio.coroutine(lambda: None)()
            
            start_time = time.time()
            
            # Przetworz jedną porcję komend
            processed = 0
            while not client_app.command_queue.empty() and processed < num_commands:
                try:
                    command = client_app.command_queue.get_nowait()
                    await client_app.execute_command(command)
                    processed += 1
                except queue.Empty:
                    break
            
            processing_time = time.time() - start_time
        
        # Sprawdź wydajność
        commands_per_second = processed / processing_time if processing_time > 0 else 0
        
        assert commands_per_second > 200, f"Command processing too slow: {commands_per_second:.1f} cmd/s"
        assert processed == num_commands, f"Not all commands processed: {processed}/{num_commands}"
        
        print(f"Command queue throughput: {commands_per_second:.1f} commands/second")


@pytest.mark.slow
@pytest.mark.performance
class TestIntegratedPerformance:
    """Testy wydajności zintegrowanego systemu."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_performance(self, server_app, client_app):
        """Test wydajności pełnej konwersacji."""
        num_conversations = 20
        
        # Setup klienta
        client_app.websocket = AsyncMock()
        client_app.tts = AsyncMock()
        
        # Setup serwera
        server_app.ai_module.get_response.return_value = {
            "text": "Performance test response",
            "confidence": 0.9
        }
        
        conversation_times = []
        
        for i in range(num_conversations):
            start_time = time.time()
            
            # 1. Klient wysyła zapytanie
            query_message = {
                "type": "ai_query",
                "query": f"Performance conversation {i}",
                "context": {}
            }
            
            # 2. Serwer przetwarza
            response = await server_app.process_user_request("perf_user", query_message)
            
            # 3. Klient odbiera i przetwarza odpowiedź
            await client_app.handle_server_message(response)
            
            conversation_time = time.time() - start_time
            conversation_times.append(conversation_time)
        
        # Analiza wydajności
        avg_time = sum(conversation_times) / len(conversation_times)
        max_time = max(conversation_times)
        min_time = min(conversation_times)
        
        print(f"Conversation performance:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")
        print(f"  Min: {min_time:.3f}s")
        
        # Sprawdź czy średni czas jest rozsądny (mniej niż 1 sekunda)
        assert avg_time < 1.0, f"Average conversation time too high: {avg_time:.3f}s"
        assert max_time < 2.0, f"Max conversation time too high: {max_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_system_stability_under_load(self, server_app, client_app):
        """Test stabilności systemu pod obciążeniem."""
        # Setup
        num_clients = 5
        duration_seconds = 30
        requests_per_client_per_second = 2
        
        client_app.websocket = AsyncMock()
        server_app.ai_module.get_response.return_value = {
            "text": "Stability test response",
            "confidence": 0.9
        }
        
        async def client_load_generator(client_id, duration, rate):
            """Generator obciążenia dla jednego klienta."""
            end_time = time.time() + duration
            request_count = 0
            
            while time.time() < end_time:
                request = {
                    "type": "ai_query",
                    "query": f"Client {client_id} request {request_count}",
                    "context": {}
                }
                
                try:
                    await server_app.process_user_request(f"load_client_{client_id}", request)
                    request_count += 1
                except Exception as e:
                    print(f"Error in client {client_id}: {e}")
                
                # Kontrola częstotliwości
                await asyncio.sleep(1.0 / rate)
            
            return request_count
        
        # Uruchom wszystkich klientów równocześnie
        print(f"Starting load test: {num_clients} clients for {duration_seconds}s")
        
        start_time = time.time()
        
        client_tasks = []
        for client_id in range(num_clients):
            task = client_load_generator(client_id, duration_seconds, requests_per_client_per_second)
            client_tasks.append(task)
        
        request_counts = await asyncio.gather(*client_tasks, return_exceptions=True)
        
        actual_duration = time.time() - start_time
        
        # Analiza wyników
        total_requests = sum(count for count in request_counts if isinstance(count, int))
        expected_requests = num_clients * duration_seconds * requests_per_client_per_second
        
        print(f"Load test results:")
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Total requests: {total_requests}")
        print(f"  Expected requests: {expected_requests}")
        print(f"  Success rate: {total_requests / expected_requests * 100:.1f}%")
        
        # Sprawdź stabilność (przynajmniej 80% requestów powinno się udać)
        success_rate = total_requests / expected_requests
        assert success_rate > 0.8, f"System stability too low: {success_rate * 100:.1f}% success rate"


@pytest.mark.slow
@pytest.mark.performance
class TestResourceUsage:
    """Testy użycia zasobów."""
    
    def test_cpu_usage_monitoring(self):
        """Test monitorowania użycia CPU."""
        import threading
        import time
        
        # Monitor CPU w tle
        cpu_samples = []
        monitoring = True
        
        def cpu_monitor():
            while monitoring:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_samples.append(cpu_percent)
                time.sleep(0.1)
        
        monitor_thread = threading.Thread(target=cpu_monitor, daemon=True)
        monitor_thread.start()
        
        # Symuluj obciążenie przez 5 sekund
        import math
        end_time = time.time() + 5
        while time.time() < end_time:
            # Lekkie obciążenie CPU
            _ = sum(math.sqrt(i) for i in range(1000))
        
        monitoring = False
        monitor_thread.join(timeout=1)
        
        if cpu_samples:
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            max_cpu = max(cpu_samples)
            
            print(f"CPU usage during test:")
            print(f"  Average: {avg_cpu:.1f}%")
            print(f"  Maximum: {max_cpu:.1f}%")
            
            # Sprawdź czy CPU nie jest nadmiernie wykorzystywane
            assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu:.1f}%"
    
    def test_memory_leak_detection(self):
        """Test wykrywania wycieków pamięci."""
        import gc
        
        process = psutil.Process(os.getpid())
        
        # Bazowe użycie pamięci
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Symuluj operacje które mogą powodować wycieki
        objects = []
        for i in range(1000):
            # Utwórz obiekty które mogą być problematyczne
            obj = {
                "id": i,
                "data": "x" * 1000,
                "nested": {"more_data": list(range(100))}
            }
            objects.append(obj)
        
        mid_memory = process.memory_info().rss / 1024 / 1024
        
        # Usuń obiekty
        objects.clear()
        del objects
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        print(f"Memory leak test:")
        print(f"  Initial: {initial_memory:.1f}MB")
        print(f"  With objects: {mid_memory:.1f}MB")
        print(f"  After cleanup: {final_memory:.1f}MB")
        
        # Sprawdź czy pamięć została zwolniona (z małym marginesem na GC)
        memory_retained = final_memory - initial_memory
        assert memory_retained < 10, f"Possible memory leak: {memory_retained:.1f}MB retained"


if __name__ == "__main__":
    # Uruchom testy wydajności
    pytest.main([__file__, "-v", "-m", "performance"])

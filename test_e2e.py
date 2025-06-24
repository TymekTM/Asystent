#!/usr/bin/env python3
"""End-to-End Test Suite dla GAJA Assistant Zgodnie z checklistą w todo.md."""

import asyncio
import json
import logging
import sys
import time
from typing import Any

import aiohttp
import websockets

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GajaE2ETester:
    """End-to-end tester dla systemu GAJA."""

    def __init__(
        self,
        server_url: str = "http://localhost:8001",
        ws_url: str = "ws://localhost:8001/ws/",
    ):
        self.server_url = server_url
        self.ws_url = ws_url
        self.test_results = {}
        self.start_time = time.time()

    def log_test_result(
        self, test_name: str, passed: bool, details: str = "", duration: float = None
    ):
        """Loguje wynik testu."""
        status = "✅ PASSED" if passed else "❌ FAILED"
        if duration:
            print(f"{status} | {test_name} | {duration:.2f}s | {details}")
        else:
            print(f"{status} | {test_name} | {details}")

        self.test_results[test_name] = {
            "passed": passed,
            "details": details,
            "duration": duration,
            "timestamp": time.time(),
        }

    async def test_1_server_availability(self) -> bool:
        """Test 1: Podstawowa dostępność serwera"""
        test_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        self.log_test_result(
                            "Server Availability",
                            True,
                            f"Server responding on {self.server_url}",
                            time.time() - test_start,
                        )
                        return True
                    else:
                        self.log_test_result(
                            "Server Availability",
                            False,
                            f"Server returned status {response.status}",
                            time.time() - test_start,
                        )
                        return False
        except Exception as e:
            self.log_test_result(
                "Server Availability",
                False,
                f"Connection failed: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_2_websocket_flow(self) -> bool:
        """Test 2: Pełny flow WebSocket (input → intent → response)"""
        test_start = time.time()
        user_id = f"test_user_{int(time.time())}"

        try:
            async with websockets.connect(f"{self.ws_url}{user_id}") as websocket:
                # Test 1: Symulacja wejścia głosowego
                voice_input = {
                    "type": "voice_input",
                    "content": "Jaka jest dzisiaj pogoda?",
                    "timestamp": time.time(),
                    "language": "pl",
                }

                await websocket.send(json.dumps(voice_input))

                # Oczekiwanie na odpowiedź AI
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)

                    if response_data.get("type") in ["ai_response", "error"]:
                        self.log_test_result(
                            "WebSocket Voice Flow",
                            True,
                            f"Received response type: {response_data.get('type')}",
                            time.time() - test_start,
                        )
                        return True
                    else:
                        self.log_test_result(
                            "WebSocket Voice Flow",
                            False,
                            f"Unexpected response type: {response_data.get('type')}",
                            time.time() - test_start,
                        )
                        return False

                except TimeoutError:
                    self.log_test_result(
                        "WebSocket Voice Flow",
                        False,
                        "Server timeout - no response in 10s",
                        time.time() - test_start,
                    )
                    return False

        except Exception as e:
            self.log_test_result(
                "WebSocket Voice Flow",
                False,
                f"WebSocket error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_3_plugin_system(self) -> bool:
        """Test 3: System pluginów"""
        test_start = time.time()
        user_id = f"test_user_{int(time.time())}"

        try:
            async with websockets.connect(f"{self.ws_url}{user_id}") as websocket:
                # Test różnych typów zapytań które powinny wywołać pluginy
                test_queries = [
                    "Jaka jest dzisiaj pogoda?",  # Weather plugin
                    "Znajdź informacje o Python",  # Search plugin
                    "Jak się masz?",  # General LLM fallback
                ]

                plugin_responses = []

                for query in test_queries:
                    message = {
                        "type": "user_input",
                        "content": query,
                        "timestamp": time.time(),
                    }

                    await websocket.send(json.dumps(message))

                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        plugin_responses.append(response_data)

                        # Krótka przerwa między zapytaniami
                        await asyncio.sleep(1)

                    except TimeoutError:
                        plugin_responses.append({"type": "timeout", "query": query})

                # Sprawdź czy otrzymano odpowiedzi
                successful_responses = [
                    r for r in plugin_responses if r.get("type") != "timeout"
                ]

                if len(successful_responses) >= 2:  # Przynajmniej 2 z 3 zapytań
                    self.log_test_result(
                        "Plugin System",
                        True,
                        f"Received {len(successful_responses)}/3 plugin responses",
                        time.time() - test_start,
                    )
                    return True
                else:
                    self.log_test_result(
                        "Plugin System",
                        False,
                        f"Only {len(successful_responses)}/3 responses received",
                        time.time() - test_start,
                    )
                    return False

        except Exception as e:
            self.log_test_result(
                "Plugin System",
                False,
                f"Plugin test error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_4_memory_system(self) -> bool:
        """Test 4: System pamięci (short-term)"""
        test_start = time.time()
        user_id = f"test_user_{int(time.time())}"

        try:
            async with websockets.connect(f"{self.ws_url}{user_id}") as websocket:
                # Pierwsza wiadomość z kontekstem
                first_message = {
                    "type": "user_input",
                    "content": "Nazywam się Test User i lubię kawę",
                    "timestamp": time.time(),
                }

                await websocket.send(json.dumps(first_message))

                # Odbierz pierwszą odpowiedź
                await asyncio.wait_for(websocket.recv(), timeout=5.0)

                # Poczekaj chwilę
                await asyncio.sleep(2)

                # Druga wiadomość odwołująca się do kontekstu
                second_message = {
                    "type": "user_input",
                    "content": "Jak się nazywam?",
                    "timestamp": time.time(),
                }

                await websocket.send(json.dumps(second_message))

                # Sprawdź czy pamięta kontekst
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)

                # Sprawdź czy odpowiedź zawiera wcześniejszą informację
                response_content = response_data.get("content", "").lower()

                if "test user" in response_content or "test" in response_content:
                    self.log_test_result(
                        "Memory System",
                        True,
                        "System remembers previous context",
                        time.time() - test_start,
                    )
                    return True
                else:
                    self.log_test_result(
                        "Memory System",
                        False,
                        "System does not remember context",
                        time.time() - test_start,
                    )
                    return False

        except Exception as e:
            self.log_test_result(
                "Memory System",
                False,
                f"Memory test error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_5_multi_user(self) -> bool:
        """Test 5: Obsługa wielu użytkowników"""
        test_start = time.time()

        try:
            # Utwórz 3 równoczesne połączenia
            user_ids = [f"user_{i}_{int(time.time())}" for i in range(3)]
            connections = []

            # Połącz wszystkich użytkowników
            for user_id in user_ids:
                ws = await websockets.connect(f"{self.ws_url}{user_id}")
                connections.append((user_id, ws))

            # Wyślij równocześnie zapytania od wszystkich użytkowników
            tasks = []
            for user_id, ws in connections:
                message = {
                    "type": "user_input",
                    "content": f"Jestem użytkownik {user_id}",
                    "timestamp": time.time(),
                }
                tasks.append(ws.send(json.dumps(message)))

            await asyncio.gather(*tasks)

            # Odbierz odpowiedzi
            responses = []
            for _, ws in connections:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    responses.append(json.loads(response))
                except TimeoutError:
                    responses.append({"type": "timeout"})

            # Zamknij połączenia
            for _, ws in connections:
                await ws.close()

            # Sprawdź wyniki
            successful_responses = [r for r in responses if r.get("type") != "timeout"]

            if len(successful_responses) >= 2:  # Przynajmniej 2 z 3 użytkowników
                self.log_test_result(
                    "Multi-User Support",
                    True,
                    f"{len(successful_responses)}/3 users handled successfully",
                    time.time() - test_start,
                )
                return True
            else:
                self.log_test_result(
                    "Multi-User Support",
                    False,
                    f"Only {len(successful_responses)}/3 users handled",
                    time.time() - test_start,
                )
                return False

        except Exception as e:
            self.log_test_result(
                "Multi-User Support",
                False,
                f"Multi-user test error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_6_error_handling(self) -> bool:
        """Test 6: Obsługa błędów i fallbacków"""
        test_start = time.time()
        user_id = f"test_user_{int(time.time())}"

        try:
            async with websockets.connect(f"{self.ws_url}{user_id}") as websocket:
                # Test różnych przypadków błędów
                error_tests = [
                    {"type": "invalid_type", "content": "test"},  # Nieprawidłowy typ
                    {"type": "user_input", "content": ""},  # Pusta treść
                    {"malformed": "json"},  # Niepełny JSON
                ]

                error_responses = []

                for test_data in error_tests:
                    await websocket.send(json.dumps(test_data))

                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        error_responses.append(response_data)

                        await asyncio.sleep(0.5)  # Krótka przerwa

                    except TimeoutError:
                        error_responses.append({"type": "timeout"})

                # Sprawdź czy serwer obsłużył błędy bez crashowania
                handled_errors = [
                    r
                    for r in error_responses
                    if r.get("type") in ["error", "ai_response"]
                ]

                if len(handled_errors) >= 2:
                    self.log_test_result(
                        "Error Handling",
                        True,
                        f"Server handled {len(handled_errors)}/3 error cases",
                        time.time() - test_start,
                    )
                    return True
                else:
                    self.log_test_result(
                        "Error Handling",
                        False,
                        f"Server handled only {len(handled_errors)}/3 error cases",
                        time.time() - test_start,
                    )
                    return False

        except Exception as e:
            self.log_test_result(
                "Error Handling",
                False,
                f"Error handling test failed: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_7_performance_basic(self) -> bool:
        """Test 7: Podstawowa wydajność"""
        test_start = time.time()
        user_id = f"test_user_{int(time.time())}"

        try:
            async with websockets.connect(f"{self.ws_url}{user_id}") as websocket:
                # Test szybkości odpowiedzi
                response_times = []

                for i in range(5):
                    msg_start = time.time()

                    message = {
                        "type": "user_input",
                        "content": f"Test message {i+1}",
                        "timestamp": time.time(),
                    }

                    await websocket.send(json.dumps(message))

                    try:
                        await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        response_time = time.time() - msg_start
                        response_times.append(response_time)

                        await asyncio.sleep(0.5)  # Przerwa między testami

                    except TimeoutError:
                        response_times.append(10.0)  # Timeout

                # Analiza wydajności
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)

                # Kryteria: średnia < 5s, max < 10s
                if avg_response_time < 5.0 and max_response_time < 10.0:
                    self.log_test_result(
                        "Performance Basic",
                        True,
                        f"Avg: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s",
                        time.time() - test_start,
                    )
                    return True
                else:
                    self.log_test_result(
                        "Performance Basic",
                        False,
                        f"Too slow - Avg: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s",
                        time.time() - test_start,
                    )
                    return False

        except Exception as e:
            self.log_test_result(
                "Performance Basic",
                False,
                f"Performance test error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def run_all_tests(self) -> dict[str, Any]:
        """Uruchom wszystkie testy E2E."""
        print("🚀 Starting GAJA End-to-End Tests")
        print("=" * 80)
        print(f"Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Server URL: {self.server_url}")
        print(f"WebSocket URL: {self.ws_url}")
        print("=" * 80)

        # Lista testów do uruchomienia
        tests = [
            ("1. Server Availability", self.test_1_server_availability),
            ("2. WebSocket Voice Flow", self.test_2_websocket_flow),
            ("3. Plugin System", self.test_3_plugin_system),
            ("4. Memory System", self.test_4_memory_system),
            ("5. Multi-User Support", self.test_5_multi_user),
            ("6. Error Handling", self.test_6_error_handling),
            ("7. Performance Basic", self.test_7_performance_basic),
        ]

        print("Running tests...")
        print("-" * 80)

        # Uruchom testy
        for test_name, test_func in tests:
            try:
                await test_func()
            except Exception as e:
                self.log_test_result(
                    test_name, False, f"Test execution failed: {str(e)}"
                )

        # Podsumowanie
        print("=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)

        passed_tests = sum(
            1 for result in self.test_results.values() if result["passed"]
        )
        total_tests = len(self.test_results)

        for test_name, result in self.test_results.items():
            status_icon = "✅" if result["passed"] else "❌"
            duration_str = f"{result['duration']:.2f}s" if result["duration"] else "N/A"
            print(
                f"{status_icon} {test_name:<25} | {duration_str:<8} | {result['details']}"
            )

        print("-" * 80)
        total_duration = time.time() - self.start_time
        print(f"🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"📅 Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Rekomendacje
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! System is ready for production.")
            print("✨ Gaja is working correctly and can handle basic operations.")
        elif passed_tests >= total_tests * 0.8:  # 80% lub więcej
            print(
                f"\n⚠️  Most tests passed ({passed_tests}/{total_tests}). System is mostly functional."
            )
            print("🔧 Some issues detected - check failed tests for details.")
        else:
            print(
                f"\n❌ Many tests failed ({total_tests - passed_tests}/{total_tests}). System needs attention."
            )
            print("🚨 Critical issues detected - system not ready for production.")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests,
            "duration": total_duration,
            "results": self.test_results,
        }


async def main():
    """Główna funkcja testowa."""
    # Sprawdź czy serwer jest dostępny
    print("🔍 Checking server availability...")
    tester = GajaE2ETester()

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8001/health") as response:
                print(f"Health check response: {response.status}")
                if response.status != 200:
                    print("❌ Server is not running! Please start server first:")
                    print("   python manage.py start-server")
                    sys.exit(1)
                else:
                    print("✅ Server health check passed!")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please make sure server is running:")
        print("   python manage.py start-server")
        sys.exit(1)

    # Uruchom testy
    results = await tester.run_all_tests()

    # Kod wyjścia dla CI/CD
    if results["success_rate"] >= 0.8:  # 80% testów musi przejść
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    asyncio.run(main())

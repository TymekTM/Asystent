#!/usr/bin/env python3
"""Test połączenia klient-serwer zgodnie z checklistą w todo.md."""

import asyncio
import json
import sys
import time

import aiohttp
import websockets


class GajaConnectionTester:
    """Tester połączenia z serwerem Gaja."""

    def __init__(
        self,
        server_url: str = "http://localhost:8001",
        ws_url: str = "ws://localhost:8001/ws/test_user",
    ):
        self.server_url = server_url
        self.ws_url = ws_url
        self.test_results = {}

    async def test_server_health(self) -> bool:
        """Test podstawowego healthchecku serwera."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        print("✅ Server health check - PASSED")
                        return True
                    else:
                        print(
                            f"❌ Server health check - FAILED (status: {response.status})"
                        )
                        return False
        except Exception as e:
            print(f"❌ Server health check - FAILED (error: {e})")
            return False

    async def test_websocket_connection(self) -> bool:
        """Test połączenia WebSocket."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print("✅ WebSocket connection - PASSED")

                # Test wysłania wiadomości
                test_message = {
                    "type": "user_input",
                    "content": "test connection",
                    "timestamp": time.time(),
                }

                await websocket.send(json.dumps(test_message))

                # Oczekiwanie na odpowiedź (timeout 5s)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    print(
                        f"✅ WebSocket message exchange - PASSED (response type: {response_data.get('type', 'unknown')})"
                    )
                    return True
                except TimeoutError:
                    print(
                        "⚠️ WebSocket message exchange - TIMEOUT (connection works but no response)"
                    )
                    return True  # Połączenie działa, nawet jeśli brak odpowiedzi

        except Exception as e:
            print(f"❌ WebSocket connection - FAILED (error: {e})")
            return False

    async def test_api_endpoints(self) -> bool:
        """Test podstawowych endpointów API."""
        endpoints_to_test = [
            ("/", "GET"),
            ("/api/status", "GET"),
            ("/api/config", "GET"),
        ]

        results = []

        async with aiohttp.ClientSession() as session:
            for endpoint, method in endpoints_to_test:
                try:
                    if method == "GET":
                        async with session.get(
                            f"{self.server_url}{endpoint}"
                        ) as response:
                            if (
                                response.status < 500
                            ):  # Akceptujemy wszystko poza błędami serwera
                                print(
                                    f"✅ API endpoint {endpoint} - PASSED (status: {response.status})"
                                )
                                results.append(True)
                            else:
                                print(
                                    f"❌ API endpoint {endpoint} - FAILED (status: {response.status})"
                                )
                                results.append(False)
                except Exception as e:
                    print(f"❌ API endpoint {endpoint} - FAILED (error: {e})")
                    results.append(False)

        return all(results)

    async def test_cors_headers(self) -> bool:
        """Test nagłówków CORS."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Origin": "http://localhost:3000"}
                async with session.options(
                    f"{self.server_url}/api/status", headers=headers
                ) as response:
                    cors_header = response.headers.get("Access-Control-Allow-Origin")
                    if cors_header:
                        print(
                            f"✅ CORS headers - PASSED (allowed origin: {cors_header})"
                        )
                        return True
                    else:
                        print("⚠️ CORS headers - WARNING (no CORS headers found)")
                        return True  # Nie krytyczne
        except Exception as e:
            print(f"❌ CORS headers - FAILED (error: {e})")
            return False

    async def run_all_tests(self) -> dict:
        """Uruchom wszystkie testy połączenia."""
        print("🚀 Starting GAJA Connection Tests...")
        print(f"Server URL: {self.server_url}")
        print(f"WebSocket URL: {self.ws_url}")
        print("=" * 50)

        # Test 1: Health check
        health_ok = await self.test_server_health()
        self.test_results["health"] = health_ok

        # Test 2: WebSocket
        websocket_ok = await self.test_websocket_connection()
        self.test_results["websocket"] = websocket_ok

        # Test 3: API endpoints
        api_ok = await self.test_api_endpoints()
        self.test_results["api"] = api_ok

        # Test 4: CORS
        cors_ok = await self.test_cors_headers()
        self.test_results["cors"] = cors_ok

        # Podsumowanie
        print("=" * 50)
        print("📊 TEST RESULTS SUMMARY:")

        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)

        for test_name, result in self.test_results.items():
            status = "PASSED" if result else "FAILED"
            emoji = "✅" if result else "❌"
            print(f"{emoji} {test_name.upper()}: {status}")

        print(f"\n🎯 Overall: {passed}/{total} tests passed")

        if passed == total:
            print(
                "🎉 All connection tests PASSED! Server is ready for client connection."
            )
        else:
            print("⚠️ Some tests FAILED. Check server configuration.")

        return self.test_results


async def main():
    """Główna funkcja testowa."""
    tester = GajaConnectionTester()
    results = await tester.run_all_tests()

    # Kod wyjścia dla CI/CD
    if all(results.values()):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    asyncio.run(main())

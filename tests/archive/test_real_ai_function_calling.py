#!/usr/bin/env python3
"""TEST RZECZYWISTEGO FUNCTION CALLING Z OpenAI API GPT-4.1-nano Łączy się z
rzeczywistym serwerem Gaja i wykonuje prawdziwe zapytania AI."""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any

import aiohttp
import websockets

# Add project paths
sys.path.insert(0, ".")
sys.path.insert(0, "./server")

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv(".env")
    print("✅ Loaded environment variables from .env")
except ImportError:
    print("⚠️ python-dotenv not installed, using manual .env loading")
    # Manual fallback for .env loading
    env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
            print(f"✅ Manually loaded environment variables from {env_path}")
        except Exception as e:
            print(f"❌ Error loading .env file: {e}")


class RealAIFunctionTest:
    """Test rzeczywistego function calling przez serwer Gaja z OpenAI API."""

    def __init__(self):
        self.server_url = "http://localhost:8001"
        self.websocket_url = "ws://localhost:8001"
        self.user_id = "test_user_function_calling"
        self.test_results = []

    async def check_server_health(self) -> bool:
        """Sprawdź czy serwer jest dostępny."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Serwer jest dostępny: {data}")
                        return True
                    else:
                        print(f"❌ Serwer odpowiedział z kodem: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Nie można połączyć się z serwerem: {e}")
            return False

    async def check_api_key(self) -> bool:
        """Sprawdź konfigurację klucza API."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY nie jest ustawiony w zmiennych środowiskowych")
            return False

        if api_key.startswith("sk-") and len(api_key) > 20:
            print(
                f"✅ Klucz API OpenAI jest skonfigurowany: {api_key[:10]}...{api_key[-4:]}"
            )
            return True
        else:
            print(f"❌ Nieprawidłowy format klucza API: {api_key[:20]}...")
            return False

    async def test_rest_api_query(
        self, query: str, expected_functions: list[str] = None
    ) -> dict[str, Any]:
        """Test zapytania przez REST API."""
        try:
            payload = {
                "query": query,
                "user_id": self.user_id,
                "use_function_calling": True,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/api/v1/ai/query", json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "response": data,
                            "method": "REST",
                            "query": query,
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "method": "REST",
                            "query": query,
                        }
        except Exception as e:
            return {"success": False, "error": str(e), "method": "REST", "query": query}

    async def test_websocket_query(
        self, query: str, expected_functions: list[str] = None
    ) -> dict[str, Any]:
        """Test zapytania przez WebSocket."""
        try:
            uri = f"{self.websocket_url}/ws/{self.user_id}"

            async with websockets.connect(uri) as websocket:
                # Wyślij handshake
                handshake = {
                    "type": "handshake",
                    "user_id": self.user_id,
                    "timestamp": datetime.now().isoformat(),
                }
                await websocket.send(json.dumps(handshake))

                # Poczekaj na odpowiedź handshake
                response = await websocket.recv()
                print(f"📝 Handshake response: {response}")

                # Wyślij zapytanie AI
                message = {
                    "type": "ai_query",
                    "query": query,
                    "context": {"user_id": self.user_id, "use_function_calling": True},
                    "timestamp": datetime.now().isoformat(),
                }

                await websocket.send(json.dumps(message))

                # Odbierz odpowiedź
                response = await websocket.recv()
                response_data = json.loads(response)

                return {
                    "success": True,
                    "response": response_data,
                    "method": "WebSocket",
                    "query": query,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "WebSocket",
                "query": query,
            }

    async def run_test_scenario(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Uruchom pojedynczy scenariusz testowy."""
        print(f"\n{'='*80}")
        print(f"🧪 SCENARIUSZ: {scenario['name']}")
        print(f"{'='*80}")
        print(f"👤 Zapytanie: {scenario['query']}")
        print(
            f"🎯 Oczekiwane funkcje: {', '.join(scenario.get('expected_functions', []))}"
        )

        results = {
            "scenario": scenario["name"],
            "query": scenario["query"],
            "expected_functions": scenario.get("expected_functions", []),
            "tests": [],
            "timestamp": datetime.now().isoformat(),
        }

        # Test przez REST API
        print("\n🌐 Test przez REST API...")
        rest_result = await self.test_rest_api_query(
            scenario["query"], scenario.get("expected_functions")
        )
        results["tests"].append(rest_result)

        if rest_result["success"]:
            print("✅ REST API: Sukces")
            print(
                f"📄 Odpowiedź: {json.dumps(rest_result['response'], ensure_ascii=False, indent=2)[:200]}..."
            )
        else:
            print(f"❌ REST API: {rest_result['error']}")

        # Test przez WebSocket
        print("\n🔌 Test przez WebSocket...")
        ws_result = await self.test_websocket_query(
            scenario["query"], scenario.get("expected_functions")
        )
        results["tests"].append(ws_result)

        if ws_result["success"]:
            print("✅ WebSocket: Sukces")
            print(
                f"📄 Odpowiedź: {json.dumps(ws_result['response'], ensure_ascii=False, indent=2)[:200]}..."
            )
        else:
            print(f"❌ WebSocket: {ws_result['error']}")

        return results

    async def run_comprehensive_test(self):
        """Uruchom kompletny test function calling."""
        print("🔍 TEST RZECZYWISTEGO FUNCTION CALLING Z OpenAI GPT-4.1-nano")
        print("=" * 80)

        # Sprawdź przedwarunki
        print("\n📋 SPRAWDZANIE PRZEDWARUNKÓW:")

        # 1. Sprawdź klucz API
        if not await self.check_api_key():
            print("❌ Test przerwany - brak poprawnego klucza API")
            return

        # 2. Sprawdź dostępność serwera
        if not await self.check_server_health():
            print("❌ Test przerwany - serwer niedostępny")
            print("💡 Uruchom serwer: python server_main.py")
            return

        print("✅ Wszystkie przedwarunki spełnione\n")

        # Scenariusze testowe
        test_scenarios = [
            {
                "name": "Pogoda w Warszawie",
                "query": "Jaka jest pogoda w Warszawie?",
                "expected_functions": ["weather_module_get_weather"],
            },
            {
                "name": "Ustawienie timera i zadania",
                "query": "Ustaw timer na 5 minut i dodaj zadanie 'Sprawdzić maile'",
                "expected_functions": ["core_module_set_timer", "core_module_add_task"],
            },
            {
                "name": "Wyszukiwanie w internecie",
                "query": "Wyszukaj najnowsze informacje o sztucznej inteligencji",
                "expected_functions": ["search_module_search"],
            },
            {
                "name": "Kontrola muzyki",
                "query": "Zatrzymaj muzykę i sprawdź aktualny czas",
                "expected_functions": [
                    "music_module_control_music",
                    "core_module_get_current_time",
                ],
            },
            {
                "name": "Kalendarz i przypomnienia",
                "query": "Dodaj wydarzenie na jutro o 15:00 i ustaw przypomnienie",
                "expected_functions": [
                    "core_module_add_event",
                    "core_module_set_reminder",
                ],
            },
            {
                "name": "Prognoza pogody",
                "query": "Jaka będzie pogoda w Krakowie na następne 3 dni?",
                "expected_functions": ["weather_module_get_forecast"],
            },
            {
                "name": "Wiadomości",
                "query": "Pokaż najnowsze wiadomości o technologii",
                "expected_functions": ["search_module_search_news"],
            },
            {
                "name": "Status Spotify",
                "query": "Co teraz gra na Spotify?",
                "expected_functions": ["music_module_get_spotify_status"],
            },
            {
                "name": "Zarządzanie listą",
                "query": "Dodaj 'chleb' do listy zakupów i pokaż całą listę",
                "expected_functions": ["core_module_add_item", "core_module_view_list"],
            },
            {
                "name": "Zewnętrzne API",
                "query": "Wykonaj zapytanie GET do api.github.com/users/octocat",
                "expected_functions": ["api_module_make_api_request"],
            },
        ]

        # Uruchom wszystkie scenariusze
        all_results = []
        successful_tests = 0
        total_tests = 0

        for scenario in test_scenarios:
            result = await self.run_test_scenario(scenario)
            all_results.append(result)

            # Policz sukcesy
            for test in result["tests"]:
                total_tests += 1
                if test["success"]:
                    successful_tests += 1

            # Krótka przerwa między testami
            await asyncio.sleep(2)

        # Podsumowanie
        print(f"\n{'='*80}")
        print("📊 PODSUMOWANIE KOŃCOWE")
        print(f"{'='*80}")

        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"✅ Scenariuszy testowych: {len(test_scenarios)}")
        print(f"🔧 Łączna liczba testów: {total_tests}")
        print(f"✅ Udanych testów: {successful_tests}")
        print(f"❌ Nieudanych testów: {total_tests - successful_tests}")
        print(f"📈 Procent sukcesu: {success_rate:.1f}%")

        # Szczegółowy raport błędów
        failed_tests = []
        for result in all_results:
            for test in result["tests"]:
                if not test["success"]:
                    failed_tests.append(
                        {
                            "scenario": result["scenario"],
                            "method": test["method"],
                            "error": test["error"],
                        }
                    )

        if failed_tests:
            print("\n❌ SZCZEGÓŁY BŁĘDÓW:")
            for i, fail in enumerate(failed_tests, 1):
                print(f"{i}. {fail['scenario']} ({fail['method']}): {fail['error']}")

        # Zapisz wyniki
        results_file = "real_ai_function_calling_test_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "test_summary": {
                        "total_scenarios": len(test_scenarios),
                        "total_tests": total_tests,
                        "successful_tests": successful_tests,
                        "success_rate": success_rate,
                        "timestamp": datetime.now().isoformat(),
                    },
                    "scenarios": all_results,
                    "failed_tests": failed_tests,
                },
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        print(f"\n💾 Szczegółowe wyniki zapisane do: {results_file}")

        if success_rate >= 80:
            print(f"\n🎉 TEST ZAKOŃCZONY SUKCESEM! ({success_rate:.1f}% sukcesu)")
        else:
            print(f"\n⚠️ TEST CZĘŚCIOWO UDANY ({success_rate:.1f}% sukcesu)")

        return all_results


async def main():
    """Główna funkcja testowa."""
    tester = RealAIFunctionTest()

    try:
        await tester.run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n⚠️ Test przerwany przez użytkownika")
    except Exception as e:
        print(f"\n❌ Błąd podczas testu: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

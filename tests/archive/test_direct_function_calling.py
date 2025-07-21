#!/usr/bin/env python3
"""Test direct function calling sprawdzający czy funkcje są rzeczywiście wywoływane."""

import asyncio
import json
import sys
from datetime import datetime

import websockets

# Add project paths
sys.path.insert(0, ".")
sys.path.insert(0, "./server")

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv(".env")
    print("✅ Loaded environment variables from .env")
except:
    pass


class DirectFunctionCallTest:
    """Test bezpośredniego function calling."""

    def __init__(self):
        self.websocket_url = "ws://localhost:8001"
        self.user_id = "direct_test_user"

    async def test_direct_function_call(self, query: str) -> dict:
        """Test pojedynczego zapytania z logowaniem szczegółów."""
        try:
            uri = f"{self.websocket_url}/ws/{self.user_id}"

            async with websockets.connect(uri) as websocket:
                # Handshake
                handshake = {
                    "type": "handshake",
                    "user_id": self.user_id,
                    "timestamp": datetime.now().isoformat(),
                }
                await websocket.send(json.dumps(handshake))
                response = await websocket.recv()
                print(f"📝 Handshake: {response}")

                # Wyślij zapytanie
                message = {
                    "type": "ai_query",
                    "query": query,
                    "context": {
                        "user_id": self.user_id,
                        "use_function_calling": True,
                        "detailed_logging": True,
                    },
                    "timestamp": datetime.now().isoformat(),
                }

                print(f"\n🔍 Wysyłam zapytanie: {query}")
                await websocket.send(json.dumps(message))

                # Odbierz odpowiedź
                response = await websocket.recv()
                response_data = json.loads(response)

                print("📄 Otrzymana odpowiedź:")
                print(json.dumps(response_data, ensure_ascii=False, indent=2))

                # Analiza odpowiedzi
                if response_data.get("type") == "ai_response":
                    ai_response = response_data.get("data", {}).get("response", "")
                    try:
                        parsed_response = json.loads(ai_response)
                        function_calls_executed = parsed_response.get(
                            "function_calls_executed", False
                        )
                        text = parsed_response.get("text", "")

                        print("\n🔍 ANALIZA:")
                        print(f"   Text: {text[:100]}...")
                        print(f"   Function calls executed: {function_calls_executed}")

                        return {
                            "success": True,
                            "query": query,
                            "text": text,
                            "function_calls_executed": function_calls_executed,
                            "raw_response": response_data,
                        }
                    except json.JSONDecodeError:
                        return {
                            "success": True,
                            "query": query,
                            "text": ai_response,
                            "function_calls_executed": False,
                            "raw_response": response_data,
                        }

                return {
                    "success": False,
                    "error": "Invalid response format",
                    "raw_response": response_data,
                }

        except Exception as e:
            return {"success": False, "error": str(e), "query": query}


async def main():
    """Test główny."""
    print("🔍 TEST BEZPOŚREDNIEGO FUNCTION CALLING")
    print("=" * 60)

    tester = DirectFunctionCallTest()

    # Test scenariusze które POWINNY wywołać funkcje
    test_queries = [
        "Ustaw timer na 30 sekund",  # core_module_set_timer
        "Jaka jest pogoda w Londynie?",  # weather_module_get_weather
        "Dodaj zadanie 'Kupić mleko'",  # core_module_add_task
        "Pokaż aktualny czas",  # core_module_get_current_time
        "Wyszukaj informacje o Python",  # search_module_search
    ]

    results = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST {i}/{len(test_queries)}")
        print(f"{'='*60}")

        result = await tester.test_direct_function_call(query)
        results.append(result)

        # Krótka przerwa
        await asyncio.sleep(3)

    # Podsumowanie
    print(f"\n{'='*60}")
    print("📊 PODSUMOWANIE")
    print(f"{'='*60}")

    function_calls_count = sum(
        1 for r in results if r.get("function_calls_executed", False)
    )

    print(f"✅ Testów wykonanych: {len(results)}")
    print(f"🔧 Funkcji wykonanych: {function_calls_count}")
    print(f"📈 Procent function calling: {function_calls_count/len(results)*100:.1f}%")

    # Szczegóły
    print("\n📋 SZCZEGÓŁY:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("function_calls_executed", False) else "❌"
        query = result.get("query", "Unknown")
        print(f"{i}. {status} {query}")

    # Zapisz wyniki
    with open("direct_function_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print("\n💾 Szczegółowe wyniki: direct_function_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Test rzeczywistego użycia function calling przez AI.

Symuluje komunikację z OpenAI API z dostępnymi funkcjami.
"""

import asyncio
import json
import sys
from datetime import datetime

# Add project paths
sys.path.insert(0, ".")
sys.path.insert(0, "./server")


# Mock database manager
class MockDatabaseManager:
    def get_user_api_key(self, user_id, provider):
        return None

    def log_api_usage(self, *args, **kwargs):
        pass


import unittest.mock

sys.modules["database_manager"] = unittest.mock.MagicMock()
sys.modules["database_manager"].get_database_manager = lambda: MockDatabaseManager()

from server.modules import (
    api_module,
    core_module,
    music_module,
    open_web_module,
    search_module,
    weather_module,
)


class MockOpenAIResponse:
    """Mock OpenAI API response for testing."""

    def __init__(self, function_calls=None, text_response=None):
        self.function_calls = function_calls or []
        self.text_response = text_response or "Mock AI response"

    def to_dict(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": self.text_response,
                        "tool_calls": [
                            {
                                "id": f"call_{i}",
                                "type": "function",
                                "function": {
                                    "name": call["name"],
                                    "arguments": json.dumps(call["arguments"]),
                                },
                            }
                            for i, call in enumerate(self.function_calls)
                        ]
                        if self.function_calls
                        else None,
                    }
                }
            ]
        }


class AIFunctionCallingSimulator:
    """Symuluje pełny przepływ function calling z AI."""

    def __init__(self):
        self.modules = {
            "weather_module": weather_module,
            "search_module": search_module,
            "core_module": core_module,
            "music_module": music_module,
            "api_module": api_module,
            "open_web_module": open_web_module,
        }

    def get_openai_functions_schema(self):
        """Generuje schema funkcji w formacie OpenAI."""
        functions = []

        for module_name, module in self.modules.items():
            if hasattr(module, "get_functions"):
                module_functions = module.get_functions()
                for func in module_functions:
                    openai_func = {
                        "type": "function",
                        "function": {
                            "name": f"{module_name}_{func['name']}",
                            "description": func["description"],
                            "parameters": func["parameters"],
                        },
                    }
                    functions.append(openai_func)

        return functions

    async def execute_function_call(self, function_name, arguments, user_id=1):
        """Wykonuje wywołanie funkcji z AI."""
        # Parse module name and function name
        # Format: weather_module_get_weather -> weather_module, get_weather
        parts = function_name.split("_")
        if len(parts) < 3:
            return {"error": f"Invalid function name format: {function_name}"}

        # Find module name (ends with '_module')
        module_name = None
        func_name_parts = []

        for i, part in enumerate(parts):
            if part == "module" and i > 0:
                module_name = "_".join(parts[: i + 1])
                func_name_parts = parts[i + 1 :]
                break

        if not module_name or not func_name_parts:
            return {"error": f"Cannot parse function name: {function_name}"}

        func_name = "_".join(func_name_parts)

        if module_name not in self.modules:
            return {"error": f"Module {module_name} not found"}

        module = self.modules[module_name]

        if not hasattr(module, "execute_function"):
            return {
                "error": f"Module {module_name} does not support function execution"
            }

        try:
            result = await module.execute_function(func_name, arguments, user_id)
            return result
        except Exception as e:
            return {"error": str(e), "exception_type": type(e).__name__}

    async def simulate_ai_conversation(self, user_query, mock_ai_response):
        """Symuluje pełną konwersację z AI używając function calling."""
        print(f"👤 Użytkownik: {user_query}")
        print(f"🤖 AI zamierza: {mock_ai_response.text_response}")

        if not mock_ai_response.function_calls:
            print("📝 AI nie wywołuje żadnych funkcji")
            return mock_ai_response.text_response

        print(f"🔧 AI wywołuje {len(mock_ai_response.function_calls)} funkcji:")

        function_results = []

        for i, func_call in enumerate(mock_ai_response.function_calls, 1):
            print(f"\n🎯 Funkcja {i}: {func_call['name']}")
            print(
                f"📋 Argumenty: {json.dumps(func_call['arguments'], ensure_ascii=False, indent=2)}"
            )

            result = await self.execute_function_call(
                func_call["name"], func_call["arguments"]
            )

            function_results.append(result)

            if result.get("success", False):
                print(f"✅ Sukces: {result.get('message', 'Brak wiadomości')}")
            else:
                print(f"❌ Błąd: {result.get('error', 'Nieznany błąd')}")

        print(f"\n💬 AI finalnie odpowiada: {mock_ai_response.text_response}")
        return {
            "ai_response": mock_ai_response.text_response,
            "function_results": function_results,
        }


async def main():
    """Główna funkcja testowa."""
    simulator = AIFunctionCallingSimulator()

    print("🧪 TEST RZECZYWISTEGO FUNCTION CALLING Z AI")
    print("=" * 60)

    # Pokaż dostępne funkcje
    functions_schema = simulator.get_openai_functions_schema()
    print(f"\n📦 Dostępnych funkcji dla AI: {len(functions_schema)}")

    for func in functions_schema[:5]:  # Pokaż pierwsze 5
        name = func["function"]["name"]
        desc = func["function"]["description"]
        print(f"  • {name}: {desc}")
    print(f"  ... i {len(functions_schema) - 5} więcej")

    # Scenariusze testowe
    test_scenarios = [
        {
            "user_query": "Jaka jest pogoda w Warszawie?",
            "ai_response": MockOpenAIResponse(
                function_calls=[
                    {
                        "name": "weather_module_get_weather",
                        "arguments": {"location": "Warsaw", "test_mode": True},
                    }
                ],
                text_response="Sprawdzam pogodę w Warszawie...",
            ),
        },
        {
            "user_query": "Ustaw timer na 10 minut i dodaj zadanie do wykonania",
            "ai_response": MockOpenAIResponse(
                function_calls=[
                    {
                        "name": "core_module_set_timer",
                        "arguments": {"duration": "10m", "label": "Timer użytkownika"},
                    },
                    {
                        "name": "core_module_add_task",
                        "arguments": {
                            "task": "Wykonaj zaplanowane zadanie",
                            "priority": "medium",
                        },
                    },
                ],
                text_response="Ustawiłem timer na 10 minut i dodałem zadanie do listy.",
            ),
        },
        {
            "user_query": "Wyszukaj informacje o AI i otwórz stronę OpenAI",
            "ai_response": MockOpenAIResponse(
                function_calls=[
                    {
                        "name": "search_module_search",
                        "arguments": {
                            "query": "artificial intelligence",
                            "test_mode": True,
                        },
                    },
                    {
                        "name": "open_web_module_open_web",
                        "arguments": {"url": "https://openai.com", "test_mode": True},
                    },
                ],
                text_response="Wyszukałem informacje o AI i otworzyłem stronę OpenAI.",
            ),
        },
        {
            "user_query": "Zatrzymaj muzykę i sprawdź aktualny czas",
            "ai_response": MockOpenAIResponse(
                function_calls=[
                    {
                        "name": "music_module_control_music",
                        "arguments": {"action": "pause", "test_mode": True},
                    },
                    {"name": "core_module_get_current_time", "arguments": {}},
                ],
                text_response="Zatrzymałem muzykę i sprawdziłem aktualny czas.",
            ),
        },
        {
            "user_query": "Dodaj wydarzenie do kalendarza na jutro",
            "ai_response": MockOpenAIResponse(
                function_calls=[
                    {
                        "name": "core_module_add_event",
                        "arguments": {
                            "title": "Spotkanie zaplanowane przez AI",
                            "date": "2025-07-21",
                            "time": "10:00",
                        },
                    }
                ],
                text_response="Dodałem wydarzenie do kalendarza na jutro o 10:00.",
            ),
        },
    ]

    # Uruchom scenariusze
    all_results = []

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*60}")
        print(f"📋 SCENARIUSZ {i}/{len(test_scenarios)}")
        print(f"{'='*60}")

        result = await simulator.simulate_ai_conversation(
            scenario["user_query"], scenario["ai_response"]
        )

        all_results.append(
            {
                "scenario": i,
                "user_query": scenario["user_query"],
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

    # Podsumowanie
    print(f"\n{'='*60}")
    print("📊 PODSUMOWANIE KOŃCOWE")
    print(f"{'='*60}")

    total_function_calls = sum(
        len(result["result"]["function_results"])
        for result in all_results
        if isinstance(result["result"], dict)
    )

    successful_calls = sum(
        sum(
            1
            for func_result in result["result"]["function_results"]
            if func_result.get("success", False)
        )
        for result in all_results
        if isinstance(result["result"], dict)
    )

    print(f"✅ Scenariuszy przetestowanych: {len(test_scenarios)}")
    print(f"🔧 Łączna liczba wywołań funkcji: {total_function_calls}")
    print(f"✅ Udanych wywołań: {successful_calls}")
    print(f"❌ Nieudanych wywołań: {total_function_calls - successful_calls}")
    print(f"📈 Procent sukcesu: {successful_calls/total_function_calls*100:.1f}%")

    # Zapisz wyniki
    with open("ai_conversation_test_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    print("\n💾 Szczegółowe wyniki zapisane do: ai_conversation_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Test script to verify AI function calling with all available plugins.

This simulates how the AI would use the available functions.
"""

import asyncio
import json
import sys

# Add project paths
sys.path.insert(0, ".")
sys.path.insert(0, "./server")


# Mock database manager to avoid dependencies
class MockDatabaseManager:
    def get_user_api_key(self, user_id, provider):
        return None

    def log_api_usage(self, *args, **kwargs):
        pass


# Install mock
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


class AIFunctionTester:
    """Simulates AI function calling behavior."""

    def __init__(self):
        self.modules = {
            "weather": weather_module,
            "search": search_module,
            "core": core_module,
            "music": music_module,
            "api": api_module,
            "web": open_web_module,
        }

    def get_all_functions(self):
        """Get all available functions from all modules."""
        all_functions = {}
        for module_name, module in self.modules.items():
            if hasattr(module, "get_functions"):
                functions = module.get_functions()
                for func in functions:
                    func_key = f"{module_name}.{func['name']}"
                    all_functions[func_key] = {"module": module, "definition": func}
        return all_functions

    async def test_function(self, function_key, test_params, user_id=1):
        """Test a specific function with given parameters."""
        all_functions = self.get_all_functions()

        if function_key not in all_functions:
            return {"error": f"Function {function_key} not found"}

        func_info = all_functions[function_key]
        module = func_info["module"]
        func_name = func_info["definition"]["name"]

        try:
            result = await module.execute_function(func_name, test_params, user_id)
            return result
        except Exception as e:
            return {"error": str(e), "exception_type": type(e).__name__}

    async def run_comprehensive_test(self):
        """Run comprehensive tests simulating AI usage."""
        print("🤖 SYMULACJA UŻYCIA FUNKCJI PRZEZ AI")
        print("=" * 50)

        # Test scenarios simulating real AI requests
        test_scenarios = [
            {
                "description": "AI sprawdza pogodę dla Warszawy",
                "function": "weather.get_weather",
                "params": {"location": "Warsaw", "test_mode": True},
            },
            {
                "description": "AI ustawia timer na 5 minut",
                "function": "core.set_timer",
                "params": {"duration": "5m", "label": "Test Timer"},
            },
            {
                "description": "AI dodaje zadanie do listy",
                "function": "core.add_task",
                "params": {"task": "Sprawdź dokumentację AI", "priority": "high"},
            },
            {
                "description": "AI kontroluje muzykę - play",
                "function": "music.control_music",
                "params": {"action": "play", "test_mode": True},
            },
            {
                "description": "AI otwiera stronę internetową",
                "function": "web.open_web",
                "params": {"url": "https://example.com", "test_mode": True},
            },
            {
                "description": "AI wyszukuje informacje",
                "function": "search.search",
                "params": {"query": "Python programming", "test_mode": True},
            },
            {
                "description": "AI dodaje wydarzenie do kalendarza",
                "function": "core.add_event",
                "params": {
                    "title": "Meeting z AI",
                    "date": "2024-01-15",
                    "time": "14:00",
                },
            },
            {
                "description": "AI sprawdza prognozę pogody",
                "function": "weather.get_forecast",
                "params": {"location": "Krakow", "days": 3, "test_mode": True},
            },
            {
                "description": "AI wyszukuje najnowsze wiadomości",
                "function": "search.search_news",
                "params": {"query": "artificial intelligence", "test_mode": True},
            },
            {
                "description": "AI sprawdza aktualny czas",
                "function": "core.get_current_time",
                "params": {},
            },
        ]

        results = {}
        success_count = 0
        total_count = len(test_scenarios)

        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🧪 Test {i}/{total_count}: {scenario['description']}")
            print(f"📋 Funkcja: {scenario['function']}")
            print(
                f"📝 Parametry: {json.dumps(scenario['params'], ensure_ascii=False, indent=2)}"
            )

            result = await self.test_function(scenario["function"], scenario["params"])

            results[scenario["function"]] = result

            if result.get("success", False):
                print("✅ SUKCES")
                success_count += 1
                if "message" in result:
                    print(f"💬 Odpowiedź: {result['message']}")
            else:
                print("❌ BŁĄD")
                if "error" in result:
                    print(f"🚨 Błąd: {result['error']}")
                if "message" in result:
                    print(f"💬 Wiadomość: {result['message']}")

            print("-" * 40)

        # Summary
        print("\n📊 PODSUMOWANIE TESTÓW")
        print(f"✅ Udane: {success_count}/{total_count}")
        print(f"❌ Nieudane: {total_count - success_count}/{total_count}")
        print(f"📈 Procent sukcesu: {success_count/total_count*100:.1f}%")

        return results

    def display_available_functions(self):
        """Display all available functions for AI."""
        print("\n📦 WSZYSTKIE DOSTĘPNE FUNKCJE DLA AI:")
        print("=" * 50)

        all_functions = self.get_all_functions()

        for func_key, func_info in all_functions.items():
            definition = func_info["definition"]
            print(f"\n🔧 {func_key}")
            print(f"📄 Opis: {definition['description']}")

            # Show required parameters
            params = definition.get("parameters", {}).get("properties", {})
            required = definition.get("parameters", {}).get("required", [])

            if params:
                print("📋 Parametry:")
                for param_name, param_info in params.items():
                    required_mark = " (wymagany)" if param_name in required else ""
                    print(
                        f"  • {param_name}: {param_info.get('description', 'Brak opisu')}{required_mark}"
                    )
            else:
                print("📋 Parametry: Brak")


async def main():
    """Main test function."""
    tester = AIFunctionTester()

    # Display available functions
    tester.display_available_functions()

    # Run comprehensive tests
    results = await tester.run_comprehensive_test()

    # Save results to file
    with open("ai_function_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print("\n💾 Wyniki zapisane do: ai_function_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())

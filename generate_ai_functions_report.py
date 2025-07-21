#!/usr/bin/env python3
"""
FINALNE PODSUMOWANIE - Pluginy dostępne dla AI poprzez Function Calling
Wykonuje kompletną analizę wszystkich dostępnych funkcji dla AI.
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
    memory_module,
    music_module,
    onboarding_plugin_module,
    open_web_module,
    plugin_monitor_module,
    search_module,
    weather_module,
)


def analyze_function_schema(func_schema):
    """Analizuje szczegóły schema funkcji."""
    params = func_schema.get("parameters", {})
    properties = params.get("properties", {})
    required = params.get("required", [])

    param_count = len(properties)
    required_count = len(required)
    optional_count = param_count - required_count

    return {
        "parameter_count": param_count,
        "required_parameters": required_count,
        "optional_parameters": optional_count,
        "parameters": list(properties.keys()),
        "required_params": required,
        "optional_params": [p for p in properties.keys() if p not in required],
    }


async def main():
    print("🔍 FINALNE PODSUMOWANIE - PLUGINY DOSTĘPNE DLA AI")
    print("=" * 80)

    modules = {
        "weather_module": weather_module,
        "search_module": search_module,
        "core_module": core_module,
        "music_module": music_module,
        "api_module": api_module,
        "open_web_module": open_web_module,
        "memory_module": memory_module,
        "plugin_monitor_module": plugin_monitor_module,
        "onboarding_plugin_module": onboarding_plugin_module,
    }

    total_functions = 0
    module_details = {}
    all_functions = []

    for module_name, module in modules.items():
        if hasattr(module, "get_functions"):
            try:
                functions = module.get_functions()
                function_count = len(functions)
                total_functions += function_count

                # Analizuj każdą funkcję
                function_details = []
                for func in functions:
                    analysis = analyze_function_schema(func)
                    function_details.append(
                        {
                            "name": func["name"],
                            "description": func["description"],
                            "analysis": analysis,
                        }
                    )

                    all_functions.append(
                        {
                            "module": module_name,
                            "name": func["name"],
                            "description": func["description"],
                            "full_name": f"{module_name}_{func['name']}",
                            **analysis,
                        }
                    )

                module_details[module_name] = {
                    "function_count": function_count,
                    "functions": function_details,
                    "status": "active",
                }

            except Exception as e:
                module_details[module_name] = {
                    "function_count": 0,
                    "functions": [],
                    "status": f"error: {str(e)}",
                }
        else:
            module_details[module_name] = {
                "function_count": 0,
                "functions": [],
                "status": "no get_functions method",
            }

    # Wyświetl szczegółowy raport
    print("📊 STATYSTYKI OGÓLNE:")
    print(f"   • Łączna liczba modułów: {len(modules)}")
    print(
        f"   • Aktywne moduły: {sum(1 for m in module_details.values() if m['status'] == 'active')}"
    )
    print(f"   • Łączna liczba funkcji: {total_functions}")
    print()

    print("📋 SZCZEGÓŁOWY PRZEGLĄD MODUŁÓW:")
    print("-" * 80)

    for module_name, details in module_details.items():
        status_icon = "✅" if details["status"] == "active" else "❌"
        print(f"\n{status_icon} {module_name.upper()}")
        print(f"   Status: {details['status']}")
        print(f"   Funkcji: {details['function_count']}")

        if details["functions"]:
            print("   Dostępne funkcje:")
            for func in details["functions"]:
                name = func["name"]
                desc = (
                    func["description"][:60] + "..."
                    if len(func["description"]) > 60
                    else func["description"]
                )
                params = func["analysis"]["parameter_count"]
                required = func["analysis"]["required_parameters"]
                print(f"     • {name} ({params} parametrów, {required} wymaganych)")
                print(f"       {desc}")

    # Kategorie funkcji
    print("\n🗂️  KATEGORYZACJA FUNKCJI:")
    print("-" * 80)

    categories = {
        "Pogoda": [f for f in all_functions if "weather" in f["module"]],
        "Wyszukiwanie": [f for f in all_functions if "search" in f["module"]],
        "Zarządzanie czasem": [
            f
            for f in all_functions
            if "timer" in f["name"] or "event" in f["name"] or "time" in f["name"]
        ],
        "Zadania i listy": [
            f for f in all_functions if "task" in f["name"] or "list" in f["name"]
        ],
        "Muzyka": [f for f in all_functions if "music" in f["module"]],
        "Internet i API": [
            f for f in all_functions if "web" in f["module"] or "api" in f["module"]
        ],
        "Pamięć i dane": [f for f in all_functions if "memory" in f["module"]],
        "System i monitoring": [
            f
            for f in all_functions
            if "monitor" in f["module"] or "onboarding" in f["module"]
        ],
        "Inne": [
            f
            for f in all_functions
            if not any(
                keyword in f["module"].lower() or keyword in f["name"].lower()
                for keyword in [
                    "weather",
                    "search",
                    "timer",
                    "event",
                    "time",
                    "task",
                    "list",
                    "music",
                    "web",
                    "api",
                    "memory",
                    "monitor",
                    "onboarding",
                ]
            )
        ],
    }

    for category, funcs in categories.items():
        if funcs:
            print(f"\n📂 {category} ({len(funcs)} funkcji):")
            for func in funcs:
                print(f"   • {func['full_name']}: {func['description'][:50]}...")

    # Analiza parametrów
    print("\n📈 ANALIZA PARAMETRÓW:")
    print("-" * 80)

    param_stats = {
        "no_params": len([f for f in all_functions if f["parameter_count"] == 0]),
        "simple": len([f for f in all_functions if 1 <= f["parameter_count"] <= 3]),
        "medium": len([f for f in all_functions if 4 <= f["parameter_count"] <= 6]),
        "complex": len([f for f in all_functions if f["parameter_count"] > 6]),
    }

    print(f"Funkcje bez parametrów: {param_stats['no_params']}")
    print(f"Funkcje proste (1-3 parametry): {param_stats['simple']}")
    print(f"Funkcje średnie (4-6 parametrów): {param_stats['medium']}")
    print(f"Funkcje złożone (7+ parametrów): {param_stats['complex']}")

    # Lista wszystkich funkcji dostępnych dla AI
    print("\n🤖 KOMPLETNA LISTA FUNKCJI DOSTĘPNYCH DLA AI:")
    print("-" * 80)

    for i, func in enumerate(all_functions, 1):
        print(f"{i:2d}. {func['full_name']}")
        print(f"    📝 {func['description']}")
        print(
            f"    ⚙️  Parametry: {func['parameter_count']} ({func['required_parameters']} wymaganych)"
        )
        if func["required_params"]:
            print(f"    ✅ Wymagane: {', '.join(func['required_params'])}")
        if func["optional_params"]:
            print(f"    🔹 Opcjonalne: {', '.join(func['optional_params'])}")
        print()

    # Zapisz szczegółowy raport
    report = {
        "summary": {
            "total_modules": len(modules),
            "active_modules": sum(
                1 for m in module_details.values() if m["status"] == "active"
            ),
            "total_functions": total_functions,
            "generated_at": datetime.now().isoformat(),
        },
        "modules": module_details,
        "functions": all_functions,
        "categories": {
            cat: [f["full_name"] for f in funcs]
            for cat, funcs in categories.items()
            if funcs
        },
        "parameter_statistics": param_stats,
    }

    with open("ai_functions_complete_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print("💾 SZCZEGÓŁOWY RAPORT ZAPISANY DO: ai_functions_complete_report.json")
    print(
        f"📄 Raport zawiera pełną dokumentację {total_functions} funkcji dostępnych dla AI"
    )


if __name__ == "__main__":
    asyncio.run(main())

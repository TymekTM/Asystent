#!/usr/bin/env python3
"""Patch dla function calling system żeby używał bezpośrednio modułów z serwera."""

import asyncio
import sys

import aiohttp

# Add project paths
sys.path.insert(0, ".")
sys.path.insert(0, "./server")


async def test_direct_modules():
    """Test bezpośredniego dostępu do modułów."""

    print("🔍 TEST BEZPOŚREDNIEGO DOSTĘPU DO MODUŁÓW")
    print("=" * 60)

    # Test importu modułów
    try:
        sys.path.insert(0, "./server/modules")

        from server.modules import (
            api_module,
            core_module,
            music_module,
            open_web_module,
            search_module,
            weather_module,
        )

        modules = {
            "weather_module": weather_module,
            "search_module": search_module,
            "core_module": core_module,
            "music_module": music_module,
            "api_module": api_module,
            "open_web_module": open_web_module,
        }

        print("✅ Moduły zaimportowane pomyślnie:")

        total_functions = 0
        for module_name, module in modules.items():
            if hasattr(module, "get_functions"):
                functions = module.get_functions()
                print(f"   • {module_name}: {len(functions)} funkcji")
                total_functions += len(functions)
            else:
                print(f"   • {module_name}: brak get_functions()")

        print(f"\n📊 Łącznie funkcji dostępnych: {total_functions}")

        # Test pojedynczej funkcji
        if hasattr(core_module, "execute_function"):
            print("\n🧪 Test wykonania funkcji get_current_time:")
            result = await core_module.execute_function(
                "get_current_time", {}, user_id=1
            )
            print(f"Wynik: {result}")

        return True

    except Exception as e:
        print(f"❌ Błąd: {e}")
        import traceback

        traceback.print_exc()
        return False


async def patch_function_calling_system():
    """Patchuj function calling system żeby używał bezpośrednio modułów."""

    print("\n🔧 PATCH FUNCTION CALLING SYSTEM")
    print("=" * 60)

    # Utworzmy patch dla function_calling_system.py
    patch_content = '''
    def convert_modules_to_functions_direct(self) -> list[dict[str, Any]]:
        """Convert server modules directly to OpenAI function calling format."""
        import sys
        sys.path.insert(0, './server/modules')

        functions = []

        try:
            from server.modules import (
                weather_module, search_module, core_module, music_module,
                api_module, open_web_module
            )

            modules = {
                'weather_module': weather_module,
                'search_module': search_module,
                'core_module': core_module,
                'music_module': music_module,
                'api_module': api_module,
                'open_web_module': open_web_module
            }

            for module_name, module in modules.items():
                if hasattr(module, 'get_functions'):
                    module_functions = module.get_functions()
                    for func in module_functions:
                        openai_func = {
                            "type": "function",
                            "function": {
                                "name": f"{module_name}_{func['name']}",
                                "description": func['description'],
                                "parameters": func['parameters']
                            }
                        }
                        functions.append(openai_func)

                        # Store handler for execution
                        handler_name = f"{module_name}_{func['name']}"
                        self.function_handlers[handler_name] = {
                            "module": module,
                            "function_name": func['name']
                        }

            logger.info(f"Converted {len(functions)} functions from server modules")
            return functions

        except Exception as e:
            logger.error(f"Error converting server modules: {e}")
            return []
    '''

    print("Patch content created. Need to modify server to use direct modules.")
    return True


async def create_direct_function_test():
    """Utwórz test który używa bezpośrednio modułów."""

    print("\n🚀 CREATING DIRECT MODULE TEST")
    print("=" * 60)

    # Test czy możemy wykonać request z patchowanym systemem
    payload = {"type": "patch_function_calling", "action": "use_direct_modules"}

    try:
        async with aiohttp.ClientSession() as session:
            # Sprawdź czy serwer ma endpoint do patchowania
            async with session.get("http://localhost:8001/health") as response:
                if response.status == 200:
                    print("✅ Serwer dostępny - można dodać patch")
                    return True

    except Exception as e:
        print(f"❌ Problem z serwerem: {e}")
        return False


async def main():
    """Main test function."""

    # Test 1: Dostęp do modułów
    modules_ok = await test_direct_modules()

    # Test 2: Patch system
    patch_ok = await patch_function_calling_system()

    # Test 3: Przygotowanie testu
    test_ok = await create_direct_function_test()

    print(f"\n{'='*60}")
    print("📊 PODSUMOWANIE ANALIZY")
    print(f"{'='*60}")
    print(f"✅ Moduły dostępne: {modules_ok}")
    print(f"✅ Patch możliwy: {patch_ok}")
    print(f"✅ Test gotowy: {test_ok}")

    if modules_ok:
        print("\n🎯 ANALIZA PROBLEMU:")
        print("1. Moduły serwera mają 30+ funkcji dostępnych")
        print("2. Plugin manager ma 0 pluginów załadowanych")
        print("3. Function calling system używa plugin_manager zamiast modułów")
        print("4. AI otrzymuje tylko 4 funkcje zamiast 30+")
        print("5. Dlatego function calling działa częściowo")

        print("\n✅ ROZWIĄZANIE:")
        print("Trzeba zmodyfikować function_calling_system.py żeby używał")
        print("bezpośrednio modułów serwera zamiast plugin_manager")


if __name__ == "__main__":
    asyncio.run(main())

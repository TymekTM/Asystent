#!/usr/bin/env python3
"""Test dla nowej funkcji ask_for_clarification."""

import asyncio
import json
import sys
from pathlib import Path

# Add server path to imports
sys.path.insert(0, str(Path(__file__).parent / "server"))


async def test_clarification_function():
    """Test funkcji ask_for_clarification."""

    print("🧪 Testing ask_for_clarification function...")

    try:
        # Import modułu core
        from server.modules.core_module import ask_for_clarification

        # Test 1: Basic clarification request
        print("\n📝 Test 1: Basic clarification request")
        params = {
            "question": "Jakiej pogody potrzebujesz - dla jakiego miasta?",
            "context": "Użytkownik zapytał o pogodę, ale nie podał lokalizacji.",
        }

        result = await ask_for_clarification(params)
        print(f"✅ Result: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # Test 2: Without context
        print("\n📝 Test 2: Without context")
        params = {"question": "Jakiej muzyki chcesz posłuchać?"}

        result = await ask_for_clarification(params)
        print(f"✅ Result: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # Test 3: Invalid parameters
        print("\n📝 Test 3: Invalid parameters (missing question)")
        params = {"context": "Some context"}

        result = await ask_for_clarification(params)
        print(f"❌ Result: {json.dumps(result, indent=2, ensure_ascii=False)}")

        print("\n🎉 All tests completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


async def test_function_calling_integration():
    """Test integracji z systemem function calling."""

    print("\n🔧 Testing function calling integration...")

    try:
        from server.function_calling_system import FunctionCallingSystem

        # Initialize function calling system
        system = FunctionCallingSystem()

        # Get functions to see if ask_for_clarification is included
        functions = system.convert_modules_to_functions()

        # Find clarification function
        clarification_functions = [
            f
            for f in functions
            if f["function"]["name"].endswith("ask_for_clarification")
        ]

        if clarification_functions:
            func = clarification_functions[0]
            print(f"✅ Found ask_for_clarification function:")
            print(f"   Name: {func['function']['name']}")
            print(f"   Description: {func['function']['description']}")
            print(
                f"   Parameters: {json.dumps(func['function']['parameters'], indent=2)}"
            )

            # Test execution through function calling system
            print("\n🔧 Testing execution through function calling system...")
            result = await system.execute_function(
                func["function"]["name"],
                {"question": "Test clarification question?", "context": "Test context"},
            )
            print(
                f"✅ Execution result: {json.dumps(result, indent=2, ensure_ascii=False)}"
            )

        else:
            print(
                "❌ ask_for_clarification function not found in function calling system"
            )
            print(f"Available functions: {[f['function']['name'] for f in functions]}")

    except Exception as e:
        print(f"❌ Error during function calling integration test: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Main test function."""
    print("🚀 Testing ask_for_clarification functionality")
    print("=" * 60)

    await test_clarification_function()
    await test_function_calling_integration()

    print("\n" + "=" * 60)
    print("✅ Testing completed!")


if __name__ == "__main__":
    asyncio.run(main())

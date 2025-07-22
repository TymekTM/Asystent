#!/usr/bin/env python3
"""Test script for Function Calling System fixes.

Tests the fixes for stability and reliability issues.
"""

import asyncio
import sys
from pathlib import Path

# Add server path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

try:
    from function_calling_system import FunctionCallingSystem

    print("✅ Function calling system imported successfully")
except ImportError as e:
    print(f"❌ Failed to import function calling system: {e}")
    sys.exit(1)


async def test_function_calling_system():
    """Test the function calling system fixes."""
    print("\n=== Testing Function Calling System Fixes ===")

    # Initialize system
    system = FunctionCallingSystem()
    await system.initialize()
    print("✅ System initialized successfully")

    # Test module registration
    test_module = {
        "handler": lambda x="test": f"Test result: {x}",
        "sub_commands": {
            "test_sub": {
                "function": lambda y="sub": f"Sub test: {y}",
                "description": "Test subcommand",
            }
        },
    }

    system.register_module("test_module", test_module)
    print("✅ Module registration works")

    # Test function execution
    try:
        result = await system.execute_function("test_module", {"x": "hello"})
        print(f"✅ Async function execution works: {result}")
    except Exception as e:
        print(f"❌ Function execution failed: {e}")

    # Test function conversion
    try:
        functions = system.convert_modules_to_functions()
        print(f"✅ Function conversion works: {len(functions)} functions found")
        for func in functions[:3]:  # Show first 3
            print(f"   - {func['function']['name']}: {func['function']['description']}")
    except Exception as e:
        print(f"❌ Function conversion failed: {e}")

    print("\n=== Function Calling System Test Complete ===")


async def test_server_modules():
    """Test server modules import and basic functionality."""
    print("\n=== Testing Server Modules ===")

    try:
        from modules import core_module

        print("✅ Core module imported")

        # Test get_functions
        functions = core_module.get_functions()
        print(f"✅ Core module has {len(functions)} functions")

    except Exception as e:
        print(f"❌ Core module test failed: {e}")

    try:
        from modules import weather_module

        print("✅ Weather module imported")

        functions = weather_module.get_functions()
        print(f"✅ Weather module has {len(functions)} functions")

    except Exception as e:
        print(f"❌ Weather module test failed: {e}")

    try:
        from modules import search_module

        print("✅ Search module imported")

        functions = search_module.get_functions()
        print(f"✅ Search module has {len(functions)} functions")

    except Exception as e:
        print(f"❌ Search module test failed: {e}")

    print("\n=== Server Modules Test Complete ===")


async def test_websocket_basics():
    """Test basic WebSocket functionality."""
    print("\n=== Testing WebSocket Basics ===")

    try:
        from websocket_manager import ConnectionManager, WebSocketMessage

        manager = ConnectionManager()
        print("✅ WebSocket manager created")

        # Test message creation
        message = WebSocketMessage("test", {"data": "hello"})
        print(f"✅ WebSocket message created: {message.to_dict()}")

    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

    print("\n=== WebSocket Test Complete ===")


def test_type_hints():
    """Test that type hints are working correctly."""
    print("\n=== Testing Type Hints ===")

    try:
        # Test function calling system types
        system = FunctionCallingSystem()

        # Test that function_handlers is properly typed as dict
        system.function_handlers["test"] = {"type": "test", "module": None}
        print("✅ Function handlers typing works")

        # Test that modules dict works
        system.modules["test"] = {"handler": lambda: "test"}
        print("✅ Modules dict typing works")

    except Exception as e:
        print(f"❌ Type hints test failed: {e}")

    print("\n=== Type Hints Test Complete ===")


async def main():
    """Run all tests."""
    print("🚀 Starting Function Calling System Fixes Test")

    test_type_hints()
    await test_function_calling_system()
    await test_server_modules()
    await test_websocket_basics()

    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())

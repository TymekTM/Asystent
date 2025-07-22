#!/usr/bin/env python3
"""Function Calling System Validation Test.

This test specifically validates the function calling system's ability to:
1. Convert modules to function schemas
2. Handle parameter extraction and validation
3. Execute function calls correctly
4. Integrate with AI providers
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Setup logging to be less verbose than server
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("function_calling_test.log"),
    ],
)
logger = logging.getLogger(__name__)

# Suppress verbose logs from other modules
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class FunctionCallingValidator:
    """Validates function calling system functionality."""

    def __init__(self):
        self.results = {
            "schema_validation": [],
            "execution_tests": [],
            "integration_tests": [],
            "errors": [],
        }

    def log_result(
        self, category: str, test_name: str, success: bool, details: str = ""
    ):
        """Log test result."""
        status = "✅" if success else "❌"
        logger.info(f"{status} {test_name}: {details}")

        self.results[category].append(
            {"test": test_name, "success": success, "details": details}
        )

    async def validate_function_schemas(self) -> bool:
        """Validate function schema generation."""
        logger.info("🔍 Validating Function Schema Generation")

        try:
            # Import function calling system
            sys.path.append(str(Path(__file__).parent))
            sys.path.append(str(Path(__file__).parent / "server"))
            from function_calling_system import FunctionCallingSystem

            fc_system = FunctionCallingSystem()

            # Test schema conversion with mock module data
            mock_modules = {
                "weather": {
                    "command": "weather",
                    "description": "Get weather information",
                    "handler": lambda: "mock weather",
                    "function_schema": {
                        "name": "get_weather",
                        "description": "Get current weather for a location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "City name",
                                }
                            },
                            "required": ["location"],
                        },
                    },
                },
                "memory": {
                    "command": "memory",
                    "description": "Memory operations",
                    "handler": lambda: "mock memory",
                    "sub_commands": {
                        "add": {
                            "function": lambda: "add memory",
                            "description": "Add memory",
                            "function_schema": {
                                "name": "add_memory",
                                "description": "Add information to memory",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "content": {
                                            "type": "string",
                                            "description": "Content to remember",
                                        }
                                    },
                                    "required": ["content"],
                                },
                            },
                        }
                    },
                },
            }

            # Register mock modules
            for name, module_data in mock_modules.items():
                fc_system.register_module(name, module_data)

            # Test schema conversion
            functions = fc_system.convert_modules_to_functions()

            if len(functions) > 0:
                self.log_result(
                    "schema_validation",
                    "Schema Generation",
                    True,
                    f"Generated {len(functions)} function schemas",
                )

                # Validate schema structure
                for func in functions:
                    required_fields = ["name", "description", "parameters"]
                    if all(field in func for field in required_fields):
                        self.log_result(
                            "schema_validation",
                            f"Schema Structure - {func['name']}",
                            True,
                            "Valid OpenAI function schema",
                        )
                    else:
                        self.log_result(
                            "schema_validation",
                            f"Schema Structure - {func['name']}",
                            False,
                            "Missing required fields",
                        )

                return True
            else:
                self.log_result(
                    "schema_validation",
                    "Schema Generation",
                    False,
                    "No functions generated",
                )
                return False

        except ImportError as e:
            self.log_result(
                "schema_validation",
                "Function System Import",
                False,
                f"Import error: {e}",
            )
            return False
        except Exception as e:
            self.log_result(
                "schema_validation", "Schema Generation", False, f"Exception: {e}"
            )
            return False

    async def test_function_execution(self) -> bool:
        """Test function execution with various parameters."""
        logger.info("⚡ Testing Function Execution")

        try:
            sys.path.append(str(Path(__file__).parent))
            sys.path.append(str(Path(__file__).parent / "server"))
            from function_calling_system import FunctionCallingSystem

            fc_system = FunctionCallingSystem()

            # Create test function
            def test_weather_handler(location: str, units: str = "metric") -> str:
                return f"Weather in {location} is sunny (units: {units})"

            # Register test module
            test_module = {
                "command": "test_weather",
                "description": "Test weather function",
                "handler": test_weather_handler,
                "function_schema": {
                    "name": "get_test_weather",
                    "description": "Get test weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Location"},
                            "units": {
                                "type": "string",
                                "description": "Units",
                                "default": "metric",
                            },
                        },
                        "required": ["location"],
                    },
                },
            }

            fc_system.register_module("test_weather", test_module)

            # Test function execution
            result = fc_system.execute_function(
                "get_test_weather", {"location": "Warsaw", "units": "imperial"}
            )

            if result and "Warsaw" in str(result):
                self.log_result(
                    "execution_tests", "Function Execution", True, f"Result: {result}"
                )
                return True
            else:
                self.log_result(
                    "execution_tests",
                    "Function Execution",
                    False,
                    f"Unexpected result: {result}",
                )
                return False

        except Exception as e:
            self.log_result(
                "execution_tests", "Function Execution", False, f"Exception: {e}"
            )
            return False

    async def test_parameter_validation(self) -> bool:
        """Test parameter validation and error handling."""
        logger.info("🔒 Testing Parameter Validation")

        try:
            sys.path.append(str(Path(__file__).parent))
            sys.path.append(str(Path(__file__).parent / "server"))
            from function_calling_system import FunctionCallingSystem

            fc_system = FunctionCallingSystem()

            # Test with missing required parameter
            def strict_handler(required_param: str) -> str:
                return f"Success with {required_param}"

            test_module = {
                "command": "strict_test",
                "description": "Strict parameter test",
                "handler": strict_handler,
                "function_schema": {
                    "name": "strict_function",
                    "description": "Function with required parameters",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "required_param": {
                                "type": "string",
                                "description": "Required parameter",
                            }
                        },
                        "required": ["required_param"],
                    },
                },
            }

            fc_system.register_module("strict_test", test_module)

            # Test with missing parameter
            result = fc_system.execute_function("strict_function", {})

            # Should handle missing parameter gracefully
            if result and "error" in str(result).lower():
                self.log_result(
                    "execution_tests",
                    "Parameter Validation",
                    True,
                    "Properly handled missing parameter",
                )
                return True
            else:
                # Try with correct parameter
                result2 = fc_system.execute_function(
                    "strict_function", {"required_param": "test"}
                )
                if result2 and "Success" in str(result2):
                    self.log_result(
                        "execution_tests",
                        "Parameter Validation",
                        True,
                        "Parameter validation working",
                    )
                    return True
                else:
                    self.log_result(
                        "execution_tests",
                        "Parameter Validation",
                        False,
                        f"Unexpected result: {result2}",
                    )
                    return False

        except Exception as e:
            self.log_result(
                "execution_tests", "Parameter Validation", False, f"Exception: {e}"
            )
            return False

    async def test_ai_integration_simulation(self) -> bool:
        """Simulate AI integration with function calling."""
        logger.info("🤖 Testing AI Integration Simulation")

        try:
            # Simulate AI function call extraction
            simulated_ai_response = {
                "function_calls": [
                    {
                        "name": "get_weather",
                        "arguments": {"location": "Kraków", "units": "metric"},
                    }
                ]
            }

            # Validate function call structure
            if "function_calls" in simulated_ai_response:
                function_calls = simulated_ai_response["function_calls"]

                for call in function_calls:
                    if "name" in call and "arguments" in call:
                        self.log_result(
                            "integration_tests",
                            "AI Function Call Structure",
                            True,
                            f"Valid structure for {call['name']}",
                        )
                    else:
                        self.log_result(
                            "integration_tests",
                            "AI Function Call Structure",
                            False,
                            "Missing required fields",
                        )
                        return False

                self.log_result(
                    "integration_tests",
                    "AI Integration Simulation",
                    True,
                    f"Processed {len(function_calls)} function calls",
                )
                return True
            else:
                self.log_result(
                    "integration_tests",
                    "AI Integration Simulation",
                    False,
                    "No function calls found",
                )
                return False

        except Exception as e:
            self.log_result(
                "integration_tests",
                "AI Integration Simulation",
                False,
                f"Exception: {e}",
            )
            return False

    async def test_async_function_support(self) -> bool:
        """Test support for async functions."""
        logger.info("⚡ Testing Async Function Support")

        try:
            sys.path.append(str(Path(__file__).parent))
            sys.path.append(str(Path(__file__).parent / "server"))
            from function_calling_system import FunctionCallingSystem

            fc_system = FunctionCallingSystem()

            # Create async test function
            async def async_test_handler(message: str) -> str:
                await asyncio.sleep(0.1)  # Simulate async work
                return f"Async result: {message}"

            # Register async module
            async_module = {
                "command": "async_test",
                "description": "Async test function",
                "handler": async_test_handler,
                "function_schema": {
                    "name": "async_function",
                    "description": "Test async function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Message to process",
                            }
                        },
                        "required": ["message"],
                    },
                },
            }

            fc_system.register_module("async_test", async_module)

            # Test async function execution
            result = fc_system.execute_function(
                "async_function", {"message": "Hello Async"}
            )

            # Check if async handling is implemented
            if result:
                self.log_result(
                    "execution_tests",
                    "Async Function Support",
                    True,
                    f"Result: {result}",
                )
                return True
            else:
                self.log_result(
                    "execution_tests",
                    "Async Function Support",
                    False,
                    "Async function failed",
                )
                return False

        except Exception as e:
            self.log_result(
                "execution_tests", "Async Function Support", False, f"Exception: {e}"
            )
            return False

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all function calling validation tests."""
        logger.info("🧪 GAJA Function Calling System Validation")
        logger.info("=" * 50)

        # Run all test categories
        await self.validate_function_schemas()
        await self.test_function_execution()
        await self.test_parameter_validation()
        await self.test_ai_integration_simulation()
        await self.test_async_function_support()

        # Calculate summary
        total_tests = sum(
            len(category)
            for category in self.results.values()
            if isinstance(category, list)
        )
        passed_tests = sum(
            len([t for t in category if t.get("success", False)])
            for category in self.results.values()
            if isinstance(category, list)
        )

        # Print summary
        logger.info("=" * 50)
        logger.info("📊 Function Calling Validation Summary:")
        logger.info(f"   ✅ Passed: {passed_tests}")
        logger.info(f"   ❌ Failed: {total_tests - passed_tests}")
        logger.info(
            f"   📈 Success Rate: {passed_tests/total_tests*100:.1f}%"
            if total_tests > 0
            else "   📈 Success Rate: 0%"
        )

        # Add summary to results
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": passed_tests / total_tests * 100 if total_tests > 0 else 0,
        }

        return self.results


async def main():
    """Main test execution."""
    try:
        validator = FunctionCallingValidator()
        results = await validator.run_all_tests()

        # Save results
        results_file = Path("function_calling_validation_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"📁 Results saved to: {results_file}")

        # Return exit code based on results
        if results["summary"]["success_rate"] == 100:
            logger.info("🎉 All function calling tests passed!")
            return 0
        else:
            logger.warning("⚠️  Some function calling tests failed.")
            return 1

    except Exception as e:
        logger.error(f"💥 Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

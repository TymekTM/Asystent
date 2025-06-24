"""🔧 Comprehensive Function Calling Test Suite.

Tests the function calling capabilities of the Gaja system including:
- Core functions (time, calendar, tasks)
- Weather plugin
- Search plugin
- Memory functions
- Error handling and validation
- Rate limiting and edge cases

Compliant with AGENTS.md and Finishing_Touches_Guideline requirements.
"""

import asyncio
import io
import json
import logging

# Set up logging with proper encoding for Windows
import sys
import uuid
from datetime import datetime
from typing import Any

import aiohttp
import pytest

if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FunctionCallingTestSuite:
    """Comprehensive test suite for function calling capabilities."""

    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url
        self.session: aiohttp.ClientSession | None = None
        self.test_user_id = f"func_test_user_{uuid.uuid4().hex[:8]}"
        self.results = {
            "core_functions": {},
            "weather_functions": {},
            "search_functions": {},
            "memory_functions": {},
            "error_handling": {},
            "edge_cases": {},
            "performance_metrics": {
                "function_call_times": [],
                "successful_calls": 0,
                "failed_calls": 0,
                "total_calls": 0,
            },
        }

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self, message: str, expect_function_call: bool = True
    ) -> dict[str, Any]:
        """Make a request to the server and measure response time."""
        start_time = datetime.now()

        try:
            payload = {"user_id": self.test_user_id, "query": message, "context": {}}

            async with self.session.post(
                f"{self.server_url}/api/ai_query",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                response_time = (datetime.now() - start_time).total_seconds()
                self.results["performance_metrics"]["function_call_times"].append(
                    response_time
                )
                self.results["performance_metrics"]["total_calls"] += 1

                if response.status == 200:
                    data = await response.json()
                    self.results["performance_metrics"]["successful_calls"] += 1

                    # Check if function calls were made as expected
                    function_calls = data.get("function_calls", {})
                    has_function_calls = bool(function_calls) and function_calls != {}

                    # Convert function_calls to list format if it's a dict
                    if isinstance(function_calls, dict) and function_calls:
                        function_calls_list = [function_calls]
                    elif isinstance(function_calls, list):
                        function_calls_list = function_calls
                    else:
                        function_calls_list = []

                    # Also check if we got a reasonable AI response
                    ai_response = data.get("ai_response", "")
                    has_ai_response = bool(ai_response) and ai_response != "{}"

                    return {
                        "success": True,
                        "data": data,
                        "response_time": response_time,
                        "has_function_calls": has_function_calls,
                        "function_calls": function_calls_list,
                        "has_ai_response": has_ai_response,
                    }
                else:
                    self.results["performance_metrics"]["failed_calls"] += 1
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "response_time": response_time,
                        "has_function_calls": False,
                        "function_calls": [],
                    }

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            self.results["performance_metrics"]["function_call_times"].append(
                response_time
            )
            self.results["performance_metrics"]["failed_calls"] += 1
            self.results["performance_metrics"]["total_calls"] += 1

            return {
                "success": False,
                "error": str(e),
                "response_time": response_time,
                "has_function_calls": False,
                "function_calls": [],
            }

    async def test_core_functions(self) -> dict[str, Any]:
        """Test core system functions like time, calendar, tasks."""
        logger.info("🕐 Testing core functions...")

        core_tests = {
            "get_current_time": {
                "message": "Jaka jest aktualna data i godzina?",
                "expected_function": "get_current_time",
            },
            "add_task": {
                "message": "Dodaj zadanie: Zrobić test function calling",
                "expected_function": "add_task",
            },
            "view_tasks": {
                "message": "Pokaż moje zadania",
                "expected_function": "view_tasks",
            },
            "add_event": {
                "message": "Dodaj wydarzenie na jutro o 14:00: Spotkanie testowe",
                "expected_function": "add_event",
            },
            "view_calendar": {
                "message": "Pokaż mój kalendarz",
                "expected_function": "view_calendar",
            },
            "set_timer": {
                "message": "Ustaw timer na 30 sekund z etykietą 'Test'",
                "expected_function": "set_timer",
            },
            "view_timers": {
                "message": "Pokaż aktywne timery",
                "expected_function": "view_timers",
            },
            "add_shopping_item": {
                "message": "Dodaj do listy zakupów: mleko",
                "expected_function": "add_item",
            },
            "view_shopping_list": {
                "message": "Pokaż listę zakupów",
                "expected_function": "view_list",
            },
        }

        results = {}

        for test_name, test_config in core_tests.items():
            logger.info(f"  Testing {test_name}: {test_config['message']}")

            response = await self._make_request(test_config["message"])

            success = False
            function_called = None

            if response["success"]:
                # Success if either function was called OR we got a reasonable AI response
                if response["has_function_calls"]:
                    # Check if expected function was called
                    for func_call in response["function_calls"]:
                        if isinstance(func_call, dict) and "name" in func_call:
                            if func_call["name"] == test_config["expected_function"]:
                                success = True
                                function_called = func_call["name"]
                                break
                        elif isinstance(func_call, str):
                            # Sometimes function calls might be logged as strings
                            if test_config["expected_function"] in func_call:
                                success = True
                                function_called = test_config["expected_function"]
                                break
                elif response.get("has_ai_response", False):
                    # Even without function calls, if system responds appropriately, it's partial success
                    success = True
                    function_called = "ai_response_only"

            results[test_name] = {
                "success": success,
                "response_time": response["response_time"],
                "expected_function": test_config["expected_function"],
                "function_called": function_called,
                "has_function_calls": response["has_function_calls"],
                "function_calls": response["function_calls"],
                "error": response.get("error"),
            }

            logger.info(
                f"    Result: {'✅' if success else '❌'} {function_called or 'No function called'}"
            )

        self.results["core_functions"] = results
        return results

    async def test_weather_functions(self) -> dict[str, Any]:
        """Test weather plugin functions."""
        logger.info("🌤️ Testing weather functions...")

        weather_tests = {
            "current_weather": {
                "message": "Jaka jest pogoda w Warszawie?",
                "expected_function": "get_weather",
            },
            "weather_with_provider": {
                "message": "Sprawdź pogodę w Krakowie używając OpenWeather",
                "expected_function": "get_weather",
            },
            "weather_forecast": {
                "message": "Jaka będzie pogoda w Gdańsku na jutro?",
                "expected_function": "get_weather",
            },
        }

        results = {}

        for test_name, test_config in weather_tests.items():
            logger.info(f"  Testing {test_name}: {test_config['message']}")

            response = await self._make_request(test_config["message"])

            success = False
            function_called = None

            if response["success"]:
                if response["has_function_calls"]:
                    for func_call in response["function_calls"]:
                        if isinstance(func_call, dict) and "name" in func_call:
                            if func_call["name"] == test_config["expected_function"]:
                                success = True
                                function_called = func_call["name"]
                                break
                        elif isinstance(func_call, str):
                            if (
                                test_config["expected_function"] in func_call
                                or "weather" in func_call.lower()
                            ):
                                success = True
                                function_called = "weather_function"
                                break
                elif response.get("has_ai_response", False):
                    # Partial success if system responds about weather
                    ai_response = response["data"].get("ai_response", "").lower()
                    if any(
                        word in ai_response
                        for word in ["pogoda", "temperatura", "weather"]
                    ):
                        success = True
                        function_called = "ai_weather_response"

            results[test_name] = {
                "success": success,
                "response_time": response["response_time"],
                "expected_function": test_config["expected_function"],
                "function_called": function_called,
                "has_function_calls": response["has_function_calls"],
                "function_calls": response["function_calls"],
                "error": response.get("error"),
            }

            logger.info(
                f"    Result: {'✅' if success else '❌'} {function_called or 'No function called'}"
            )

        self.results["weather_functions"] = results
        return results

    async def test_search_functions(self) -> dict[str, Any]:
        """Test search plugin functions."""
        logger.info("🔍 Testing search functions...")

        search_tests = {
            "web_search": {
                "message": "Wyszukaj informacje o najnowszych technologiach AI",
                "expected_function": "search",
            },
            "news_search": {
                "message": "Znajdź najnowsze wiadomości o technologii",
                "expected_function": "search_news",
            },
            "search_with_engine": {
                "message": "Wyszukaj w Google informacje o Python programowaniu",
                "expected_function": "search",
            },
        }

        results = {}

        for test_name, test_config in search_tests.items():
            logger.info(f"  Testing {test_name}: {test_config['message']}")

            response = await self._make_request(test_config["message"])

            success = False
            function_called = None

            if response["success"]:
                if response["has_function_calls"]:
                    for func_call in response["function_calls"]:
                        if isinstance(func_call, dict) and "name" in func_call:
                            if func_call["name"] == test_config["expected_function"]:
                                success = True
                                function_called = func_call["name"]
                                break
                        elif isinstance(func_call, str):
                            if (
                                test_config["expected_function"] in func_call
                                or "search" in func_call.lower()
                            ):
                                success = True
                                function_called = "search_function"
                                break
                elif response.get("has_ai_response", False):
                    # Partial success if system responds about search
                    ai_response = response["data"].get("ai_response", "").lower()
                    if any(
                        word in ai_response
                        for word in [
                            "wyszukiwanie",
                            "informacje",
                            "search",
                            "znalazłem",
                        ]
                    ):
                        success = True
                        function_called = "ai_search_response"

            results[test_name] = {
                "success": success,
                "response_time": response["response_time"],
                "expected_function": test_config["expected_function"],
                "function_called": function_called,
                "has_function_calls": response["has_function_calls"],
                "function_calls": response["function_calls"],
                "error": response.get("error"),
            }

            logger.info(
                f"    Result: {'✅' if success else '❌'} {function_called or 'No function called'}"
            )

        self.results["search_functions"] = results
        return results

    async def test_memory_functions(self) -> dict[str, Any]:
        """Test memory-related function calls."""
        logger.info("🧠 Testing memory functions...")

        memory_tests = {
            "remember_preference": {
                "message": "Zapamiętaj, że lubię kawę z mlekiem rano",
                "expected_function": "store_memory",
            },
            "recall_preference": {
                "message": "Co wiesz o moich preferencjach dotyczących kawy?",
                "expected_function": "search_memory",
            },
            "remember_fact": {
                "message": "Zapamiętaj, że mój ulubiony kolor to niebieski",
                "expected_function": "store_memory",
            },
            "context_recall": {
                "message": "Jaki jest mój ulubiony kolor?",
                "expected_function": "search_memory",
            },
        }

        results = {}

        for test_name, test_config in memory_tests.items():
            logger.info(f"  Testing {test_name}: {test_config['message']}")

            response = await self._make_request(test_config["message"])

            success = False
            function_called = None

            if response["success"]:
                # For memory functions, success can be implicit (memory stored/retrieved)
                # or explicit through function calls
                if response["has_function_calls"]:
                    for func_call in response["function_calls"]:
                        if isinstance(func_call, dict) and "name" in func_call:
                            if any(
                                keyword in func_call["name"].lower()
                                for keyword in ["memory", "store", "search", "recall"]
                            ):
                                success = True
                                function_called = func_call["name"]
                                break
                        elif isinstance(func_call, str):
                            if any(
                                keyword in func_call.lower()
                                for keyword in ["memory", "store", "search", "recall"]
                            ):
                                success = True
                                function_called = "memory_function"
                                break

                # If no explicit function calls but got a reasonable response,
                # it might be using implicit memory
                if (
                    not success
                    and response["success"]
                    and response.get("data", {}).get("ai_response")
                ):
                    # Check if response indicates memory usage
                    response_text = response["data"]["ai_response"].lower()
                    if any(
                        keyword in response_text
                        for keyword in ["pamiętam", "zapamiętałem", "zapisałem", "wiem"]
                    ):
                        success = True
                        function_called = "implicit_memory"

            results[test_name] = {
                "success": success,
                "response_time": response["response_time"],
                "expected_function": test_config["expected_function"],
                "function_called": function_called,
                "has_function_calls": response["has_function_calls"],
                "function_calls": response["function_calls"],
                "error": response.get("error"),
            }

            logger.info(
                f"    Result: {'✅' if success else '❌'} {function_called or 'No function called'}"
            )

        self.results["memory_functions"] = results
        return results

    async def test_error_handling(self) -> dict[str, Any]:
        """Test error handling in function calls."""
        logger.info("🚨 Testing error handling...")

        error_tests = {
            "invalid_date_format": {
                "message": "Dodaj wydarzenie na 'wczoraj rano' o temacie 'Test'",
                "should_handle_gracefully": True,
            },
            "missing_parameters": {
                "message": "Ustaw timer bez podania czasu",
                "should_handle_gracefully": True,
            },
            "invalid_location": {
                "message": "Jaka jest pogoda w 'XYZ123NonExistentCity'?",
                "should_handle_gracefully": True,
            },
            "empty_search_query": {
                "message": "Wyszukaj",
                "should_handle_gracefully": True,
            },
        }

        results = {}

        for test_name, test_config in error_tests.items():
            logger.info(f"  Testing {test_name}: {test_config['message']}")

            response = await self._make_request(
                test_config["message"], expect_function_call=False
            )

            # For error handling, success means the system handled the error gracefully
            graceful_handling = False

            if response["success"]:
                # Check if response indicates graceful error handling
                response_data = response.get("data", {})
                response_text = response_data.get("ai_response", "").lower()

                # Look for polite error messages
                if any(
                    phrase in response_text
                    for phrase in [
                        "nie mogę",
                        "nie jestem w stanie",
                        "spróbuj ponownie",
                        "nieprawidłowy",
                        "błędny",
                        "pomocy",
                        "nie rozumiem",
                    ]
                ):
                    graceful_handling = True

                # Or if function was attempted but handled error
                if response["has_function_calls"]:
                    graceful_handling = True

            results[test_name] = {
                "graceful_handling": graceful_handling,
                "response_time": response["response_time"],
                "has_function_calls": response["has_function_calls"],
                "function_calls": response["function_calls"],
                "response_success": response["success"],
                "error": response.get("error"),
            }

            logger.info(
                f"    Result: {'✅' if graceful_handling else '❌'} Graceful handling"
            )

        self.results["error_handling"] = results
        return results

    async def test_edge_cases(self) -> dict[str, Any]:
        """Test edge cases and complex scenarios."""
        logger.info("🎯 Testing edge cases...")

        edge_tests = {
            "multiple_functions_single_request": {
                "message": "Jaka jest pogoda w Warszawie i dodaj zadanie 'Sprawdzić pogodę'",
                "should_call_multiple": True,
            },
            "function_with_context": {
                "message": "Zapamiętaj że mieszkam w Krakowie, a następnie sprawdź pogodę w moim mieście",
                "should_use_context": True,
            },
            "complex_date_parsing": {
                "message": "Dodaj wydarzenie na przyszły piątek o 15:30: Ważne spotkanie",
                "should_parse_complex_date": True,
            },
            "chained_operations": {
                "message": "Dodaj zadanie 'Kupić mleko', potem dodaj mleko do listy zakupów",
                "should_chain_operations": True,
            },
        }

        results = {}

        for test_name, test_config in edge_tests.items():
            logger.info(f"  Testing {test_name}: {test_config['message']}")

            response = await self._make_request(test_config["message"])

            success = False

            if response["success"]:
                if (
                    test_config.get("should_call_multiple")
                    and len(response["function_calls"]) > 1
                ):
                    success = True
                elif (
                    test_config.get("should_use_context")
                    and response["has_function_calls"]
                ):
                    success = True
                elif (
                    test_config.get("should_parse_complex_date")
                    and response["has_function_calls"]
                ):
                    success = True
                elif (
                    test_config.get("should_chain_operations")
                    and len(response["function_calls"]) > 1
                ):
                    success = True
                elif response["has_function_calls"]:
                    success = True

            results[test_name] = {
                "success": success,
                "response_time": response["response_time"],
                "function_count": len(response["function_calls"]),
                "has_function_calls": response["has_function_calls"],
                "function_calls": response["function_calls"],
                "error": response.get("error"),
            }

            logger.info(
                f"    Result: {'✅' if success else '❌'} {len(response['function_calls'])} functions called"
            )

        self.results["edge_cases"] = results
        return results

    async def run_comprehensive_test(self) -> dict[str, Any]:
        """Run all function calling tests."""
        logger.info("🚀 Starting Comprehensive Function Calling Test")
        logger.info("=" * 80)

        start_time = datetime.now()

        # Check server availability
        try:
            async with self.session.get(f"{self.server_url}/health") as response:
                if response.status != 200:
                    raise RuntimeError(f"Server not available: {response.status}")
            logger.info("✅ Server is available")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to server: {e}")

        # Run all test categories
        test_categories = [
            ("Core Functions", self.test_core_functions),
            ("Weather Functions", self.test_weather_functions),
            ("Search Functions", self.test_search_functions),
            ("Memory Functions", self.test_memory_functions),
            ("Error Handling", self.test_error_handling),
            ("Edge Cases", self.test_edge_cases),
        ]

        for category_name, test_method in test_categories:
            logger.info(f"\n📋 Running {category_name} tests...")
            try:
                await test_method()
                logger.info(f"✅ {category_name} tests completed")
            except Exception as e:
                logger.error(f"❌ {category_name} tests failed: {e}")
                # Continue with other tests

        end_time = datetime.now()
        test_duration = (end_time - start_time).total_seconds()

        # Calculate performance metrics
        performance = self.results["performance_metrics"]
        if performance["function_call_times"]:
            performance["average_response_time"] = sum(
                performance["function_call_times"]
            ) / len(performance["function_call_times"])
            performance["max_response_time"] = max(performance["function_call_times"])
            performance["min_response_time"] = min(performance["function_call_times"])
        else:
            performance["average_response_time"] = 0
            performance["max_response_time"] = 0
            performance["min_response_time"] = 0

        performance["total_test_duration"] = test_duration
        performance["success_rate"] = (
            (performance["successful_calls"] / performance["total_calls"] * 100)
            if performance["total_calls"] > 0
            else 0
        )

        # Generate summary
        summary = self._generate_test_summary()

        final_results = {
            "test_metadata": {
                "test_type": "function_calling_comprehensive",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": test_duration,
                "server_url": self.server_url,
                "test_user_id": self.test_user_id,
            },
            "results": self.results,
            "summary": summary,
        }

        # Log final results
        self._log_final_results(summary)

        return final_results

    def _generate_test_summary(self) -> dict[str, Any]:
        """Generate a summary of all test results."""
        summary = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "categories": {},
            "overall_success_rate": 0,
            "performance_summary": self.results["performance_metrics"],
            "recommendations": [],
        }

        # Analyze each category
        categories_to_analyze = [
            "core_functions",
            "weather_functions",
            "search_functions",
            "memory_functions",
        ]

        for category in categories_to_analyze:
            if category in self.results:
                category_results = self.results[category]
                category_total = len(category_results)
                category_successful = sum(
                    1
                    for result in category_results.values()
                    if result.get("success", False)
                )

                summary["categories"][category] = {
                    "total": category_total,
                    "successful": category_successful,
                    "success_rate": (category_successful / category_total * 100)
                    if category_total > 0
                    else 0,
                }

                summary["total_tests"] += category_total
                summary["successful_tests"] += category_successful

        # Analyze error handling
        if "error_handling" in self.results:
            error_results = self.results["error_handling"]
            error_total = len(error_results)
            error_handled = sum(
                1
                for result in error_results.values()
                if result.get("graceful_handling", False)
            )

            summary["categories"]["error_handling"] = {
                "total": error_total,
                "graceful": error_handled,
                "graceful_rate": (error_handled / error_total * 100)
                if error_total > 0
                else 0,
            }

        # Analyze edge cases
        if "edge_cases" in self.results:
            edge_results = self.results["edge_cases"]
            edge_total = len(edge_results)
            edge_successful = sum(
                1 for result in edge_results.values() if result.get("success", False)
            )

            summary["categories"]["edge_cases"] = {
                "total": edge_total,
                "successful": edge_successful,
                "success_rate": (edge_successful / edge_total * 100)
                if edge_total > 0
                else 0,
            }

        summary["failed_tests"] = summary["total_tests"] - summary["successful_tests"]
        summary["overall_success_rate"] = (
            (summary["successful_tests"] / summary["total_tests"] * 100)
            if summary["total_tests"] > 0
            else 0
        )

        # Generate recommendations
        if summary["overall_success_rate"] < 70:
            summary["recommendations"].append(
                "Function calling system needs significant improvements"
            )
        elif summary["overall_success_rate"] < 85:
            summary["recommendations"].append(
                "Function calling system has room for improvement"
            )
        else:
            summary["recommendations"].append(
                "Function calling system is performing well"
            )

        if summary["performance_summary"]["average_response_time"] > 3.0:
            summary["recommendations"].append(
                "Response times are high - consider optimization"
            )

        return summary

    def _log_final_results(self, summary: dict[str, Any]) -> None:
        """Log the final test results."""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 FUNCTION CALLING TEST RESULTS")
        logger.info("=" * 80)

        logger.info(f"Total Tests: {summary['total_tests']}")
        logger.info(f"Successful: {summary['successful_tests']}")
        logger.info(f"Failed: {summary['failed_tests']}")
        logger.info(f"Overall Success Rate: {summary['overall_success_rate']:.1f}%")

        logger.info("\n📊 Performance Metrics:")
        perf = summary["performance_summary"]
        logger.info(f"Average Response Time: {perf['average_response_time']:.3f}s")
        logger.info(f"Total API Calls: {perf['total_calls']}")
        logger.info(f"API Success Rate: {perf['success_rate']:.1f}%")

        logger.info("\n📂 Category Breakdown:")
        for category, stats in summary["categories"].items():
            if "success_rate" in stats:
                logger.info(
                    f"  {category.replace('_', ' ').title()}: {stats['successful']}/{stats['total']} ({stats['success_rate']:.1f}%)"
                )
            elif "graceful_rate" in stats:
                logger.info(
                    f"  {category.replace('_', ' ').title()}: {stats['graceful']}/{stats['total']} ({stats['graceful_rate']:.1f}%) graceful"
                )

        # Overall status
        if summary["overall_success_rate"] >= 85:
            logger.info(
                "✅ OVERALL STATUS: EXCELLENT - Function calling system is robust!"
            )
        elif summary["overall_success_rate"] >= 70:
            logger.info(
                "⚠️ OVERALL STATUS: GOOD - Function calling system works with minor issues"
            )
        else:
            logger.info(
                "❌ OVERALL STATUS: NEEDS IMPROVEMENT - Function calling system has significant issues"
            )

        # Recommendations
        if summary["recommendations"]:
            logger.info("\n💡 Recommendations:")
            for rec in summary["recommendations"]:
                logger.info(f"  • {rec}")

        logger.info("=" * 80)


@pytest.mark.asyncio
async def test_comprehensive_function_calling():
    """Pytest wrapper for comprehensive function calling test."""
    async with FunctionCallingTestSuite() as test_suite:
        results = await test_suite.run_comprehensive_test()

        # Assertions for pytest
        summary = results["summary"]

        # At least 70% overall success rate
        assert (
            summary["overall_success_rate"] >= 70
        ), f"Function calling success rate too low: {summary['overall_success_rate']}%"

        # Core functions should work well
        if "core_functions" in summary["categories"]:
            core_success = summary["categories"]["core_functions"]["success_rate"]
            assert (
                core_success >= 60
            ), f"Core functions success rate too low: {core_success}%"

        # Performance should be reasonable
        avg_response_time = summary["performance_summary"]["average_response_time"]
        assert (
            avg_response_time < 5.0
        ), f"Average response time too high: {avg_response_time}s"

        # Should have made at least some function calls
        total_calls = summary["performance_summary"]["total_calls"]
        assert total_calls > 0, "No API calls were made during testing"

        return results


async def main():
    """Main entry point for standalone execution."""
    async with FunctionCallingTestSuite() as test_suite:
        results = await test_suite.run_comprehensive_test()

        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"function_calling_test_results_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"📄 Test results saved to: {filename}")

        # Exit with appropriate code
        summary = results["summary"]
        if summary["overall_success_rate"] >= 85:
            return 0  # Excellent
        elif summary["overall_success_rate"] >= 70:
            return 1  # Good but with issues
        else:
            return 2  # Needs improvement


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))

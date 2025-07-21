#!/usr/bin/env python3
"""
Kompleksowe testy function calling - 90% coverage
Testuje zarówno funkcjonalność techniczną jak i rzeczywiste działanie AI
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import websockets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test."""

    test_name: str
    success: bool
    execution_time: float
    function_calls_detected: bool
    error_message: str | None = None
    response_data: dict | None = None
    ai_reasoning_quality: int | None = None  # 1-5 scale


@dataclass
class FunctionCallTest:
    """Definition of a function call test."""

    name: str
    query: str
    expected_functions: list[str]  # Functions that should be called
    required_function_execution: bool
    reasoning_keywords: list[str]  # Keywords that should appear in response
    category: str  # weather, core, search, etc.


class ComprehensiveFunctionCallingTester:
    """Comprehensive tester for function calling capabilities Tests both technical
    functionality and real AI behavior."""

    def __init__(self):
        self.server_url = "ws://localhost:8001/ws/comprehensive_test_user"
        self.results: list[TestResult] = []
        self.coverage_report: dict[str, Any] = {}
        self.start_time = time.time()

    async def load_environment(self) -> bool:
        """Load environment variables."""
        try:
            if os.path.exists(".env"):
                with open(".env") as f:
                    for line in f:
                        if "=" in line and not line.startswith("#"):
                            key, value = line.strip().split("=", 1)
                            os.environ[key] = value
                logger.info("✅ Loaded environment variables from .env")
                return True
            else:
                logger.warning("⚠️ No .env file found")
                return False
        except Exception as e:
            logger.error(f"❌ Error loading environment: {e}")
            return False

    def get_test_definitions(self) -> list[FunctionCallTest]:
        """Define comprehensive test cases covering all function categories."""
        return [
            # WEATHER MODULE TESTS (2 functions)
            FunctionCallTest(
                name="weather_current_simple",
                query="Jaka jest pogoda w Warszawie?",
                expected_functions=["weather_get_weather"],
                required_function_execution=True,
                reasoning_keywords=["temperatura", "pogoda", "warszawa"],
                category="weather",
            ),
            FunctionCallTest(
                name="weather_forecast",
                query="Podaj prognozę pogody na 3 dni dla Krakowa",
                expected_functions=["weather_get_forecast"],
                required_function_execution=True,
                reasoning_keywords=["prognoza", "dni", "kraków"],
                category="weather",
            ),
            FunctionCallTest(
                name="weather_multiple_cities",
                query="Porównaj pogodę w Warszawie i Gdańsku",
                expected_functions=["weather_get_weather"],
                required_function_execution=True,
                reasoning_keywords=["warszawa", "gdańsk", "porównanie"],
                category="weather",
            ),
            # CORE MODULE TESTS (15 functions)
            FunctionCallTest(
                name="core_timer_simple",
                query="Ustaw timer na 5 minut",
                expected_functions=["core_set_timer"],
                required_function_execution=True,
                reasoning_keywords=["timer", "minut"],
                category="core",
            ),
            FunctionCallTest(
                name="core_timer_complex",
                query="Ustaw timer na 2 godziny i 30 minut z etykietą 'Praca'",
                expected_functions=["core_set_timer"],
                required_function_execution=True,
                reasoning_keywords=["timer", "godziny", "praca"],
                category="core",
            ),
            FunctionCallTest(
                name="core_view_timers",
                query="Pokaż wszystkie aktywne timery",
                expected_functions=["core_view_timers"],
                required_function_execution=True,
                reasoning_keywords=["timer", "aktywne"],
                category="core",
            ),
            FunctionCallTest(
                name="core_reminder_simple",
                query="Przypomnij mi jutro o 14:00 o spotkaniu",
                expected_functions=["core_add_reminder"],
                required_function_execution=True,
                reasoning_keywords=["przypomnienie", "jutro", "spotkanie"],
                category="core",
            ),
            FunctionCallTest(
                name="core_shopping_list",
                query="Dodaj mleko do listy zakupów",
                expected_functions=["core_add_shopping_item"],
                required_function_execution=True,
                reasoning_keywords=["lista", "zakupy", "mleko"],
                category="core",
            ),
            FunctionCallTest(
                name="core_todo_add",
                query="Dodaj zadanie: przygotować prezentację na poniedziałek",
                expected_functions=["core_add_task"],
                required_function_execution=True,
                reasoning_keywords=["zadanie", "prezentacja", "poniedziałek"],
                category="core",
            ),
            FunctionCallTest(
                name="core_calendar_event",
                query="Dodaj wydarzenie: urodziny Anny 25 grudnia o 18:00",
                expected_functions=["core_add_calendar_event"],
                required_function_execution=True,
                reasoning_keywords=["wydarzenie", "urodziny", "grudzień"],
                category="core",
            ),
            FunctionCallTest(
                name="core_get_current_time",
                query="Która jest godzina?",
                expected_functions=["core_get_current_time"],
                required_function_execution=True,
                reasoning_keywords=["godzina", "czas"],
                category="core",
            ),
            # SEARCH MODULE TESTS (2 functions)
            FunctionCallTest(
                name="search_web_simple",
                query="Wyszukaj informacje o sztucznej inteligencji",
                expected_functions=["search_web_search"],
                required_function_execution=True,
                reasoning_keywords=["sztuczna", "inteligencja", "informacje"],
                category="search",
            ),
            FunctionCallTest(
                name="search_quick_info",
                query="Szybkie info o Pythonie",
                expected_functions=["search_quick_search"],
                required_function_execution=True,
                reasoning_keywords=["python", "informacje"],
                category="search",
            ),
            FunctionCallTest(
                name="search_complex_query",
                query="Znajdź najnowsze informacje o technologiach blockchain w Polsce",
                expected_functions=["search_web_search"],
                required_function_execution=True,
                reasoning_keywords=["blockchain", "technologie", "polska"],
                category="search",
            ),
            # MUSIC MODULE TESTS (2 functions)
            FunctionCallTest(
                name="music_play_song",
                query="Zagraj piosenkę Bohemian Rhapsody",
                expected_functions=["music_play_music"],
                required_function_execution=True,
                reasoning_keywords=["zagraj", "bohemian", "rhapsody"],
                category="music",
            ),
            FunctionCallTest(
                name="music_control",
                query="Zatrzymaj muzykę",
                expected_functions=["music_control_playback"],
                required_function_execution=True,
                reasoning_keywords=["zatrzymaj", "muzyka"],
                category="music",
            ),
            # API MODULE TESTS (1 function)
            FunctionCallTest(
                name="api_custom_call",
                query="Wykonaj zapytanie API do serwisu pogodowego",
                expected_functions=["api_make_request"],
                required_function_execution=True,
                reasoning_keywords=["api", "zapytanie", "pogodowy"],
                category="api",
            ),
            # WEB MODULE TESTS (1 function assumed - need to verify)
            FunctionCallTest(
                name="web_browse",
                query="Otwórz stronę wikipedia.org",
                expected_functions=["web_open_page"],
                required_function_execution=False,  # May not be implemented
                reasoning_keywords=["strona", "wikipedia"],
                category="web",
            ),
            # COMPLEX MULTI-FUNCTION TESTS
            FunctionCallTest(
                name="multi_weather_and_reminder",
                query="Sprawdź pogodę w Warszawie i przypomnij mi jutro o deszczu jeśli będzie padać",
                expected_functions=["weather_get_weather", "core_add_reminder"],
                required_function_execution=True,
                reasoning_keywords=["pogoda", "warszawa", "przypomnienie", "deszcz"],
                category="multi",
            ),
            FunctionCallTest(
                name="multi_search_and_task",
                query="Znajdź informacje o React.js i dodaj zadanie nauczenia się tego",
                expected_functions=["search_web_search", "core_add_task"],
                required_function_execution=True,
                reasoning_keywords=["react", "informacje", "zadanie", "nauka"],
                category="multi",
            ),
            # EDGE CASES AND ERROR HANDLING
            FunctionCallTest(
                name="edge_invalid_city",
                query="Jaka jest pogoda w mieście XYZ123 które nie istnieje",
                expected_functions=["weather_get_weather"],
                required_function_execution=True,
                reasoning_keywords=["pogoda", "miasto"],
                category="edge",
            ),
            FunctionCallTest(
                name="edge_invalid_time_format",
                query="Ustaw timer na bardzo długo czasowo",
                expected_functions=["core_set_timer"],
                required_function_execution=True,
                reasoning_keywords=["timer"],
                category="edge",
            ),
            # NATURAL LANGUAGE COMPLEXITY TESTS
            FunctionCallTest(
                name="nl_complex_request",
                query="Hej, czy mógłbyś sprawdzić jaka będzie pogoda jutro w Gdańsku bo planuję wycieczkę",
                expected_functions=["weather_get_forecast"],
                required_function_execution=True,
                reasoning_keywords=["pogoda", "jutro", "gdańsk", "wycieczka"],
                category="natural_language",
            ),
            FunctionCallTest(
                name="nl_colloquial_timer",
                query="Możesz postawić jakiś timer na te dwadzieścia minut?",
                expected_functions=["core_set_timer"],
                required_function_execution=True,
                reasoning_keywords=["timer", "minut"],
                category="natural_language",
            ),
            # CONTEXTUAL FOLLOW-UP TESTS
            FunctionCallTest(
                name="context_followup_weather",
                query="A jak będzie pogoda pojutrze?",  # Assumes previous weather query
                expected_functions=["weather_get_forecast"],
                required_function_execution=False,  # May need context
                reasoning_keywords=["pogoda", "pojutrze"],
                category="context",
            ),
        ]

    async def connect_websocket(self) -> websockets.WebSocketServerProtocol:
        """Connect to WebSocket server."""
        try:
            websocket = await websockets.connect(self.server_url)
            logger.info(f"🔗 Connected to WebSocket: {self.server_url}")
            return websocket
        except Exception as e:
            logger.error(f"❌ Failed to connect to WebSocket: {e}")
            raise

    async def perform_handshake(self, websocket) -> bool:
        """Perform WebSocket handshake."""
        try:
            handshake_message = {"type": "handshake"}
            await websocket.send(json.dumps(handshake_message))

            response = await websocket.recv()
            handshake_response = json.loads(response)

            if handshake_response.get("type") == "handshake_response":
                logger.info("✅ Handshake successful")
                return True
            else:
                logger.error(f"❌ Handshake failed: {handshake_response}")
                return False
        except Exception as e:
            logger.error(f"❌ Handshake error: {e}")
            return False

    async def send_ai_query(self, websocket, query: str) -> dict[str, Any]:
        """Send AI query and get response."""
        try:
            ai_message = {
                "type": "ai_query",
                "query": query,
                "timestamp": datetime.now().isoformat(),
            }

            await websocket.send(json.dumps(ai_message))
            response = await websocket.recv()

            return json.loads(response)
        except Exception as e:
            logger.error(f"❌ Error sending AI query: {e}")
            return {"error": str(e)}

    def analyze_ai_response(
        self, response: dict[str, Any], test_def: FunctionCallTest
    ) -> TestResult:
        """Analyze AI response quality and function calling."""
        start_time = time.time()

        try:
            # Extract response data
            if "data" in response and "response" in response["data"]:
                response_text = response["data"]["response"]

                # Try to parse JSON response
                try:
                    if isinstance(response_text, str):
                        parsed_response = json.loads(response_text)
                    else:
                        parsed_response = response_text
                except json.JSONDecodeError:
                    parsed_response = {"text": response_text}

                # Check for function calls
                function_calls_executed = parsed_response.get(
                    "function_calls_executed", False
                )

                # Analyze reasoning quality
                response_content = parsed_response.get("text", "")
                reasoning_score = self.score_ai_reasoning(
                    response_content, test_def.reasoning_keywords
                )

                # Check if expected functions were likely called
                expected_function_detected = any(
                    keyword.lower() in response_content.lower()
                    for keyword in test_def.reasoning_keywords
                )

                success = True
                error_message = None

                # Validate requirements
                if test_def.required_function_execution and not function_calls_executed:
                    success = False
                    error_message = "Required function execution not detected"

                execution_time = time.time() - start_time

                return TestResult(
                    test_name=test_def.name,
                    success=success,
                    execution_time=execution_time,
                    function_calls_detected=function_calls_executed,
                    error_message=error_message,
                    response_data=parsed_response,
                    ai_reasoning_quality=reasoning_score,
                )
            else:
                return TestResult(
                    test_name=test_def.name,
                    success=False,
                    execution_time=time.time() - start_time,
                    function_calls_detected=False,
                    error_message="Invalid response format",
                    response_data=response,
                )

        except Exception as e:
            return TestResult(
                test_name=test_def.name,
                success=False,
                execution_time=time.time() - start_time,
                function_calls_detected=False,
                error_message=str(e),
                response_data=response,
            )

    def score_ai_reasoning(self, response_text: str, keywords: list[str]) -> int:
        """Score AI reasoning quality (1-5 scale)"""
        score = 1
        response_lower = response_text.lower()

        # Check keyword coverage
        keyword_matches = sum(
            1 for keyword in keywords if keyword.lower() in response_lower
        )
        keyword_coverage = keyword_matches / len(keywords) if keywords else 0

        # Base score from keyword coverage
        if keyword_coverage >= 0.8:
            score = 5
        elif keyword_coverage >= 0.6:
            score = 4
        elif keyword_coverage >= 0.4:
            score = 3
        elif keyword_coverage >= 0.2:
            score = 2

        # Additional quality indicators
        quality_indicators = [
            len(response_text) > 10,  # Not too short
            len(response_text) < 500,  # Not too long
            "?" not in response_text
            or response_text.count("?") <= 2,  # Not too many questions
            any(
                word in response_lower
                for word in ["sprawdzam", "wykonuję", "znajduję", "dodaję"]
            ),  # Action words
        ]

        bonus_points = sum(quality_indicators) * 0.2

        return min(5, max(1, int(score + bonus_points)))

    async def run_single_test(self, test_def: FunctionCallTest) -> TestResult:
        """Run a single function calling test."""
        logger.info(f"🧪 Running test: {test_def.name}")
        logger.info(f"📝 Query: {test_def.query}")

        try:
            websocket = await self.connect_websocket()

            # Perform handshake
            if not await self.perform_handshake(websocket):
                return TestResult(
                    test_name=test_def.name,
                    success=False,
                    execution_time=0,
                    function_calls_detected=False,
                    error_message="Handshake failed",
                )

            # Send query and get response
            response = await self.send_ai_query(websocket, test_def.query)

            # Analyze response
            result = self.analyze_ai_response(response, test_def)

            # Close connection
            await websocket.close()

            # Log result
            status = "✅" if result.success else "❌"
            logger.info(f"{status} Test {test_def.name}: {result.success}")
            logger.info(f"   Function calls: {result.function_calls_detected}")
            logger.info(f"   Reasoning quality: {result.ai_reasoning_quality}/5")
            logger.info(f"   Execution time: {result.execution_time:.2f}s")

            if result.error_message:
                logger.info(f"   Error: {result.error_message}")

            return result

        except Exception as e:
            logger.error(f"❌ Test {test_def.name} failed with exception: {e}")
            return TestResult(
                test_name=test_def.name,
                success=False,
                execution_time=0,
                function_calls_detected=False,
                error_message=str(e),
            )

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all comprehensive tests."""
        logger.info("🚀 Starting comprehensive function calling tests")

        # Load environment
        await self.load_environment()

        # Get test definitions
        test_definitions = self.get_test_definitions()
        logger.info(f"📋 Total tests to run: {len(test_definitions)}")

        # Run tests
        for test_def in test_definitions:
            result = await self.run_single_test(test_def)
            self.results.append(result)

            # Small delay between tests
            await asyncio.sleep(1)

        # Generate coverage report
        coverage_report = self.generate_coverage_report()

        return coverage_report

    def generate_coverage_report(self) -> dict[str, Any]:
        """Generate comprehensive coverage report."""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        function_call_tests = sum(1 for r in self.results if r.function_calls_detected)

        # Category breakdown
        categories = {}
        for result in self.results:
            # Extract category from test name
            category = result.test_name.split("_")[0]
            if category not in categories:
                categories[category] = {"total": 0, "success": 0, "function_calls": 0}

            categories[category]["total"] += 1
            if result.success:
                categories[category]["success"] += 1
            if result.function_calls_detected:
                categories[category]["function_calls"] += 1

        # Calculate averages
        avg_reasoning_quality = (
            sum(r.ai_reasoning_quality or 0 for r in self.results) / total_tests
            if total_tests > 0
            else 0
        )
        avg_execution_time = (
            sum(r.execution_time for r in self.results) / total_tests
            if total_tests > 0
            else 0
        )

        # Function calling coverage
        function_calling_coverage = (
            (function_call_tests / total_tests * 100) if total_tests > 0 else 0
        )

        # Overall success rate
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        report = {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "function_calling_coverage": function_calling_coverage,
                "avg_reasoning_quality": avg_reasoning_quality,
                "avg_execution_time": avg_execution_time,
                "total_test_time": time.time() - self.start_time,
            },
            "categories": categories,
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "function_calls_detected": r.function_calls_detected,
                    "ai_reasoning_quality": r.ai_reasoning_quality,
                    "execution_time": r.execution_time,
                    "error_message": r.error_message,
                }
                for r in self.results
            ],
            "failed_tests": [
                {
                    "test_name": r.test_name,
                    "error_message": r.error_message,
                    "response_data": r.response_data,
                }
                for r in self.results
                if not r.success
            ],
        }

        return report

    def print_coverage_report(self, report: dict[str, Any]):
        """Print formatted coverage report."""
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE FUNCTION CALLING TEST REPORT")
        print("=" * 80)

        summary = report["summary"]
        print("📊 OVERALL RESULTS:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(
            f"   Successful: {summary['successful_tests']} ({summary['success_rate']:.1f}%)"
        )
        print(
            f"   Function Calling Coverage: {summary['function_calling_coverage']:.1f}%"
        )
        print(f"   Average Reasoning Quality: {summary['avg_reasoning_quality']:.1f}/5")
        print(f"   Average Execution Time: {summary['avg_execution_time']:.2f}s")
        print(f"   Total Test Time: {summary['total_test_time']:.2f}s")

        print("\n📈 CATEGORY BREAKDOWN:")
        for category, stats in report["categories"].items():
            success_rate = (
                (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            fc_rate = (
                (stats["function_calls"] / stats["total"] * 100)
                if stats["total"] > 0
                else 0
            )
            print(
                f"   {category.upper()}: {stats['success']}/{stats['total']} ({success_rate:.1f}%) - FC: {fc_rate:.1f}%"
            )

        if report["failed_tests"]:
            print(f"\n❌ FAILED TESTS ({len(report['failed_tests'])}):")
            for test in report["failed_tests"]:
                print(f"   - {test['test_name']}: {test['error_message']}")

        print("\n🎯 COVERAGE ASSESSMENT:")
        if summary["function_calling_coverage"] >= 90:
            print("   ✅ EXCELLENT - Function calling coverage exceeds 90%!")
        elif summary["function_calling_coverage"] >= 80:
            print("   ✅ GOOD - Function calling coverage above 80%")
        elif summary["function_calling_coverage"] >= 70:
            print("   ⚠️ FAIR - Function calling coverage needs improvement")
        else:
            print("   ❌ POOR - Function calling coverage below 70%")

        if summary["avg_reasoning_quality"] >= 4.0:
            print("   ✅ EXCELLENT - AI reasoning quality is high")
        elif summary["avg_reasoning_quality"] >= 3.0:
            print("   ✅ GOOD - AI reasoning quality is acceptable")
        else:
            print("   ⚠️ NEEDS IMPROVEMENT - AI reasoning quality is low")

    async def save_report(
        self,
        report: dict[str, Any],
        filename: str = "comprehensive_function_calling_report.json",
    ):
        """Save detailed report to file."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Report saved to: {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save report: {e}")


async def main():
    """Run comprehensive function calling tests."""
    tester = ComprehensiveFunctionCallingTester()

    try:
        # Run all tests
        report = await tester.run_all_tests()

        # Print results
        tester.print_coverage_report(report)

        # Save detailed report
        await tester.save_report(report)

        # Return success based on coverage
        function_calling_coverage = report["summary"]["function_calling_coverage"]
        success_rate = report["summary"]["success_rate"]

        if function_calling_coverage >= 90 and success_rate >= 80:
            print("\n🎉 SUCCESS: Function calling tests meet coverage requirements!")
            return True
        else:
            print(
                f"\n⚠️ COVERAGE INCOMPLETE: FC Coverage: {function_calling_coverage:.1f}% (need 90%), Success Rate: {success_rate:.1f}%"
            )
            return False

    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)

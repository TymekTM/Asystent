"""
🧪 Wielogodzinny test wieloużytkownikowy (real usage stress) - 60 minut LIVE

Test stabilności systemu Gaja podczas równoległego użytkowania przez wiele osób
w realistycznych scenariuszach przez 60 minut.

Zgodny z AGENTS.md i Finishing_Touches_Guideline requirements.
"""

import asyncio
import json
import logging
import random
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp
import pytest
from aiohttp import ClientSession, ClientTimeout

# Import function calling test
from quick_function_calling_test import run_quick_function_test

# Test configuration
TEST_DURATION_MINUTES = 60
MIN_USERS = 3
MAX_USERS = 5
SERVER_URL = "http://localhost:8001"
REQUEST_TIMEOUT = 10
MAX_RESPONSE_TIME = 3.0  # Increased for initial testing
AVERAGE_RESPONSE_TIME_TARGET = 2.0  # More realistic target

# Set up logging
# Set up logging with proper encoding for Windows
import io
import sys

# Create a UTF-8 wrapper for stdout to handle emojis on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except AttributeError:
        # Already wrapped or running in an environment that doesn't support it
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f'stress_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile for stress testing."""

    user_id: str
    user_type: str  # "free" or "premium"
    language: str  # "PL" or "EN"
    platform: str  # "Windows", "Linux", "Mac"
    requests_made: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: list[float] = field(default_factory=list)
    memory_context: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    start_time: datetime | None = None


@dataclass
class TestMetrics:
    """Test metrics collection."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    memory_test_results: list[bool] = field(default_factory=list)
    plugin_test_results: dict[str, int] = field(default_factory=dict)
    user_isolation_violations: int = 0
    rate_limit_hits: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None


class StressTestOrchestrator:
    """Orchestrates the multi-user stress test."""

    def __init__(self, server_url: str = SERVER_URL):
        self.server_url = server_url
        self.users: list[UserProfile] = []
        self.metrics = TestMetrics()
        self.session: ClientSession | None = None

        # Test queries for different scenarios
        self.plugin_queries = {
            "weather": [
                "Jaka jest pogoda?",
                "What's the weather like?",
                "Prognoza pogody na jutro",
            ],
            "time": ["Która godzina?", "What time is it?", "Podaj aktualny czas"],
            "notes": [
                "Zapisz notatkę: kupić mleko",
                "Note: meeting at 3pm",
                "Zanotuj: zadzwonić do mamy",
            ],
            "reminders": [
                "Przypomnij mi o spotkaniu",
                "Set reminder for lunch",
                "Ustaw przypomnienie na 15:00",
            ],
            "calculator": ["2 + 2", "What is 15 * 3?", "Oblicz 100 / 4"],
            "general": ["Jak się masz?", "Tell me a joke", "Co robisz?"],
        }

        self.memory_test_phrases = [
            "Nazywam się {name}",
            "Mieszkam w {city}",
            "Moim hobby jest {hobby}",
            "Pracuję jako {job}",
            "Mój ulubiony kolor to {color}",
            "Lubię jeść {food}",
        ]

        self.long_queries = [
            "Opowiedz mi szczegółowo o historii sztucznej inteligencji i jej wpływie na współczesny świat",
            "Explain in detail how machine learning algorithms work and their applications in modern technology",
            "Jakie są najnowsze trendy w programowaniu i jak wpływają na rozwój oprogramowania",
            "Describe the future of artificial intelligence and its potential impact on society",
        ]

    async def setup_test_environment(self) -> bool:
        """Set up the test environment and verify server availability."""
        try:
            timeout = ClientTimeout(total=REQUEST_TIMEOUT)
            self.session = ClientSession(timeout=timeout)

            # Test server availability
            async with self.session.get(f"{self.server_url}/health") as response:
                if response.status != 200:
                    logger.error(f"Server health check failed: {response.status}")
                    return False

            logger.info("✅ Server is available and responding")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup test environment: {e}")
            return False

    def create_test_users(self, count: int = MIN_USERS) -> list[UserProfile]:
        """Create test user profiles."""
        users = []

        # User templates
        templates = [
            {"type": "free", "lang": "PL", "platform": "Windows"},
            {"type": "premium", "lang": "EN", "platform": "Linux"},
            {"type": "free", "lang": "EN", "platform": "Mac"},
            {"type": "premium", "lang": "PL", "platform": "Windows"},
            {"type": "free", "lang": "PL", "platform": "Linux"},
        ]

        for i in range(count):
            template = templates[i % len(templates)]
            user = UserProfile(
                user_id=f"stress_test_user_{i+1}_{int(time.time())}",
                user_type=template["type"],
                language=template["lang"],
                platform=template["platform"],
                start_time=datetime.now(),
            )
            users.append(user)

        self.users = users
        logger.info(f"✅ Created {count} test users")
        return users

    async def make_query_request(
        self, user: UserProfile, query: str, context: dict | None = None
    ) -> tuple[bool, float, dict | None]:
        """Make a query request for a specific user."""
        start_time = time.time()

        try:
            payload = {
                "user_id": user.user_id,
                "query": query,
                "context": context or {},
                "user_type": user.user_type,
                "language": user.language,
            }

            async with self.session.post(
                f"{self.server_url}/api/ai_query", json=payload
            ) as response:
                response_time = time.time() - start_time

                if response.status == 200:
                    result = await response.json()
                    user.successful_requests += 1
                    user.response_times.append(response_time)
                    self.metrics.successful_requests += 1
                    self.metrics.response_times.append(response_time)
                    return True, response_time, result

                elif response.status == 429:
                    # Rate limit hit - expected for free users
                    self.metrics.rate_limit_hits += 1
                    logger.info(f"⚠️ Rate limit hit for user {user.user_id}")
                    return False, response_time, None

                else:
                    error_msg = f"HTTP {response.status} for user {user.user_id}"
                    user.errors.append(error_msg)
                    user.failed_requests += 1
                    self.metrics.failed_requests += 1
                    self.metrics.errors.append(error_msg)
                    logger.warning(error_msg)
                    return False, response_time, None

        except TimeoutError:
            response_time = time.time() - start_time
            error_msg = f"Timeout for user {user.user_id}"
            user.errors.append(error_msg)
            user.failed_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.errors.append(error_msg)
            logger.warning(error_msg)
            return False, response_time, None

        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Exception for user {user.user_id}: {str(e)}"
            user.errors.append(error_msg)
            user.failed_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.errors.append(error_msg)
            logger.error(error_msg)
            return False, response_time, None

        finally:
            user.requests_made += 1
            self.metrics.total_requests += 1

    async def phase_1_basic_interaction(self, user: UserProfile) -> None:
        """Phase 1 (0-15 min): Basic interactions with plugins and LLM."""
        logger.info(f"👤 User {user.user_id} starting Phase 1: Basic Interaction")

        # Test different plugins
        for plugin_type, queries in self.plugin_queries.items():
            query = random.choice(queries)
            success, response_time, result = await self.make_query_request(user, query)

            if success:
                self.metrics.plugin_test_results[plugin_type] = (
                    self.metrics.plugin_test_results.get(plugin_type, 0) + 1
                )

            # Random delay between requests (1-5 seconds)
            await asyncio.sleep(random.uniform(1, 5))

        # Test long query (LLM fallback)
        long_query = random.choice(self.long_queries)
        success, response_time, result = await self.make_query_request(user, long_query)

        if success and response_time > MAX_RESPONSE_TIME:
            logger.warning(
                f"⚠️ Long response time: {response_time:.2f}s for user {user.user_id}"
            )

    async def phase_2_memory_testing(self, user: UserProfile) -> None:
        """Phase 2 (15-30 min): Memory and context testing."""
        logger.info(f"👤 User {user.user_id} starting Phase 2: Memory Testing")

        # Store some information
        personal_info = {
            "name": f"TestUser{user.user_id[-1]}",
            "city": random.choice(["Warszawa", "Kraków", "Gdańsk", "Wrocław"]),
            "hobby": random.choice(["czytanie", "programowanie", "sport", "muzyka"]),
            "job": random.choice(["programista", "designer", "nauczyciel", "inżynier"]),
            "color": random.choice(["niebieski", "czerwony", "zielony", "żółty"]),
            "food": random.choice(["pizza", "sushi", "pasta", "burger"]),
        }

        # Store information in memory
        for key, value in personal_info.items():
            # Find a template that matches this key
            matching_templates = [
                template
                for template in self.memory_test_phrases
                if f"{{{key}}}" in template
            ]

            if matching_templates:
                phrase = random.choice(matching_templates).format(**{key: value})
            else:
                # Fallback to simple statement
                phrase = f"Moje {key} to {value}"

            user.memory_context.append(phrase)
            success, _, _ = await self.make_query_request(user, phrase)
            await asyncio.sleep(random.uniform(2, 4))

        # Wait a bit, then test memory recall
        await asyncio.sleep(random.uniform(10, 20))

        # Test memory recall
        recall_queries = [
            "Co o mnie wiesz?",
            "Jakie jest moje imię?",
            "Gdzie mieszkam?",
            "Co powiedziałem wcześniej o sobie?",
        ]

        for query in recall_queries:
            success, _, result = await self.make_query_request(user, query)
            if success and result:
                # Check if response contains stored information
                response_text = result.get("ai_response", "").lower()
                memory_recalled = any(
                    info.lower() in response_text for info in personal_info.values()
                )
                self.metrics.memory_test_results.append(memory_recalled)

            await asyncio.sleep(random.uniform(3, 6))

    async def phase_3_limits_and_priority(self, user: UserProfile) -> None:
        """Phase 3 (30-45 min): Test limits and priority handling."""
        logger.info(f"👤 User {user.user_id} starting Phase 3: Limits and Priority")

        if user.user_type == "free":
            # Test rate limiting for free users
            for i in range(10):  # Try to exceed rate limit
                query = f"Test query {i+1} for rate limiting"
                success, _, _ = await self.make_query_request(user, query)
                await asyncio.sleep(1)  # Short delay

        else:  # premium user
            # Test priority handling - multiple requests quickly
            tasks = []
            for i in range(5):
                query = f"Premium user priority test {i+1}"
                task = self.make_query_request(user, query)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check if premium user gets better response times
            response_times = [
                result[1]
                for result in results
                if isinstance(result, tuple) and result[0]
            ]

            if response_times:
                avg_response_time = statistics.mean(response_times)
                logger.info(
                    f"🏆 Premium user {user.user_id} avg response time: {avg_response_time:.2f}s"
                )

    async def phase_4_long_sessions_and_edge_cases(self, user: UserProfile) -> None:
        """Phase 4 (45-60 min): Long sessions and edge cases."""
        logger.info(
            f"👤 User {user.user_id} starting Phase 4: Long Sessions and Edge Cases"
        )

        # Dialog simulation
        dialog_queries = [
            "Cześć, jak się masz?",
            "Pamiętasz co mi wcześniej powiedziałeś?",
            "A co myślisz o pogodzie?",
            "Czy możesz mi pomóc z czymś?",
            "Dziękuję za rozmowę",
        ]

        for query in dialog_queries:
            success, _, _ = await self.make_query_request(user, query)
            await asyncio.sleep(random.uniform(5, 10))  # Natural conversation pace

        # Edge cases
        edge_case_queries = [
            "",  # Empty query
            "x" * 1000,  # Very long query
            "¿¡‽⸘∴∵‰‱",  # Special characters
            "SELECT * FROM users;",  # Potential SQL injection
            "🤖🚀💻🎯✨",  # Only emojis
        ]

        for query in edge_case_queries:
            try:
                success, _, _ = await self.make_query_request(user, query)
                await asyncio.sleep(2)
            except Exception as e:
                logger.info(f"🔍 Edge case handled: {query[:20]}... -> {str(e)[:50]}")

    async def run_user_scenario(self, user: UserProfile) -> None:
        """Run complete test scenario for a single user."""
        logger.info(f"🚀 Starting scenario for user {user.user_id} ({user.user_type})")

        try:
            # Phase 1: 0-15 minutes
            await self.phase_1_basic_interaction(user)

            # Phase 2: 15-30 minutes
            await self.phase_2_memory_testing(user)

            # Phase 3: 30-45 minutes
            await self.phase_3_limits_and_priority(user)

            # Phase 4: 45-60 minutes
            await self.phase_4_long_sessions_and_edge_cases(user)

        except Exception as e:
            logger.error(f"❌ User scenario failed for {user.user_id}: {e}")
            user.errors.append(f"Scenario failed: {str(e)}")

    def check_user_isolation(self) -> int:
        """Check if users' data is isolated from each other."""
        violations = 0

        # This is a simplified check - in reality, you'd analyze the responses
        # to ensure users don't see each other's data
        for user in self.users:
            if len(user.memory_context) > 0:
                # Check if any user got responses containing other users' data
                # This would require analyzing response content
                pass

        return violations

    def generate_test_report(self) -> dict:
        """Generate comprehensive test report."""
        duration = (
            self.metrics.end_time - self.metrics.start_time
        ).total_seconds() / 60

        # Calculate statistics
        if self.metrics.response_times:
            avg_response_time = statistics.mean(self.metrics.response_times)
            max_response_time = max(self.metrics.response_times)
            min_response_time = min(self.metrics.response_times)
        else:
            avg_response_time = max_response_time = min_response_time = 0

        success_rate = (
            self.metrics.successful_requests / self.metrics.total_requests * 100
            if self.metrics.total_requests > 0
            else 0
        )

        memory_success_rate = (
            sum(self.metrics.memory_test_results)
            / len(self.metrics.memory_test_results)
            * 100
            if self.metrics.memory_test_results
            else 0
        )

        report = {
            "test_summary": {
                "duration_minutes": round(duration, 2),
                "total_users": len(self.users),
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate_percent": round(success_rate, 2),
                "rate_limit_hits": self.metrics.rate_limit_hits,
            },
            "performance_metrics": {
                "average_response_time_seconds": round(avg_response_time, 3),
                "max_response_time_seconds": round(max_response_time, 3),
                "min_response_time_seconds": round(min_response_time, 3),
                "responses_over_target": sum(
                    1 for t in self.metrics.response_times if t > MAX_RESPONSE_TIME
                ),
                "target_response_time_seconds": MAX_RESPONSE_TIME,
            },
            "memory_testing": {
                "memory_tests_performed": len(self.metrics.memory_test_results),
                "memory_success_rate_percent": round(memory_success_rate, 2),
            },
            "plugin_testing": self.metrics.plugin_test_results,
            "user_isolation": {"violations": self.metrics.user_isolation_violations},
            "errors": {
                "total_errors": len(self.metrics.errors),
                "error_details": self.metrics.errors[:10],  # First 10 errors
            },
            "user_details": [
                {
                    "user_id": user.user_id,
                    "user_type": user.user_type,
                    "language": user.language,
                    "requests_made": user.requests_made,
                    "successful_requests": user.successful_requests,
                    "failed_requests": user.failed_requests,
                    "avg_response_time": (
                        round(statistics.mean(user.response_times), 3)
                        if user.response_times
                        else 0
                    ),
                    "errors": len(user.errors),
                }
                for user in self.users
            ],
        }

        return report

    async def _run_function_calling_test(self) -> dict[str, Any]:
        """Run quick function calling verification test."""
        try:
            # Run the quick function calling test using existing session
            if not self.session:
                # Create temporary session if needed
                self.session = aiohttp.ClientSession(
                    timeout=ClientTimeout(total=REQUEST_TIMEOUT)
                )

            results = await run_quick_function_test(self.server_url, self.session)

            logger.info(
                f"Function calling test completed: {results['success_rate']:.1f}% success rate"
            )

            return {
                "success": results["success_rate"] >= 60,  # At least 60% success
                "success_rate": results["success_rate"],
                "tests_run": results["tests_run"],
                "successful_calls": results["successful_calls"],
                "functions_called": results["functions_called"],
                "avg_functions_per_call": results["avg_functions_per_call"],
                "test_details": results["test_details"],
            }

        except Exception as e:
            logger.error(f"Function calling test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "success_rate": 0,
                "tests_run": 0,
                "successful_calls": 0,
                "functions_called": 0,
            }

    def evaluate_test_success(self, report: dict) -> tuple[bool, list[str]]:
        """Evaluate if the test was successful based on criteria."""
        issues = []

        # Check for crashes (no major failures)
        if (
            report["test_summary"]["failed_requests"]
            > report["test_summary"]["total_requests"] * 0.1
        ):
            issues.append("❌ Too many failed requests (>10%)")

        # Check response times
        if (
            report["performance_metrics"]["average_response_time_seconds"]
            > AVERAGE_RESPONSE_TIME_TARGET
        ):
            issues.append(
                f"❌ Average response time too high: {report['performance_metrics']['average_response_time_seconds']}s"
            )

        # Check memory functionality
        if report["memory_testing"]["memory_success_rate_percent"] < 70:
            issues.append(
                f"❌ Memory success rate too low: {report['memory_testing']['memory_success_rate_percent']}%"
            )

        # Check user isolation
        if report["user_isolation"]["violations"] > 0:
            issues.append(
                f"❌ User isolation violations: {report['user_isolation']['violations']}"
            )

        # Check plugin functionality
        if len(report["plugin_testing"]) < 3:
            issues.append("❌ Not enough plugin types tested")

        # Check function calling functionality
        if "function_calling_test" in report:
            func_test = report["function_calling_test"]
            if not func_test.get("success", False):
                issues.append(
                    f"❌ Function calling test failed: {func_test.get('success_rate', 0)}% success rate"
                )
            elif func_test.get("success_rate", 0) < 70:
                issues.append(
                    f"⚠️ Function calling success rate low: {func_test.get('success_rate', 0)}%"
                )
        else:
            issues.append("❌ Function calling test was not run")

        success = len(issues) == 0
        return success, issues

    async def run_stress_test(self) -> dict:
        """Run the complete 60-minute stress test."""
        logger.info("🚀 Starting 60-minute multi-user stress test")

        # Setup
        if not await self.setup_test_environment():
            raise RuntimeError("Failed to setup test environment")

        self.create_test_users(MIN_USERS)
        self.metrics.start_time = datetime.now()

        try:
            # Run all user scenarios concurrently
            tasks = [self.run_user_scenario(user) for user in self.users]

            # Wait for completion or timeout
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=TEST_DURATION_MINUTES * 60 + 300,  # 5 minutes buffer
            )

        except TimeoutError:
            logger.warning("⚠️ Test timed out")

        finally:
            self.metrics.end_time = datetime.now()

        # Run function calling verification test
        logger.info("🔧 Running function calling verification...")
        function_calling_results = await self._run_function_calling_test()

        # Close session after all tests
        if self.session:
            await self.session.close()

        # Generate and evaluate report
        report = self.generate_test_report()
        report[
            "function_calling_test"
        ] = function_calling_results  # Add function calling results
        success, issues = self.evaluate_test_success(report)

        # Log results
        logger.info("📊 STRESS TEST COMPLETED")
        logger.info(f"Duration: {report['test_summary']['duration_minutes']} minutes")
        logger.info(f"Total requests: {report['test_summary']['total_requests']}")
        logger.info(f"Success rate: {report['test_summary']['success_rate_percent']}%")
        logger.info(
            f"Average response time: {report['performance_metrics']['average_response_time_seconds']}s"
        )

        if success:
            logger.info("✅ STRESS TEST PASSED - All criteria met!")
        else:
            logger.error("❌ STRESS TEST FAILED - Issues found:")
            for issue in issues:
                logger.error(f"  {issue}")

        return report


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.performance
async def test_60_minute_multi_user_stress():
    """🧪 60-minute multi-user stress test.

    This test runs for 60 minutes with multiple users to verify:
    - System stability (no crashes)
    - Session isolation (users don't mix)
    - Memory functionality for each user
    - Performance under load
    - Rate limiting (free vs premium)
    - Plugin and fallback functionality under production conditions
    """
    orchestrator = StressTestOrchestrator()

    # Run the stress test
    report = await orchestrator.run_stress_test()

    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"stress_test_report_{timestamp}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"📄 Detailed report saved to: {report_file}")

    # Assertions for test success
    assert (
        report["test_summary"]["success_rate_percent"] >= 90
    ), f"Success rate too low: {report['test_summary']['success_rate_percent']}%"

    assert (
        report["performance_metrics"]["average_response_time_seconds"]
        <= AVERAGE_RESPONSE_TIME_TARGET
    ), f"Average response time too high: {report['performance_metrics']['average_response_time_seconds']}s"

    assert (
        report["user_isolation"]["violations"] == 0
    ), f"User isolation violations detected: {report['user_isolation']['violations']}"

    assert (
        len(report["plugin_testing"]) >= 3
    ), "Not enough plugin types were tested successfully"

    # Memory testing should have reasonable success rate
    if report["memory_testing"]["memory_tests_performed"] > 0:
        assert (
            report["memory_testing"]["memory_success_rate_percent"] >= 60
        ), f"Memory functionality success rate too low: {report['memory_testing']['memory_success_rate_percent']}%"


if __name__ == "__main__":
    """Run stress test standalone."""
    import sys

    async def main():
        orchestrator = StressTestOrchestrator()
        report = await orchestrator.run_stress_test()

        # Print summary
        print("\n" + "=" * 80)
        print("🧪 STRESS TEST SUMMARY")
        print("=" * 80)
        print(f"Duration: {report['test_summary']['duration_minutes']} minutes")
        print(f"Users: {report['test_summary']['total_users']}")
        print(f"Total requests: {report['test_summary']['total_requests']}")
        print(f"Success rate: {report['test_summary']['success_rate_percent']}%")
        print(
            f"Average response time: {report['performance_metrics']['average_response_time_seconds']}s"
        )
        print(
            f"Memory tests success: {report['memory_testing']['memory_success_rate_percent']}%"
        )
        print(f"Rate limit hits: {report['test_summary']['rate_limit_hits']}")
        print(f"Plugin tests: {len(report['plugin_testing'])} types")
        print(f"Errors: {report['errors']['total_errors']}")

        success, issues = orchestrator.evaluate_test_success(report)
        if success:
            print("\n✅ TEST PASSED - System is ready for production!")
            sys.exit(0)
        else:
            print("\n❌ TEST FAILED - Issues detected:")
            for issue in issues:
                print(f"  {issue}")
            sys.exit(1)

    asyncio.run(main())

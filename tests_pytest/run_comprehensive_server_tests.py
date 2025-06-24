"""
Server Testing Runner - Executes comprehensive server tests according to server_testing_todo.md
Following AGENTS.md guidelines for async testing and proper coverage.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import pytest
from loguru import logger


class ServerTestRunner:
    """Manages and executes comprehensive server testing suite."""

    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url
        self.test_results: dict[str, dict] = {}

    async def check_server_availability(self) -> bool:
        """Check if server is running and available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.server_url}/", timeout=5)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Server not available at {self.server_url}: {e}")
            return False

    def run_test_category(
        self, category: str, test_files: list[str], markers: list[str] = None
    ) -> dict:
        """Run a specific category of tests.

        Args:
            category: Name of test category
            test_files: List of test files to run
            markers: Optional pytest markers to filter tests

        Returns:
            Test results dictionary
        """
        logger.info(f"🧪 Running {category} tests...")

        # Build pytest command
        cmd_args = []

        # Add test files
        for test_file in test_files:
            if Path(test_file).exists():
                cmd_args.append(test_file)

        # Add markers if specified
        if markers:
            for marker in markers:
                cmd_args.extend(["-m", marker])

        # Add common options
        cmd_args.extend(
            [
                "-v",  # Verbose output
                "--tb=short",  # Short traceback
                "--strict-markers",  # Strict marker checking
                "--json-report",  # JSON report for parsing
                f"--json-report-file=test_results_{category.lower().replace(' ', '_')}.json",
            ]
        )

        # Run tests
        start_time = time.time()
        exit_code = pytest.main(cmd_args)
        end_time = time.time()

        # Parse results
        results = {
            "category": category,
            "exit_code": exit_code,
            "duration": end_time - start_time,
            "success": exit_code == 0,
            "files_tested": test_files,
        }

        # Try to read JSON report
        json_file = f"test_results_{category.lower().replace(' ', '_')}.json"
        if Path(json_file).exists():
            try:
                with open(json_file) as f:
                    json_data = json.load(f)
                    results.update(
                        {
                            "total_tests": json_data.get("summary", {}).get("total", 0),
                            "passed": json_data.get("summary", {}).get("passed", 0),
                            "failed": json_data.get("summary", {}).get("failed", 0),
                            "skipped": json_data.get("summary", {}).get("skipped", 0),
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not parse JSON report: {e}")

        self.test_results[category] = results

        if results["success"]:
            logger.success(f"✅ {category} tests completed successfully")
        else:
            logger.error(f"❌ {category} tests failed")

        return results

    def run_comprehensive_tests(self) -> dict[str, dict]:
        """Run all comprehensive server tests according to server_testing_todo.md."""

        logger.info("🚀 Starting comprehensive server testing suite")
        logger.info("Testing against server_testing_todo.md requirements")

        # Check server availability first
        if not self.check_server_availability():
            logger.error("❌ Server is not available - cannot run integration tests")
            return {"error": "Server not available"}

        logger.success(f"✅ Server is available at {self.server_url}")

        # Define test categories based on server_testing_todo.md
        test_categories = [
            {
                "name": "API and Client Communication",
                "files": ["test_server_comprehensive_implementation.py"],
                "markers": ["integration"],
                "description": "🌐 1. API i komunikacja z klientem",
            },
            {
                "name": "Intent Parser",
                "files": ["test_server_comprehensive_implementation.py"],
                "markers": ["integration"],
                "description": "🧠 2. Parser intencji",
            },
            {
                "name": "Query Routing",
                "files": ["test_server_comprehensive_implementation.py"],
                "markers": ["integration"],
                "description": "🔁 3. Routing zapytań",
            },
            {
                "name": "Plugins",
                "files": ["test_server_comprehensive_implementation.py"],
                "markers": ["integration"],
                "description": "🧩 4. Pluginy",
            },
            {
                "name": "Memory Management",
                "files": ["test_server_memory_sessions.py"],
                "markers": ["integration"],
                "description": "🧠 5. Pamięć (memory manager)",
            },
            {
                "name": "Habit Learning",
                "files": ["test_server_memory_sessions.py"],
                "markers": ["integration"],
                "description": "📚 6. Nauka nawyków",
            },
            {
                "name": "AI and LLM Fallback",
                "files": ["test_server_memory_sessions.py"],
                "markers": ["integration"],
                "description": "🧠 7. Model AI / LLM fallback",
            },
            {
                "name": "Session and User Logic",
                "files": ["test_server_memory_sessions.py"],
                "markers": ["integration"],
                "description": "📦 8. Logika sesji i użytkowników",
            },
            {
                "name": "Stability and Resilience",
                "files": ["test_server_comprehensive_implementation.py"],
                "markers": ["integration", "performance"],
                "description": "🧪 9. Stabilność i odporność",
            },
            {
                "name": "Debug Tools",
                "files": ["test_server_comprehensive_implementation.py"],
                "markers": ["integration"],
                "description": "🧰 10. Dev tools / debug",
            },
            {
                "name": "Free vs Paid Limits",
                "files": ["test_server_comprehensive_implementation.py"],
                "markers": ["integration", "security"],
                "description": "💳 11. Dostępy i limity (free vs. paid)",
            },
            {
                "name": "Extended Scenarios",
                "files": ["test_server_memory_sessions.py"],
                "markers": ["integration", "slow"],
                "description": "🧪 Scenariusze testowe dla serwera",
            },
        ]

        # Run each test category
        for category in test_categories:
            logger.info(f"\n{category['description']}")
            self.run_test_category(
                category["name"], category["files"], category.get("markers", [])
            )

        return self.test_results

    def generate_test_report(self) -> str:
        """Generate comprehensive test report."""

        if not self.test_results:
            return "No test results available"

        report_lines = [
            "# 🧪 Gaja Server Comprehensive Test Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Server URL: {self.server_url}",
            "",
            "## Test Summary",
            "",
        ]

        total_categories = len(self.test_results)
        successful_categories = sum(
            1 for r in self.test_results.values() if r.get("success", False)
        )

        report_lines.extend(
            [
                f"- **Total Test Categories**: {total_categories}",
                f"- **Successful Categories**: {successful_categories}",
                f"- **Failed Categories**: {total_categories - successful_categories}",
                f"- **Success Rate**: {(successful_categories/total_categories)*100:.1f}%",
                "",
            ]
        )

        # Detailed results per category
        report_lines.append("## Detailed Results")
        report_lines.append("")

        for category, results in self.test_results.items():
            status = "✅ PASSED" if results.get("success", False) else "❌ FAILED"
            report_lines.append(f"### {status} {category}")

            if "total_tests" in results:
                report_lines.extend(
                    [
                        f"- Total Tests: {results['total_tests']}",
                        f"- Passed: {results['passed']}",
                        f"- Failed: {results['failed']}",
                        f"- Skipped: {results['skipped']}",
                    ]
                )

            report_lines.extend(
                [
                    f"- Duration: {results['duration']:.2f} seconds",
                    f"- Exit Code: {results['exit_code']}",
                    "",
                ]
            )

        # Coverage analysis
        report_lines.extend(
            [
                "## Coverage Analysis",
                "",
                "Based on server_testing_todo.md requirements:",
                "",
            ]
        )

        requirements_map = {
            "API and Client Communication": "🌐 1. API i komunikacja z klientem",
            "Intent Parser": "🧠 2. Parser intencji",
            "Query Routing": "🔁 3. Routing zapytań",
            "Plugins": "🧩 4. Pluginy",
            "Memory Management": "🧠 5. Pamięć (memory manager)",
            "Habit Learning": "📚 6. Nauka nawyków",
            "AI and LLM Fallback": "🧠 7. Model AI / LLM fallback",
            "Session and User Logic": "📦 8. Logika sesji i użytkowników",
            "Stability and Resilience": "🧪 9. Stabilność i odporność",
            "Debug Tools": "🧰 10. Dev tools / debug",
            "Free vs Paid Limits": "💳 11. Dostępy i limity (free vs. paid)",
        }

        for category, description in requirements_map.items():
            status = (
                "✅"
                if self.test_results.get(category, {}).get("success", False)
                else "❌"
            )
            report_lines.append(f"- {status} {description}")

        report_lines.extend(["", "## Recommendations", ""])

        failed_categories = [
            cat
            for cat, res in self.test_results.items()
            if not res.get("success", False)
        ]
        if failed_categories:
            report_lines.append("### Failed Categories to Address:")
            for cat in failed_categories:
                report_lines.append(f"- {cat}")
            report_lines.append("")

        if successful_categories == total_categories:
            report_lines.append(
                "🎉 **All test categories passed! Server is ready for production.**"
            )
        else:
            report_lines.append(
                f"⚠️ **{len(failed_categories)} categories need attention before production.**"
            )

        return "\n".join(report_lines)

    def save_report(self, filename: str = "server_test_report.md"):
        """Save test report to file."""
        report = self.generate_test_report()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"📊 Test report saved to {filename}")
        return filename


async def main():
    """Main async function to run server tests."""

    # Initialize test runner
    runner = ServerTestRunner()

    # Run comprehensive tests
    logger.info("Starting Gaja Server Comprehensive Testing")
    results = runner.run_comprehensive_tests()

    if "error" in results:
        logger.error("Testing failed due to server unavailability")
        sys.exit(1)

    # Generate and save report
    report_file = runner.save_report()

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("🧪 GAJA SERVER TESTING COMPLETE")
    logger.info("=" * 60)

    total_categories = len(results)
    successful_categories = sum(1 for r in results.values() if r.get("success", False))

    logger.info("📊 Test Summary:")
    logger.info(f"   - Categories tested: {total_categories}")
    logger.info(f"   - Successful: {successful_categories}")
    logger.info(f"   - Failed: {total_categories - successful_categories}")
    logger.info(
        f"   - Success rate: {(successful_categories/total_categories)*100:.1f}%"
    )
    logger.info(f"📄 Full report: {report_file}")

    if successful_categories == total_categories:
        logger.success("🎉 All tests passed! Server is ready.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Check report for details.")
        sys.exit(1)


if __name__ == "__main__":
    # Change to tests directory
    import os

    os.chdir(Path(__file__).parent)

    # Run main function
    asyncio.run(main())

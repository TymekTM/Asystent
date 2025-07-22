"""🚀 Comprehensive Stress Test Runner with Monitoring.

Runs the 60-minute multi-user stress test with full system monitoring. Compliant with
AGENTS.md and Finishing_Touches_Guideline requirements.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import io

# Set up logging with proper encoding for Windows
import sys

from system_resource_monitor import run_monitoring_during_stress_test
from test_multi_user_stress_60min import StressTestOrchestrator

# Create a UTF-8 wrapper for stdout to handle emojis on Windows
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f'comprehensive_stress_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ComprehensiveStressTestRunner:
    """Runs comprehensive stress test with full monitoring."""

    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url
        self.start_time = None
        self.end_time = None

    async def verify_server_availability(self) -> bool:
        """Verify that the server is running and available."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        logger.info("✅ Server is available and ready")
                        return True
                    else:
                        logger.error(f"❌ Server returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to server: {e}")
            return False

    async def run_comprehensive_test(self) -> dict:
        """Run the complete comprehensive stress test."""
        logger.info("🚀 Starting Comprehensive 60-Minute Stress Test")
        logger.info("=" * 80)

        self.start_time = datetime.now()

        # Verify server is available
        if not await self.verify_server_availability():
            raise RuntimeError(
                "Server is not available. Please start the server first."
            )

        # Setup log files to monitor
        log_files = [
            "logs/server.log",
            "logs/gaja_server.log",
            "logs/client.log",
            "logs/error.log",
            "server_data.db.log",  # SQLite log if exists
        ]

        # Add Docker logs if available
        try:
            # Check if Docker is available
            process = await asyncio.create_subprocess_exec(
                "docker",
                "ps",
                "--format",
                "table {{.Names}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                containers = stdout.decode().strip().split("\n")[1:]  # Skip header
                for container in containers:
                    if "gaja" in container.lower():
                        logger.info(f"📦 Detected Docker container: {container}")

        except Exception:
            logger.info("🔍 Docker not available or no containers running")

        # Start monitoring and stress test concurrently
        logger.info("🔍 Starting system monitoring...")
        logger.info("👥 Starting multi-user stress test...")

        # Create tasks for parallel execution
        monitoring_task = asyncio.create_task(
            run_monitoring_during_stress_test(
                test_duration_minutes=60, resource_interval=5.0, log_files=log_files
            )
        )

        stress_test_task = asyncio.create_task(self._run_stress_test())

        try:
            # Wait for both tasks to complete
            monitoring_report, stress_test_report = await asyncio.gather(
                monitoring_task, stress_test_task, return_exceptions=True
            )

            # Handle exceptions
            if isinstance(monitoring_report, Exception):
                logger.error(f"❌ Monitoring failed: {monitoring_report}")
                monitoring_report = {"error": str(monitoring_report)}

            if isinstance(stress_test_report, Exception):
                logger.error(f"❌ Stress test failed: {stress_test_report}")
                stress_test_report = {"error": str(stress_test_report)}

        except Exception as e:
            logger.error(f"❌ Comprehensive test failed: {e}")
            monitoring_report = {"error": "Test interrupted"}
            stress_test_report = {"error": str(e)}

        self.end_time = datetime.now()

        # Combine reports
        combined_report = self._combine_reports(monitoring_report, stress_test_report)

        # Save comprehensive report
        report_file = self._save_comprehensive_report(combined_report)

        # Log final results
        self._log_final_results(combined_report)

        return combined_report

    async def _run_stress_test(self) -> dict:
        """Run the stress test component."""
        orchestrator = StressTestOrchestrator(self.server_url)
        return await orchestrator.run_stress_test()

    def _combine_reports(
        self, monitoring_report: dict, stress_test_report: dict
    ) -> dict:
        """Combine monitoring and stress test reports."""
        duration = (self.end_time - self.start_time).total_seconds() / 60

        combined = {
            "test_metadata": {
                "test_type": "comprehensive_60_minute_stress_test",
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_minutes": round(duration, 2),
                "server_url": self.server_url,
            },
            "stress_test_results": stress_test_report,
            "monitoring_results": monitoring_report,
            "combined_analysis": self._analyze_combined_results(
                monitoring_report, stress_test_report
            ),
        }

        return combined

    def _analyze_combined_results(
        self, monitoring_report: dict, stress_test_report: dict
    ) -> dict:
        """Analyze combined results to provide insights."""
        analysis = {
            "overall_status": "unknown",
            "critical_issues": [],
            "warnings": [],
            "performance_summary": {},
            "recommendations": [],
        }

        # Check for critical issues
        if isinstance(stress_test_report, dict) and "error" not in stress_test_report:
            stress_summary = stress_test_report.get("test_summary", {})
            performance = stress_test_report.get("performance_metrics", {})

            # Performance analysis
            success_rate = stress_summary.get("success_rate_percent", 0)
            avg_response_time = performance.get("average_response_time_seconds", 0)

            if success_rate < 90:
                analysis["critical_issues"].append(f"Low success rate: {success_rate}%")
            elif success_rate < 95:
                analysis["warnings"].append(
                    f"Success rate could be better: {success_rate}%"
                )

            if avg_response_time > 3.0:
                analysis["critical_issues"].append(
                    f"High response time: {avg_response_time}s"
                )
            elif avg_response_time > 2.0:
                analysis["warnings"].append(
                    f"Response time above target: {avg_response_time}s"
                )

        # Resource usage analysis
        if isinstance(monitoring_report, dict) and "error" not in monitoring_report:
            resource_usage = monitoring_report.get("resource_usage", {})
            cpu_usage = resource_usage.get("cpu_usage", {})
            memory_usage = resource_usage.get("memory_usage", {})

            cpu_max = cpu_usage.get("maximum", 0)
            memory_max = memory_usage.get("maximum", 0)

            if cpu_max > 90:
                analysis["critical_issues"].append(f"Very high CPU usage: {cpu_max}%")
            elif cpu_max > 80:
                analysis["warnings"].append(f"High CPU usage: {cpu_max}%")

            if memory_max > 90:
                analysis["critical_issues"].append(
                    f"Very high memory usage: {memory_max}%"
                )
            elif memory_max > 80:
                analysis["warnings"].append(f"High memory usage: {memory_max}%")

        # Function calling analysis
        if (
            isinstance(stress_test_report, dict)
            and "function_calling_test" in stress_test_report
        ):
            func_test = stress_test_report["function_calling_test"]
            func_success_rate = func_test.get("success_rate", 0)

            if func_success_rate < 60:
                analysis["critical_issues"].append(
                    f"Function calling failed: {func_success_rate}% success rate"
                )
            elif func_success_rate < 80:
                analysis["warnings"].append(
                    f"Function calling success rate low: {func_success_rate}%"
                )

        # Overall status determination
        if analysis["critical_issues"]:
            analysis["overall_status"] = "failed"
            analysis["recommendations"].append(
                "Address critical issues before production deployment"
            )
        elif analysis["warnings"]:
            analysis["overall_status"] = "warning"
            analysis["recommendations"].append(
                "Consider optimizations to improve performance"
            )
        else:
            analysis["overall_status"] = "passed"
            analysis["recommendations"].append(
                "System is ready for production deployment"
            )

        return analysis

    def _save_comprehensive_report(self, report: dict) -> str:
        """Save the comprehensive report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_stress_test_report_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"📄 Comprehensive report saved to: {filename}")
        return filename

    def _log_final_results(self, report: dict) -> None:
        """Log the final test results."""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 COMPREHENSIVE STRESS TEST RESULTS")
        logger.info("=" * 80)

        # Test metadata
        metadata = report.get("test_metadata", {})
        logger.info(f"Duration: {metadata.get('duration_minutes', 0)} minutes")
        logger.info(f"Server: {metadata.get('server_url', 'unknown')}")

        # Stress test results
        stress_results = report.get("stress_test_results", {})
        if "error" not in stress_results:
            test_summary = stress_results.get("test_summary", {})
            performance = stress_results.get("performance_metrics", {})

            logger.info(f"Total Users: {test_summary.get('total_users', 0)}")
            logger.info(f"Total Requests: {test_summary.get('total_requests', 0)}")
            logger.info(f"Success Rate: {test_summary.get('success_rate_percent', 0)}%")
            logger.info(
                f"Average Response Time: {performance.get('average_response_time_seconds', 0):.3f}s"
            )
            logger.info(f"Rate Limit Hits: {test_summary.get('rate_limit_hits', 0)}")

        # Monitoring results
        monitoring_results = report.get("monitoring_results", {})
        if "error" not in monitoring_results:
            resource_usage = monitoring_results.get("resource_usage", {})
            cpu_usage = resource_usage.get("cpu_usage", {})
            memory_usage = resource_usage.get("memory_usage", {})

            logger.info(f"Peak CPU: {cpu_usage.get('maximum', 0):.1f}%")
            logger.info(f"Peak Memory: {memory_usage.get('maximum', 0):.1f}%")
            logger.info(
                f"Peak Memory Usage: {resource_usage.get('peak_memory_gb', 0):.2f} GB"
            )

        # Function calling results
        stress_results = report.get("stress_test_results", {})
        if "function_calling_test" in stress_results:
            func_test = stress_results["function_calling_test"]
            logger.info(
                f"Function Calling Success Rate: {func_test.get('success_rate', 0):.1f}%"
            )
            logger.info(f"Function Calls Made: {func_test.get('functions_called', 0)}")

        # Combined analysis
        analysis = report.get("combined_analysis", {})
        status = analysis.get("overall_status", "unknown")

        if status == "passed":
            logger.info("✅ OVERALL STATUS: PASSED - System ready for production!")
        elif status == "warning":
            logger.info("⚠️ OVERALL STATUS: WARNING - Some issues detected")
        elif status == "failed":
            logger.info("❌ OVERALL STATUS: FAILED - Critical issues found")
        else:
            logger.info("❓ OVERALL STATUS: UNKNOWN - Check detailed report")

        # Issues and recommendations
        critical_issues = analysis.get("critical_issues", [])
        warnings = analysis.get("warnings", [])
        recommendations = analysis.get("recommendations", [])

        if critical_issues:
            logger.info("\n🚨 CRITICAL ISSUES:")
            for issue in critical_issues:
                logger.info(f"  • {issue}")

        if warnings:
            logger.info("\n⚠️ WARNINGS:")
            for warning in warnings:
                logger.info(f"  • {warning}")

        if recommendations:
            logger.info("\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                logger.info(f"  • {rec}")

        logger.info("=" * 80)


async def main():
    """Main entry point for comprehensive stress test."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run comprehensive 60-minute stress test"
    )
    parser.add_argument(
        "--server-url",
        default="http://localhost:8001",
        help="Server URL to test (default: http://localhost:8001)",
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run a quick 5-minute test instead of full 60-minute test",
    )

    args = parser.parse_args()

    # Modify test duration if quick test requested
    if args.quick_test:
        logger.info("🚀 Running QUICK TEST (5 minutes)")
        # Monkey patch the test duration
        import test_multi_user_stress_60min

        test_multi_user_stress_60min.TEST_DURATION_MINUTES = 5

        import system_resource_monitor

        original_run_monitoring = (
            system_resource_monitor.run_monitoring_during_stress_test
        )

        async def quick_monitoring(*args, **kwargs):
            kwargs["test_duration_minutes"] = 5
            return await original_run_monitoring(*args, **kwargs)

        system_resource_monitor.run_monitoring_during_stress_test = quick_monitoring

    # Run the comprehensive test
    runner = ComprehensiveStressTestRunner(server_url=args.server_url)

    try:
        report = await runner.run_comprehensive_test()

        # Exit with appropriate code
        analysis = report.get("combined_analysis", {})
        status = analysis.get("overall_status", "unknown")

        if status == "passed":
            sys.exit(0)
        elif status == "warning":
            sys.exit(1)
        else:  # failed or unknown
            sys.exit(2)

    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

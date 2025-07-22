"""⚡ Quick Function Calling Test.

A streamlined version of function calling tests for integration with stress tests. Tests
essential function calling capabilities quickly and efficiently.
"""

import asyncio
import logging
import uuid
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class QuickFunctionCallingTest:
    """Quick function calling test for integration with other test suites."""

    def __init__(
        self,
        server_url: str = "http://localhost:8001",
        session: aiohttp.ClientSession | None = None,
    ):
        self.server_url = server_url
        self.session = session
        self.owns_session = session is None
        self.test_user_id = f"quick_func_test_{uuid.uuid4().hex[:8]}"

    async def __aenter__(self):
        """Async context manager entry."""
        if self.owns_session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.owns_session and self.session:
            await self.session.close()

    async def _make_quick_request(self, message: str) -> dict[str, Any]:
        """Make a quick request and return simplified result."""
        try:
            payload = {"user_id": self.test_user_id, "query": message, "context": {}}

            async with self.session.post(
                f"{self.server_url}/api/ai_query",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10.0),  # Quick timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Check if function_calls is present and populated
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
                        "has_function_calls": has_function_calls,
                        "function_calls": function_calls_list,
                        "has_ai_response": has_ai_response,
                        "ai_response": ai_response,
                    }
                else:
                    return {
                        "success": False,
                        "has_function_calls": False,
                        "function_calls": [],
                        "has_ai_response": False,
                        "ai_response": "",
                    }

        except Exception:
            return {
                "success": False,
                "has_function_calls": False,
                "function_calls": [],
                "has_ai_response": False,
                "ai_response": "",
            }

    async def test_essential_functions(self) -> dict[str, Any]:
        """Test essential function calling capabilities quickly."""
        logger.info("⚡ Running quick function calling tests...")

        # Essential test cases - designed to be fast
        tests = [
            ("time", "Jaka jest aktualna godzina?"),
            ("task", "Dodaj zadanie: Test funkcji"),
            ("weather", "Jaka jest pogoda w Warszawie?"),
            ("search", "Wyszukaj informacje o AI"),
            ("memory", "Zapamiętaj że lubię kawę"),
        ]

        results = {
            "tests_run": len(tests),
            "successful_calls": 0,
            "functions_called": 0,
            "test_details": {},
        }

        # Run tests with minimal delay
        for test_name, message in tests:
            response = await self._make_quick_request(message)

            # Success if either function was called OR we got a reasonable AI response
            success = response["success"] and (
                response["has_function_calls"] or response["has_ai_response"]
            )
            function_count = len(response["function_calls"])

            if success:
                results["successful_calls"] += 1

            results["functions_called"] += function_count
            results["test_details"][test_name] = {
                "success": success,
                "function_count": function_count,
                "has_function_calls": response["has_function_calls"],
                "has_ai_response": response["has_ai_response"],
            }

            # Small delay to avoid overwhelming the server
            await asyncio.sleep(0.1)

        # Calculate success rate
        results["success_rate"] = (
            (results["successful_calls"] / results["tests_run"] * 100)
            if results["tests_run"] > 0
            else 0
        )
        results["avg_functions_per_call"] = (
            (results["functions_called"] / results["tests_run"])
            if results["tests_run"] > 0
            else 0
        )

        logger.info(f"  Function calling success rate: {results['success_rate']:.1f}%")
        logger.info(f"  Total functions called: {results['functions_called']}")

        return results


async def run_quick_function_test(
    server_url: str = "http://localhost:8001",
    session: aiohttp.ClientSession | None = None,
) -> dict[str, Any]:
    """Run quick function calling test - can be called from other test suites."""
    if session:
        # Use provided session
        test = QuickFunctionCallingTest(server_url, session)
        return await test.test_essential_functions()
    else:
        # Create own session
        async with QuickFunctionCallingTest(server_url) as test:
            return await test.test_essential_functions()


if __name__ == "__main__":

    async def main():
        async with QuickFunctionCallingTest() as test:
            results = await test.test_essential_functions()
            print(f"Quick function calling test results: {results}")
            return 0 if results["success_rate"] >= 60 else 1

    import sys

    sys.exit(asyncio.run(main()))

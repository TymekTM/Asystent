"""Test configuration and utilities for comprehensive server testing.

Provides fixtures and helper functions for server testing.
"""

import asyncio
import os
from typing import Any

import pytest
from aiohttp import ClientSession, ClientTimeout

# Test configuration constants
TEST_SERVER_URL = os.getenv("TEST_SERVER_URL", "http://localhost:8001")
TEST_TIMEOUT = 30
DEFAULT_REQUEST_TIMEOUT = 5


@pytest.fixture
def server_url():
    """Fixture providing server URL."""
    return TEST_SERVER_URL


@pytest.fixture
async def http_session():
    """Fixture providing HTTP session with proper timeout."""
    timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
    async with ClientSession(timeout=timeout) as session:
        yield session


@pytest.fixture
def test_user_id():
    """Fixture providing test user ID."""
    return "test_user_comprehensive"


@pytest.fixture
def premium_user_id():
    """Fixture providing premium user ID."""
    return "premium_user_comprehensive"


class ServerTestHelper:
    """Helper class for server testing utilities."""

    def __init__(self, server_url: str = TEST_SERVER_URL):
        self.server_url = server_url

    async def make_query_request(
        self,
        session: ClientSession,
        user_id: str,
        query: str,
        context: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Make a query request to the server.

        Args:
            session: HTTP session
            user_id: User ID for the request
            query: Query string
            context: Optional context dictionary

        Returns:
            Response data as dictionary

        Raises:
            AssertionError: If request fails
        """
        if context is None:
            context = {}

        payload = {"user_id": user_id, "query": query, "context": context}

        async with session.post(
            f"{self.server_url}/api/ai_query", json=payload
        ) as response:
            assert (
                response.status == 200
            ), f"Request failed with status {response.status}"
            return await response.json()

    async def check_server_health(self, session: ClientSession) -> bool:
        """Check if server is healthy and responding.

        Args:
            session: HTTP session

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            # Try multiple potential health endpoints
            health_endpoints = ["/health", "/ping", "/"]

            for endpoint in health_endpoints:
                try:
                    async with session.get(f"{self.server_url}{endpoint}") as response:
                        if response.status == 200:
                            return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    async def measure_response_time(
        self, session: ClientSession, user_id: str, query: str
    ) -> tuple[float, dict[str, Any]]:
        """Measure response time for a query.

        Args:
            session: HTTP session
            user_id: User ID
            query: Query string

        Returns:
            Tuple of (response_time_seconds, response_data)
        """
        import time

        start_time = time.time()
        response_data = await self.make_query_request(session, user_id, query)
        end_time = time.time()

        return end_time - start_time, response_data

    async def make_concurrent_requests(
        self,
        session: ClientSession,
        requests: list[dict[str, Any]],
        max_concurrent: int = 10,
    ) -> list[dict[str, Any]]:
        """Make multiple concurrent requests with concurrency limit.

        Args:
            session: HTTP session
            requests: List of request dictionaries with 'user_id', 'query', 'context'
            max_concurrent: Maximum concurrent requests

        Returns:
            List of response data dictionaries
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_request(request_data):
            async with semaphore:
                return await self.make_query_request(
                    session,
                    request_data["user_id"],
                    request_data["query"],
                    request_data.get("context", {}),
                )

        tasks = [limited_request(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)


@pytest.fixture
def server_helper(server_url):
    """Fixture providing server test helper."""
    return ServerTestHelper(server_url)


# Test data fixtures
@pytest.fixture
def sample_queries():
    """Fixture providing sample queries for testing."""
    return [
        "Jaka jest pogoda?",
        "What's the weather like?",
        "Zapisz notatkę: kupić mleko",
        "Set a reminder for meeting",
        "Zrób coś",  # Ambiguous
        "Random text xyz123",  # Unknown intent
        "🎉 Emoji test query",
        "",  # Empty query
    ]


@pytest.fixture
def multilingual_queries():
    """Fixture providing multilingual test queries."""
    return [
        ("Jaka jest pogoda?", "pl"),
        ("What's the weather?", "en"),
        ("Jak się masz?", "pl"),
        ("How are you?", "en"),
        ("Zapisz notatkę", "pl"),
        ("Save a note", "en"),
    ]


@pytest.fixture
def stress_test_queries():
    """Fixture providing queries for stress testing."""
    return [
        "a" * 1000,  # Very long query
        "🎉" * 100,  # Many emojis
        "test\n\r\t" * 50,  # Special characters
        "SELECT * FROM users;",  # Potential SQL injection
        "<script>alert('xss')</script>",  # Potential XSS
        "../../etc/passwd",  # Path traversal attempt
    ]


# Performance benchmarks
PERFORMANCE_THRESHOLDS = {
    "plugin_response_time": 0.5,  # seconds
    "llm_response_time": 2.0,  # seconds
    "concurrent_requests": 50,  # number of requests
    "success_rate_threshold": 0.8,  # 80% success rate
}


@pytest.fixture
def performance_thresholds():
    """Fixture providing performance thresholds."""
    return PERFORMANCE_THRESHOLDS


# Test markers for categorizing tests
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests that require running server"
    )
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line("markers", "stress: Stress tests with high load")
    config.addinivalue_line("markers", "security: Security-related tests")
    config.addinivalue_line("markers", "slow: Slow tests that take more than 5 seconds")


# Skip tests if server is not available
def pytest_collection_modifyitems(config, items):
    """Skip integration tests if server is not available."""
    skip_integration = pytest.mark.skip(reason="Server not available")

    for item in items:
        if "integration" in item.keywords:
            # Check if server is available
            try:
                import requests

                response = requests.get(TEST_SERVER_URL, timeout=2)
                if response.status_code != 200:
                    item.add_marker(skip_integration)
            except Exception:
                item.add_marker(skip_integration)

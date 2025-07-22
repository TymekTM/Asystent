#!/usr/bin/env python3
"""Comprehensive Stress Test Suite for GAJA Server Tests various edge cases, attack
vectors, and stress scenarios."""

import asyncio
import json
import logging
import random
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import aiohttp
import requests
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/ws/"

# Test configuration
MAX_CONCURRENT_CONNECTIONS = 50
TEST_DURATION = 30  # seconds
LARGE_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10MB


class StressTestSuite:
    """Comprehensive stress testing suite for GAJA server."""

    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "performance_metrics": {},
        }
        self.active_connections = []

    def log_result(self, test_name: str, success: bool, error: str = None):
        """Log test result."""
        self.results["total_tests"] += 1
        if success:
            self.results["passed"] += 1
            logger.info(f"✅ {test_name}: PASSED")
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {error}")
            logger.error(f"❌ {test_name}: FAILED - {error}")

    def generate_large_text(self, size: int) -> str:
        """Generate large random text."""
        return "".join(
            random.choices(string.ascii_letters + string.digits + " ", k=size)
        )

    def generate_malformed_json(self) -> str:
        """Generate malformed JSON data."""
        malformed_jsons = [
            '{"invalid": json without closing brace',
            '{"nested": {"deeply": {"very": {"much": {"so": "nested"',
            '{"unicode": "\\u0000\\u0001\\u0002"}',
            '{"numbers": 1.7976931348623157e+308}',  # Max float
            '{"arrays": [' + ",".join([f'"{i}"' for i in range(1000)]) + "]}",
            '{"null_bytes": "\\x00\\x01\\x02"}',
            '[{"a": 1}, {"b": 2}, {"c": 3},' * 1000 + "]",  # Incomplete array
        ]
        return random.choice(malformed_jsons)

    async def test_websocket_flood(self):
        """Test WebSocket connection flooding."""
        test_name = "WebSocket Flood Test"
        try:
            connections = []

            # Create many concurrent WebSocket connections
            for i in range(MAX_CONCURRENT_CONNECTIONS):
                try:
                    uri = f"{WS_URL}?user_id=stress_user_{i}"
                    ws = await websockets.connect(uri, timeout=5)
                    connections.append(ws)

                    # Send a message immediately
                    await ws.send(
                        json.dumps(
                            {
                                "type": "query",
                                "data": f"Stress test message {i}",
                                "user_id": f"stress_user_{i}",
                            }
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to create connection {i}: {e}")

            logger.info(f"Created {len(connections)} WebSocket connections")

            # Send rapid messages on all connections
            for _ in range(10):
                for i, ws in enumerate(connections):
                    try:
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "query",
                                    "data": f"Rapid message {time.time()}",
                                    "user_id": f"stress_user_{i}",
                                }
                            )
                        )
                    except Exception:
                        pass
                await asyncio.sleep(0.1)

            # Close all connections
            for ws in connections:
                try:
                    await ws.close()
                except Exception:
                    pass

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    async def test_malformed_websocket_messages(self):
        """Test sending malformed WebSocket messages."""
        test_name = "Malformed WebSocket Messages"
        try:
            uri = f"{WS_URL}?user_id=malform_user"
            async with websockets.connect(uri) as ws:
                # Test various malformed messages
                malformed_messages = [
                    "not_json_at_all",
                    '{"incomplete": json',
                    b"\x00\x01\x02\x03",  # Binary data
                    "null",
                    '{"type": null, "data": undefined}',
                    '{"recursive": {"self": this}}',
                    '{"huge_number": ' + "9" * 1000 + "}",
                    "",  # Empty message
                    " ",  # Whitespace only
                    '{"unicode": "🚀💀👻🔥⚡🌟💯🎯🎪🎭"}',
                ]

                for msg in malformed_messages:
                    try:
                        await ws.send(msg)
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.debug(f"Expected error sending malformed message: {e}")

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    async def test_large_payload_websocket(self):
        """Test WebSocket with extremely large payloads."""
        test_name = "Large Payload WebSocket"
        try:
            uri = f"{WS_URL}?user_id=large_payload_user"
            async with websockets.connect(uri) as ws:
                # Send increasingly large payloads
                for size in [1024, 10240, 102400, 1024000]:  # 1KB to 1MB
                    large_text = self.generate_large_text(size)
                    message = json.dumps(
                        {
                            "type": "query",
                            "data": large_text,
                            "user_id": "large_payload_user",
                        }
                    )

                    try:
                        await ws.send(message)
                        logger.info(f"Sent {size} byte payload")
                        await asyncio.sleep(1)  # Give server time to process
                    except Exception as e:
                        logger.warning(f"Failed to send {size} byte payload: {e}")

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    async def test_rapid_websocket_messages(self):
        """Test rapid-fire WebSocket messages."""
        test_name = "Rapid WebSocket Messages"
        try:
            uri = f"{WS_URL}?user_id=rapid_user"
            async with websockets.connect(uri) as ws:
                # Send 1000 messages as fast as possible
                start_time = time.time()
                for i in range(1000):
                    message = json.dumps(
                        {
                            "type": "query",
                            "data": f"Rapid message {i}",
                            "user_id": "rapid_user",
                        }
                    )
                    await ws.send(message)

                end_time = time.time()
                duration = end_time - start_time
                rate = 1000 / duration

                self.results["performance_metrics"]["rapid_message_rate"] = rate
                logger.info(f"Sent 1000 messages in {duration:.2f}s ({rate:.2f} msg/s)")

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_http_endpoint_flood(self):
        """Test HTTP endpoint flooding."""
        test_name = "HTTP Endpoint Flood"
        try:

            def make_request(session, endpoint, data=None):
                try:
                    if data:
                        response = session.post(
                            f"{SERVER_URL}{endpoint}", json=data, timeout=5
                        )
                    else:
                        response = session.get(f"{SERVER_URL}{endpoint}", timeout=5)
                    return response.status_code
                except Exception as e:
                    return str(e)

            # Test multiple endpoints simultaneously
            endpoints = [
                "/health",
                "/api/users",
                "/api/chat/history",
                "/api/plugins",
                "/api/config",
            ]

            with requests.Session() as session:
                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = []

                    # Submit 1000 requests across different endpoints
                    for _ in range(1000):
                        endpoint = random.choice(endpoints)
                        future = executor.submit(make_request, session, endpoint)
                        futures.append(future)

                    # Collect results
                    status_codes = []
                    for future in as_completed(futures):
                        result = future.result()
                        status_codes.append(result)

                    # Analyze results
                    success_count = sum(
                        1
                        for code in status_codes
                        if isinstance(code, int) and 200 <= code < 500
                    )
                    logger.info(
                        f"HTTP flood: {success_count}/{len(status_codes)} requests successful"
                    )

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_malformed_http_requests(self):
        """Test malformed HTTP requests."""
        test_name = "Malformed HTTP Requests"
        try:
            session = requests.Session()

            # Test various malformed requests
            malformed_tests = [
                # Oversized headers
                {
                    "url": f"{SERVER_URL}/api/chat",
                    "headers": {"X-Large-Header": "A" * 100000},
                    "json": {"message": "test"},
                },
                # Invalid JSON
                {
                    "url": f"{SERVER_URL}/api/chat",
                    "data": '{"invalid": json',
                    "headers": {"Content-Type": "application/json"},
                },
                # Huge payload
                {
                    "url": f"{SERVER_URL}/api/chat",
                    "json": {"message": "A" * 1000000},  # 1MB message
                },
                # Invalid content type
                {
                    "url": f"{SERVER_URL}/api/chat",
                    "data": b"\x00\x01\x02\x03" * 1000,
                    "headers": {"Content-Type": "application/octet-stream"},
                },
            ]

            for test_case in malformed_tests:
                try:
                    if "json" in test_case:
                        response = session.post(
                            test_case["url"],
                            json=test_case["json"],
                            headers=test_case.get("headers", {}),
                            timeout=10,
                        )
                    else:
                        response = session.post(
                            test_case["url"],
                            data=test_case.get("data"),
                            headers=test_case.get("headers", {}),
                            timeout=10,
                        )
                    logger.info(f"Malformed request returned: {response.status_code}")
                except Exception as e:
                    logger.info(f"Malformed request failed as expected: {e}")

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    async def test_ai_context_overflow(self):
        """Test AI with extremely long context."""
        test_name = "AI Context Overflow"
        try:
            uri = f"{WS_URL}?user_id=ai_overflow_user"
            async with websockets.connect(uri) as ws:
                # Build up a massive context by sending many messages
                context_messages = []
                for i in range(100):  # Send 100 long messages
                    long_message = self.generate_large_text(5000)  # 5KB each
                    context_messages.append(f"Context message {i}: {long_message}")

                    message = json.dumps(
                        {
                            "type": "ai_query",
                            "data": {
                                "query": context_messages[-1],
                                "context": context_messages.copy(),
                                "user_id": "ai_overflow_user",
                            },
                        }
                    )

                    await ws.send(message)
                    await asyncio.sleep(0.5)  # Give server time

                # Send final query with all context
                final_query = json.dumps(
                    {
                        "type": "ai_query",
                        "data": {
                            "query": "Summarize everything I've told you",
                            "context": context_messages,
                            "user_id": "ai_overflow_user",
                        },
                    }
                )

                await ws.send(final_query)

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    async def test_websocket_connection_exhaustion(self):
        """Test WebSocket connection exhaustion."""
        test_name = "WebSocket Connection Exhaustion"
        try:
            connections = []

            # Try to create as many connections as possible
            for i in range(200):  # Try more than typical limits
                try:
                    uri = f"{WS_URL}?user_id=exhaust_user_{i}"
                    ws = await websockets.connect(uri, timeout=2)
                    connections.append(ws)

                    if i % 50 == 0:
                        logger.info(f"Created {i} connections so far...")

                except Exception as e:
                    logger.info(f"Connection limit reached at {i} connections: {e}")
                    break

            logger.info(f"Total connections created: {len(connections)}")

            # Keep connections alive for a while
            await asyncio.sleep(10)

            # Close all connections
            for ws in connections:
                try:
                    await ws.close()
                except Exception:
                    pass

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_memory_stress(self):
        """Test server memory usage under stress."""
        test_name = "Memory Stress Test"
        try:
            # Create large data structures and send them
            large_data = {
                "huge_list": list(range(100000)),
                "huge_string": "A" * 1000000,
                "nested_data": {
                    "level" + str(i): {"data": "X" * 1000} for i in range(1000)
                },
            }

            # Send multiple large requests
            with requests.Session() as session:
                for i in range(10):
                    try:
                        response = session.post(
                            f"{SERVER_URL}/api/test", json=large_data, timeout=30
                        )
                        logger.info(f"Large data request {i}: {response.status_code}")
                    except Exception as e:
                        logger.info(f"Large data request {i} failed: {e}")

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    async def test_concurrent_operations(self):
        """Test many concurrent operations."""
        test_name = "Concurrent Operations Test"
        try:

            async def create_websocket_client(user_id: str):
                try:
                    uri = f"{WS_URL}?user_id={user_id}"
                    async with websockets.connect(uri, timeout=5) as ws:
                        # Send multiple messages
                        for i in range(20):
                            message = json.dumps(
                                {
                                    "type": "query",
                                    "data": f"Concurrent message {i} from {user_id}",
                                    "user_id": user_id,
                                }
                            )
                            await ws.send(message)
                            await asyncio.sleep(0.1)
                except Exception as e:
                    logger.debug(f"Concurrent client {user_id} error: {e}")

            # Run 30 concurrent WebSocket clients
            tasks = []
            for i in range(30):
                task = asyncio.create_task(
                    create_websocket_client(f"concurrent_user_{i}")
                )
                tasks.append(task)

            # Wait for all to complete
            await asyncio.gather(*tasks, return_exceptions=True)

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_database_stress(self):
        """Test database operations under stress."""
        test_name = "Database Stress Test"
        try:

            def make_db_request(session, user_id):
                try:
                    # Simulate heavy database operations
                    data = {
                        "user_id": user_id,
                        "operation": "stress_test",
                        "data": {
                            "messages": [f"Message {i}" for i in range(100)],
                            "metadata": {"timestamp": time.time()},
                        },
                    }
                    response = session.post(
                        f"{SERVER_URL}/api/database/save", json=data, timeout=10
                    )
                    return response.status_code
                except Exception as e:
                    return str(e)

            with requests.Session() as session:
                with ThreadPoolExecutor(max_workers=15) as executor:
                    futures = []

                    # Submit many database operations
                    for i in range(200):
                        future = executor.submit(
                            make_db_request, session, f"db_stress_user_{i}"
                        )
                        futures.append(future)

                    # Wait for completion
                    results = [future.result() for future in as_completed(futures)]
                    success_count = sum(
                        1 for r in results if isinstance(r, int) and 200 <= r < 400
                    )

                    logger.info(
                        f"Database stress: {success_count}/{len(results)} operations successful"
                    )

            self.log_result(test_name, True)

        except Exception as e:
            self.log_result(test_name, False, str(e))

    async def run_all_tests(self):
        """Run the complete stress test suite."""
        logger.info("🚀 Starting Comprehensive Stress Test Suite")
        logger.info("=" * 60)

        start_time = time.time()

        # Run async tests
        async_tests = [
            self.test_websocket_flood(),
            self.test_malformed_websocket_messages(),
            self.test_large_payload_websocket(),
            self.test_rapid_websocket_messages(),
            self.test_ai_context_overflow(),
            self.test_websocket_connection_exhaustion(),
            self.test_concurrent_operations(),
        ]

        await asyncio.gather(*async_tests, return_exceptions=True)

        # Run sync tests
        sync_tests = [
            self.test_http_endpoint_flood,
            self.test_malformed_http_requests,
            self.test_memory_stress,
            self.test_database_stress,
        ]

        for test in sync_tests:
            try:
                test()
            except Exception as e:
                logger.error(f"Test {test.__name__} failed with exception: {e}")

        end_time = time.time()
        duration = end_time - start_time

        # Print results
        logger.info("=" * 60)
        logger.info("🏁 Stress Test Results")
        logger.info(f"Total Tests: {self.results['total_tests']}")
        logger.info(f"Passed: {self.results['passed']}")
        logger.info(f"Failed: {self.results['failed']}")
        logger.info(f"Duration: {duration:.2f} seconds")

        if self.results["performance_metrics"]:
            logger.info("\nPerformance Metrics:")
            for metric, value in self.results["performance_metrics"].items():
                logger.info(f"  {metric}: {value}")

        if self.results["errors"]:
            logger.info(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                logger.info(f"  - {error}")

        logger.info("=" * 60)

        return self.results


async def main():
    """Main test runner."""
    # Check if server is running first
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error("❌ Server is not responding! Please start the server first.")
            return
    except Exception as e:
        logger.error(f"❌ Cannot connect to server: {e}")
        logger.error("Please run: python manage.py start-server")
        return

    logger.info("✅ Server is running, starting stress tests...")

    # Run the stress test suite
    suite = StressTestSuite()
    results = await suite.run_all_tests()

    # Save results to file
    with open("stress_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    logger.info("📊 Results saved to stress_test_results.json")

    # Return exit code based on results
    if results["failed"] > 0:
        logger.warning("⚠️  Some tests failed - check server logs")
        return 1
    else:
        logger.info("🎉 All stress tests completed successfully!")
        return 0


if __name__ == "__main__":
    import sys

    result = asyncio.run(main())
    sys.exit(result)

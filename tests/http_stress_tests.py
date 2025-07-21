#!/usr/bin/env python3
"""HTTP-Only Stress Tests Comprehensive stress tests using only HTTP endpoints since
WebSocket is blocked."""

import json
import logging
import random
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:8001"


class HTTPStressTests:
    """HTTP-focused stress tests."""

    def __init__(self):
        self.results = []
        self.max_workers = 50

    def generate_large_payload(self, size_mb: int = 10):
        """Generate large payload for memory stress."""
        return {
            "large_text": "A" * (size_mb * 1024 * 1024),
            "large_list": list(range(size_mb * 1000)),
            "nested_data": {
                f"key_{i}": f"value_{'X' * 1000}" for i in range(size_mb * 100)
            },
        }

    def test_endpoint_availability(self):
        """Test which endpoints are available."""
        logger.info("🔍 Testing Endpoint Availability")

        endpoints = [
            "/",
            "/health",
            "/docs",
            "/api",
            "/api/users",
            "/api/chat",
            "/api/chat/history",
            "/api/plugins",
            "/api/config",
            "/api/stats",
            "/api/test",
            "/api/upload",
            "/api/process",
            "/api/database/save",
            "/status",
            "/metrics",
            "/admin",
        ]

        available_endpoints = []

        with requests.Session() as session:
            for endpoint in endpoints:
                try:
                    response = session.get(f"{SERVER_URL}{endpoint}", timeout=5)
                    logger.info(f"{endpoint}: {response.status_code}")
                    if response.status_code != 404:
                        available_endpoints.append((endpoint, response.status_code))
                except Exception as e:
                    logger.warning(f"{endpoint}: Error - {e}")

        self.results.append(f"Available endpoints: {len(available_endpoints)}")
        return available_endpoints

    def test_http_flood_attack(self):
        """Test HTTP request flooding."""
        logger.info("🌊 Testing HTTP Flood Attack")

        def make_request(session, request_id):
            try:
                endpoints = ["/health", "/", "/docs"]
                endpoint = random.choice(endpoints)
                response = session.get(f"{SERVER_URL}{endpoint}", timeout=10)
                return f"Request {request_id}: {response.status_code}"
            except Exception as e:
                return f"Request {request_id}: Failed - {e}"

        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                start_time = time.time()

                # Submit 2000 requests rapidly
                futures = []
                for i in range(2000):
                    future = executor.submit(make_request, session, i)
                    futures.append(future)

                # Collect results
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

                end_time = time.time()
                duration = end_time - start_time
                rate = len(results) / duration

                success_count = sum(1 for r in results if "200" in str(r))
                logger.info(
                    f"HTTP flood: {success_count}/{len(results)} successful in {duration:.2f}s ({rate:.2f} req/s)"
                )

                self.results.append(
                    f"HTTP flood: {success_count}/{len(results)} at {rate:.2f} req/s"
                )

    def test_large_payload_attack(self):
        """Test large payload attacks."""
        logger.info("📦 Testing Large Payload Attack")

        endpoints_to_test = ["/health", "/api/test", "/"]

        for endpoint in endpoints_to_test:
            for size_mb in [1, 5, 10, 25, 50]:
                try:
                    large_payload = self.generate_large_payload(size_mb)

                    start_time = time.time()
                    response = requests.post(
                        f"{SERVER_URL}{endpoint}", json=large_payload, timeout=30
                    )
                    end_time = time.time()

                    duration = end_time - start_time
                    logger.info(
                        f"{endpoint} {size_mb}MB: {response.status_code} in {duration:.2f}s"
                    )

                except Exception as e:
                    logger.warning(f"{endpoint} {size_mb}MB: Failed - {e}")

        self.results.append("Large payload: Tested up to 50MB")

    def test_malformed_requests(self):
        """Test malformed HTTP requests."""
        logger.info("🔨 Testing Malformed Requests")

        malformed_tests = [
            # Invalid JSON
            {
                "url": f"{SERVER_URL}/health",
                "data": '{"invalid": json without closing',
                "headers": {"Content-Type": "application/json"},
            },
            # Huge headers
            {
                "url": f"{SERVER_URL}/health",
                "headers": {
                    "X-Large-Header": "A" * 100000,
                    "X-Evil-Header": "\x00\x01\x02\x03" * 1000,
                },
            },
            # Binary data as JSON
            {
                "url": f"{SERVER_URL}/health",
                "data": b"\x00\x01\x02\x03" * 10000,
                "headers": {"Content-Type": "application/json"},
            },
            # Very long URL
            {
                "url": f"{SERVER_URL}/health?" + "x=" + "A" * 100000,
            },
        ]

        for i, test in enumerate(malformed_tests):
            try:
                response = requests.post(
                    test["url"],
                    data=test.get("data"),
                    headers=test.get("headers", {}),
                    timeout=10,
                )
                logger.info(f"Malformed test {i+1}: {response.status_code}")
            except Exception as e:
                logger.info(f"Malformed test {i+1}: Failed as expected - {e}")

        self.results.append("Malformed requests: Completed all tests")

    def test_concurrent_connections(self):
        """Test concurrent connection limits."""
        logger.info("🔗 Testing Concurrent Connections")

        def long_running_request(session, request_id):
            try:
                # Make a request that might take time
                response = session.get(
                    f"{SERVER_URL}/health",
                    timeout=30,
                    stream=True,  # Keep connection alive
                )
                time.sleep(5)  # Hold connection for 5 seconds
                return f"Connection {request_id}: {response.status_code}"
            except Exception as e:
                return f"Connection {request_id}: Failed - {e}"

        with ThreadPoolExecutor(max_workers=100) as executor:
            start_time = time.time()

            # Submit many long-running requests
            futures = []
            for i in range(200):
                session = requests.Session()
                future = executor.submit(long_running_request, session, i)
                futures.append(future)

            # Collect results
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

            end_time = time.time()
            duration = end_time - start_time

            success_count = sum(1 for r in results if "200" in str(r))
            logger.info(
                f"Concurrent connections: {success_count}/{len(results)} successful in {duration:.2f}s"
            )

            self.results.append(
                f"Concurrent: {success_count}/{len(results)} connections"
            )

    def test_memory_exhaustion_attack(self):
        """Test memory exhaustion through HTTP."""
        logger.info("🧠 Testing Memory Exhaustion Attack")

        def memory_bomb_request(session, request_id, size_mb):
            try:
                # Create large in-memory payload
                huge_payload = {
                    "id": request_id,
                    "data": "X" * (size_mb * 1024 * 1024),  # MB of data
                    "metadata": {f"key_{i}": f"value_{i}" * 1000 for i in range(1000)},
                }

                response = session.post(
                    f"{SERVER_URL}/health", json=huge_payload, timeout=20
                )
                return f"Memory bomb {request_id}: {response.status_code}"
            except Exception as e:
                return f"Memory bomb {request_id}: Failed - {e}"

        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = []

                # Submit memory bomb requests
                for i in range(30):
                    size_mb = random.randint(5, 20)  # 5-20MB each
                    future = executor.submit(memory_bomb_request, session, i, size_mb)
                    futures.append(future)

                # Collect results
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

                success_count = sum(1 for r in results if "200" in str(r))
                logger.info(
                    f"Memory exhaustion: {success_count}/{len(results)} requests processed"
                )

                self.results.append(
                    f"Memory exhaustion: {success_count}/{len(results)} processed"
                )

    def test_cpu_intensive_attack(self):
        """Test CPU intensive operations."""
        logger.info("⚡ Testing CPU Intensive Attack")

        def cpu_bomb_request(session, request_id):
            try:
                # Create CPU-intensive payload
                cpu_payload = {
                    "operation": "compute",
                    "data": {
                        "numbers": list(range(100000)),
                        "calculations": [i**2 for i in range(50000)],
                        "nested": {
                            f"level_{i}": {f"sublevel_{j}": j * i for j in range(1000)}
                            for i in range(100)
                        },
                    },
                }

                response = session.post(
                    f"{SERVER_URL}/health", json=cpu_payload, timeout=30
                )
                return f"CPU bomb {request_id}: {response.status_code}"
            except Exception as e:
                return f"CPU bomb {request_id}: Failed - {e}"

        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                start_time = time.time()

                futures = []
                for i in range(100):
                    future = executor.submit(cpu_bomb_request, session, i)
                    futures.append(future)

                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

                end_time = time.time()
                duration = end_time - start_time

                success_count = sum(1 for r in results if "200" in str(r))
                logger.info(
                    f"CPU intensive: {success_count}/{len(results)} in {duration:.2f}s"
                )

                self.results.append(
                    f"CPU intensive: {success_count}/{len(results)} in {duration:.2f}s"
                )

    def test_rapid_fire_requests(self):
        """Test rapid-fire requests to overwhelm server."""
        logger.info("🔥 Testing Rapid Fire Requests")

        def rapid_request(session, request_id):
            try:
                response = session.get(f"{SERVER_URL}/health", timeout=5)
                return response.status_code
            except Exception as e:
                return str(e)

        # Test different rates
        for rate_per_second in [100, 500, 1000, 2000]:
            logger.info(f"Testing {rate_per_second} requests/second...")

            with requests.Session() as session:
                start_time = time.time()

                # Calculate delay between requests
                delay = 1.0 / rate_per_second

                results = []
                for i in range(rate_per_second):
                    try:
                        result = rapid_request(session, i)
                        results.append(result)

                        if i < rate_per_second - 1:  # Don't sleep after last request
                            time.sleep(delay)

                    except Exception as e:
                        results.append(str(e))

                end_time = time.time()
                actual_duration = end_time - start_time
                actual_rate = len(results) / actual_duration

                success_count = sum(1 for r in results if r == 200)
                logger.info(
                    f"Rate {rate_per_second}: {success_count}/{len(results)} successful, actual rate: {actual_rate:.2f} req/s"
                )

        self.results.append(f"Rapid fire: Tested up to 2000 req/s")

    def run_all_http_tests(self):
        """Run all HTTP stress tests."""
        logger.info("🌐 Starting HTTP Stress Test Suite")
        logger.info("=" * 60)

        start_time = time.time()

        # Run all tests
        available_endpoints = self.test_endpoint_availability()
        self.test_http_flood_attack()
        self.test_large_payload_attack()
        self.test_malformed_requests()
        self.test_concurrent_connections()
        self.test_memory_exhaustion_attack()
        self.test_cpu_intensive_attack()
        self.test_rapid_fire_requests()

        end_time = time.time()
        duration = end_time - start_time

        logger.info("=" * 60)
        logger.info("🏁 HTTP Stress Test Results")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("Results:")
        for result in self.results:
            logger.info(f"  - {result}")
        logger.info("=" * 60)

        return self.results, available_endpoints


def main():
    """Main test runner."""
    # Check server
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error("❌ Server is not responding!")
            return 1
    except Exception as e:
        logger.error(f"❌ Cannot connect to server: {e}")
        return 1

    logger.info("✅ Server is running, starting HTTP stress tests...")
    logger.warning("⚠️  WARNING: These tests may impact server performance!")

    # Run tests
    http_tests = HTTPStressTests()
    results, endpoints = http_tests.run_all_http_tests()

    # Save results
    with open("http_stress_test_results.json", "w") as f:
        json.dump(
            {
                "results": results,
                "available_endpoints": endpoints,
                "timestamp": time.time(),
            },
            f,
            indent=2,
        )

    logger.info("📊 Results saved to http_stress_test_results.json")
    return 0


if __name__ == "__main__":
    import sys

    result = main()
    sys.exit(result)

#!/usr/bin/env python3
"""
GAJA Server Extreme Load Test - Push to Breaking Point
Test serwera aż do momentu gdy nie będzie wyrabiać z połączeniami
"""

import asyncio
import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import aiohttp
import psutil
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8001"


class ExtremeLoadTester:
    def __init__(self):
        self.breaking_point = None
        self.max_successful_rate = 0
        self.test_results = []

    def check_server(self):
        """Check if server is accessible."""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def test_rate_escalation(self, start_rate=100, max_rate=10000, step=100):
        """Escalate request rate until server breaks."""
        logger.info("🚀 Starting Rate Escalation Test")
        logger.info(f"Testing from {start_rate} to {max_rate} req/s, step {step}")

        current_rate = start_rate

        while current_rate <= max_rate:
            logger.info(f"📊 Testing {current_rate} requests/second...")

            success_rate, avg_response_time, errors = self.test_specific_rate(
                current_rate
            )

            result = {
                "target_rate": current_rate,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "errors": errors,
                "timestamp": time.time(),
            }

            self.test_results.append(result)

            logger.info(f"   ✅ Success rate: {success_rate:.2f}%")
            logger.info(f"   ⏱️  Avg response time: {avg_response_time:.3f}s")
            logger.info(f"   ❌ Errors: {errors}")

            # Check if this is our breaking point
            if (
                success_rate < 90
                or avg_response_time > 5.0
                or errors > current_rate * 0.1
            ):
                logger.warning(f"🔥 BREAKING POINT DETECTED at {current_rate} req/s!")
                logger.warning(f"   Success rate dropped to {success_rate:.2f}%")
                logger.warning(
                    f"   Response time increased to {avg_response_time:.3f}s"
                )
                logger.warning(f"   Errors increased to {errors}")
                self.breaking_point = current_rate
                break

            self.max_successful_rate = current_rate
            current_rate += step

            # Brief pause between tests
            time.sleep(2)

        return self.breaking_point

    def test_specific_rate(self, target_rate, duration=10):
        """Test specific request rate."""
        total_requests = target_rate * duration
        interval = 1.0 / target_rate

        results = []
        errors = 0
        start_time = time.time()

        def make_request():
            try:
                req_start = time.time()
                response = requests.get(f"{BASE_URL}/health", timeout=10)
                req_end = time.time()

                if response.status_code == 200:
                    return req_end - req_start
                else:
                    return None
            except Exception as e:
                return None

        # Use ThreadPoolExecutor for controlled rate
        with ThreadPoolExecutor(max_workers=min(target_rate, 500)) as executor:
            futures = []

            for i in range(total_requests):
                future = executor.submit(make_request)
                futures.append(future)

                # Control request rate
                if i < total_requests - 1:
                    time.sleep(interval)

                # Check if we're taking too long
                if time.time() - start_time > duration * 2:
                    logger.warning("⏰ Test taking too long, breaking early")
                    break

            # Collect results
            for future in as_completed(futures, timeout=duration * 2):
                try:
                    result = future.result(timeout=1)
                    if result is not None:
                        results.append(result)
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        # Calculate metrics
        success_count = len(results)
        total_attempted = len(futures)
        success_rate = (
            (success_count / total_attempted * 100) if total_attempted > 0 else 0
        )
        avg_response_time = sum(results) / len(results) if results else 0

        return success_rate, avg_response_time, errors

    async def async_flood_test(self, connections=1000, requests_per_connection=100):
        """Async flood test to push server limits."""
        logger.info(
            f"🌊 Starting Async Flood Test: {connections} connections, {requests_per_connection} req/conn"
        )

        async def make_async_request(session):
            try:
                async with session.get(f"{BASE_URL}/health") as response:
                    return response.status == 200
            except:
                return False

        async def connection_worker(session, connection_id):
            successful_requests = 0
            for i in range(requests_per_connection):
                if await make_async_request(session):
                    successful_requests += 1

                # Small delay to avoid overwhelming
                await asyncio.sleep(0.001)

            return successful_requests

        start_time = time.time()

        # Create connector with high limits
        connector = aiohttp.TCPConnector(
            limit=connections * 2,
            limit_per_host=connections * 2,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []

            for i in range(connections):
                task = connection_worker(session, i)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        # Analyze results
        successful_connections = sum(1 for r in results if isinstance(r, int))
        total_successful_requests = sum(r for r in results if isinstance(r, int))
        total_requests = connections * requests_per_connection

        success_rate = (
            (total_successful_requests / total_requests * 100)
            if total_requests > 0
            else 0
        )

        logger.info(
            f"   ✅ Successful connections: {successful_connections}/{connections}"
        )
        logger.info(
            f"   ✅ Successful requests: {total_successful_requests}/{total_requests}"
        )
        logger.info(f"   📊 Success rate: {success_rate:.2f}%")
        logger.info(f"   ⏱️  Duration: {duration:.2f}s")
        logger.info(
            f"   🚀 Effective rate: {total_successful_requests/duration:.2f} req/s"
        )

        return success_rate, total_successful_requests, duration

    def monitor_system_resources(self, duration=60):
        """Monitor system resources during stress test."""
        logger.info(f"📊 Monitoring system resources for {duration}s...")

        resource_data = []
        start_time = time.time()

        while time.time() - start_time < duration:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()

                resource_data.append(
                    {
                        "timestamp": time.time(),
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "memory_available_mb": memory.available // 1024 // 1024,
                    }
                )

                logger.info(
                    f"CPU: {cpu_percent:.1f}%, RAM: {memory.percent:.1f}%, Available: {memory.available // 1024 // 1024}MB"
                )

            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                break

        return resource_data

    def stress_test_until_failure(self):
        """Main stress test that pushes server to failure."""
        if not self.check_server():
            logger.error("❌ Server not accessible")
            return None

        logger.info("✅ Server is running, starting extreme load test...")
        logger.warning(
            "⚠️ WARNING: This test will push the server to its breaking point!"
        )

        logger.info("🔥 Starting Extreme Load Test Suite")
        logger.info("=" * 60)

        start_time = time.time()

        # Phase 1: Rate escalation test
        logger.info("Phase 1: Rate Escalation Test")
        breaking_point = self.test_rate_escalation(
            start_rate=500, max_rate=20000, step=500
        )

        # Phase 2: Async flood test
        logger.info("\nPhase 2: Async Flood Test")
        async_results = asyncio.run(
            self.async_flood_test(connections=2000, requests_per_connection=50)
        )

        # Phase 3: System resource monitoring during extreme load
        logger.info("\nPhase 3: Resource Monitoring During Extreme Load")

        def background_load():
            """Generate background load during monitoring."""
            for i in range(1000):
                try:
                    requests.get(f"{BASE_URL}/health", timeout=5)
                except:
                    pass
                time.sleep(0.01)

        # Start background load
        load_thread = threading.Thread(target=background_load)
        load_thread.start()

        # Monitor resources
        resource_data = self.monitor_system_resources(duration=30)

        load_thread.join()

        total_duration = time.time() - start_time

        # Final results
        logger.info("=" * 60)
        logger.info("🏁 Extreme Load Test Results")
        logger.info(f"Duration: {total_duration:.2f} seconds")

        if breaking_point:
            logger.info(f"💥 BREAKING POINT: {breaking_point} req/s")
            logger.info(f"🎯 Max Successful Rate: {self.max_successful_rate} req/s")
        else:
            logger.info("🚀 Server survived all tests!")
            logger.info(f"🎯 Max Tested Rate: {self.max_successful_rate} req/s")

        logger.info(f"🌊 Async Flood: {async_results[0]:.2f}% success rate")
        logger.info(f"📊 Resource Monitoring: {len(resource_data)} data points")
        logger.info("=" * 60)

        # Save results
        final_results = {
            "breaking_point": breaking_point,
            "max_successful_rate": self.max_successful_rate,
            "rate_escalation_results": self.test_results,
            "async_flood_results": {
                "success_rate": async_results[0],
                "total_requests": async_results[1],
                "duration": async_results[2],
            },
            "resource_monitoring": resource_data,
            "total_duration": total_duration,
            "timestamp": time.time(),
        }

        with open("extreme_load_test_results.json", "w") as f:
            json.dump(final_results, f, indent=2)

        logger.info("📊 Results saved to extreme_load_test_results.json")

        return breaking_point


def main():
    tester = ExtremeLoadTester()
    breaking_point = tester.stress_test_until_failure()

    if breaking_point:
        print(f"\n🔥 SERVER BREAKING POINT FOUND: {breaking_point} requests/second")
        print("💡 Server failed to handle the load at this rate")
    else:
        print(f"\n🚀 SERVER SURVIVED ALL TESTS!")
        print(f"💪 Maximum tested rate: {tester.max_successful_rate} requests/second")

    return breaking_point


if __name__ == "__main__":
    main()

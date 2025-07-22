#!/usr/bin/env python3
"""Docker Resource Exhaustion Tests Tests designed to push Docker container limits and
system resources."""

import asyncio
import json
import logging
import multiprocessing
import random
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import psutil
import requests
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/ws/"


class DockerStressTests:
    """Tests to exhaust Docker container resources."""

    def __init__(self):
        self.results = []
        self.max_workers = multiprocessing.cpu_count() * 4
        self.stress_duration = 60  # seconds

    def monitor_system_resources(self, duration: int = 60):
        """Monitor system resources during tests."""
        logger.info(f"🔍 Monitoring system resources for {duration} seconds...")

        start_time = time.time()
        resource_data = []

        while time.time() - start_time < duration:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                resource_data.append(
                    {
                        "timestamp": time.time(),
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "memory_available_mb": memory.available / 1024 / 1024,
                        "disk_percent": disk.percent,
                    }
                )

                logger.info(
                    f"CPU: {cpu_percent}%, RAM: {memory.percent}%, Available: {memory.available/1024/1024:.0f}MB"
                )

            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
                break

        return resource_data

    def create_memory_bomb(self, size_mb: int = 100):
        """Create data designed to consume memory."""
        # Create large lists and dictionaries
        memory_bomb = {
            "large_list": list(range(size_mb * 1000)),
            "large_string": "A" * (size_mb * 1024 * 1024),  # MB of As
            "nested_dicts": {
                f"key_{i}": {f"subkey_{j}": "X" * 1000 for j in range(1000)}
                for i in range(size_mb)
            },
            "random_data": [
                "".join(random.choices(string.ascii_letters, k=10000))
                for _ in range(size_mb * 10)
            ],
        }
        return memory_bomb

    async def test_websocket_memory_exhaustion(self):
        """Test WebSocket connections that consume lots of memory."""
        logger.info("🧠 Testing WebSocket Memory Exhaustion")

        try:
            connections = []
            memory_bombs = []

            # Create many connections with large data
            for i in range(100):
                try:
                    uri = f"{WS_URL}?user_id=memory_user_{i}"
                    ws = await websockets.connect(uri, timeout=5)
                    connections.append(ws)

                    # Create and send memory bomb
                    memory_bomb = self.create_memory_bomb(10)  # 10MB each
                    memory_bombs.append(memory_bomb)

                    message = json.dumps(
                        {
                            "type": "memory_test",
                            "data": memory_bomb,
                            "user_id": f"memory_user_{i}",
                        }
                    )

                    await ws.send(message)

                    if i % 10 == 0:
                        logger.info(f"Created {i} memory-heavy connections")

                except Exception as e:
                    logger.warning(f"Memory exhaustion failed at connection {i}: {e}")
                    break

            # Keep connections alive to maintain memory pressure
            await asyncio.sleep(30)

            # Close connections
            for ws in connections:
                try:
                    await ws.close()
                except Exception:
                    pass

            self.results.append(
                f"Memory exhaustion: Created {len(connections)} heavy connections"
            )

        except Exception as e:
            logger.error(f"Memory exhaustion test failed: {e}")
            self.results.append(f"Memory exhaustion: Failed - {e}")

    def test_cpu_intensive_requests(self):
        """Test CPU-intensive HTTP requests."""
        logger.info("⚡ Testing CPU-Intensive Requests")

        def cpu_bomb_request(session, request_id):
            try:
                # Create CPU-intensive data
                cpu_bomb = {
                    "operation": "cpu_intensive",
                    "data": {
                        "large_calculation": [i**2 for i in range(100000)],
                        "text_processing": "analyze " * 10000,
                        "nested_loops": [
                            [j * k for k in range(1000)] for j in range(100)
                        ],
                    },
                    "request_id": request_id,
                }

                response = session.post(
                    f"{SERVER_URL}/api/process", json=cpu_bomb, timeout=30
                )
                return f"Request {request_id}: {response.status_code}"

            except Exception as e:
                return f"Request {request_id}: Failed - {e}"

        # Start resource monitoring in background
        monitor_thread = threading.Thread(
            target=self.monitor_system_resources, args=(self.stress_duration,)
        )
        monitor_thread.start()

        # Launch CPU-intensive requests
        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []

                # Submit many CPU-intensive requests
                for i in range(200):
                    future = executor.submit(cpu_bomb_request, session, i)
                    futures.append(future)

                # Collect results
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

                success_count = sum(1 for r in results if "200" in str(r))
                logger.info(
                    f"CPU stress: {success_count}/{len(results)} requests successful"
                )

        monitor_thread.join()
        self.results.append(f"CPU intensive: {success_count}/{len(results)} successful")

    async def test_file_descriptor_exhaustion(self):
        """Test file descriptor exhaustion through connections."""
        logger.info("📁 Testing File Descriptor Exhaustion")

        try:
            connections = []

            # Try to create as many connections as possible
            for i in range(10000):  # Try to exhaust file descriptors
                try:
                    uri = f"{WS_URL}?user_id=fd_user_{i}"
                    ws = await websockets.connect(uri, timeout=1)
                    connections.append(ws)

                    if i % 100 == 0:
                        logger.info(f"Created {i} file descriptor connections")

                except Exception as e:
                    logger.info(f"FD exhaustion reached at {i} connections: {e}")
                    break

            logger.info(f"Maximum connections: {len(connections)}")

            # Close all connections
            for ws in connections:
                try:
                    await ws.close()
                except Exception:
                    pass

            self.results.append(f"FD exhaustion: Max {len(connections)} connections")

        except Exception as e:
            logger.error(f"FD exhaustion test failed: {e}")
            self.results.append(f"FD exhaustion: Failed - {e}")

    async def test_disk_space_exhaustion(self):
        """Test disk space exhaustion through large uploads."""
        logger.info("💾 Testing Disk Space Pressure")

        try:
            # Create large data to upload
            large_files = []
            for i in range(10):
                file_data = {
                    "filename": f"large_file_{i}.txt",
                    "content": "A" * (50 * 1024 * 1024),  # 50MB each
                    "metadata": {"size": 50 * 1024 * 1024, "type": "stress_test"},
                }
                large_files.append(file_data)

            # Upload files via WebSocket
            uri = f"{WS_URL}?user_id=disk_user"
            async with websockets.connect(uri, timeout=10) as ws:
                for i, file_data in enumerate(large_files):
                    message = json.dumps(
                        {
                            "type": "file_upload",
                            "data": file_data,
                            "user_id": "disk_user",
                        }
                    )

                    logger.info(f"Uploading large file {i+1} (50MB)")

                    try:
                        await ws.send(message)
                        await asyncio.sleep(2)
                    except Exception as e:
                        logger.warning(f"Large file upload {i+1} failed: {e}")

            self.results.append(f"Disk pressure: Uploaded {len(large_files)} files")

        except Exception as e:
            logger.error(f"Disk pressure test failed: {e}")
            self.results.append(f"Disk pressure: Failed - {e}")

    async def test_network_bandwidth_saturation(self):
        """Test network bandwidth saturation."""
        logger.info("🌐 Testing Network Bandwidth Saturation")

        async def bandwidth_client(client_id: int):
            try:
                uri = f"{WS_URL}?user_id=bandwidth_user_{client_id}"
                async with websockets.connect(uri, timeout=5) as ws:
                    # Send continuous large messages
                    for i in range(100):
                        large_message = {
                            "type": "bandwidth_test",
                            "data": "X" * (1024 * 1024),  # 1MB per message
                            "sequence": i,
                            "client_id": client_id,
                        }

                        message = json.dumps(large_message)
                        await ws.send(message)
                        await asyncio.sleep(0.1)  # Small delay

            except Exception as e:
                logger.debug(f"Bandwidth client {client_id} error: {e}")

        try:
            # Launch many bandwidth-intensive clients
            tasks = []
            for i in range(20):
                task = asyncio.create_task(bandwidth_client(i))
                tasks.append(task)

            # Wait for all clients to finish
            await asyncio.gather(*tasks, return_exceptions=True)

            self.results.append("Bandwidth saturation: Completed 20 clients")

        except Exception as e:
            logger.error(f"Bandwidth saturation test failed: {e}")
            self.results.append(f"Bandwidth saturation: Failed - {e}")

    def test_docker_resource_limits(self):
        """Test Docker container resource limits."""
        logger.info("🐳 Testing Docker Resource Limits")

        try:
            # Get Docker container stats
            import subprocess

            try:
                # Get container ID
                result = subprocess.run(
                    ["docker", "ps", "--filter", "name=gaja", "--format", "{{.ID}}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                container_id = result.stdout.strip()

                if container_id:
                    # Get container stats
                    stats_result = subprocess.run(
                        [
                            "docker",
                            "stats",
                            container_id,
                            "--no-stream",
                            "--format",
                            "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    logger.info(f"Docker Stats:\n{stats_result.stdout}")

                    # Get container resource limits
                    inspect_result = subprocess.run(
                        [
                            "docker",
                            "inspect",
                            container_id,
                            "--format",
                            "{{.HostConfig.Memory}} {{.HostConfig.CpuQuota}} {{.HostConfig.CpuShares}}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    logger.info(f"Resource Limits: {inspect_result.stdout}")

                    self.results.append(
                        f"Docker limits: Container {container_id[:12]} monitored"
                    )
                else:
                    self.results.append("Docker limits: No GAJA container found")

            except subprocess.TimeoutExpired:
                logger.warning("Docker commands timed out")
                self.results.append("Docker limits: Commands timed out")

        except Exception as e:
            logger.error(f"Docker resource limits test failed: {e}")
            self.results.append(f"Docker limits: Failed - {e}")

    async def test_cascade_failure(self):
        """Test cascade failure scenarios."""
        logger.info("⛓️ Testing Cascade Failure")

        try:
            # Start multiple stress tests simultaneously
            stress_tasks = [
                self.test_websocket_memory_exhaustion(),
                self.test_network_bandwidth_saturation(),
                self.test_file_descriptor_exhaustion(),
            ]

            # Start resource monitoring
            monitor_thread = threading.Thread(
                target=self.monitor_system_resources, args=(60,)
            )
            monitor_thread.start()

            # Run all stress tests simultaneously
            start_time = time.time()
            await asyncio.gather(*stress_tasks, return_exceptions=True)
            end_time = time.time()

            # Wait for monitoring to complete
            monitor_thread.join()

            duration = end_time - start_time
            self.results.append(
                f"Cascade failure: Survived {duration:.2f}s of combined stress"
            )

        except Exception as e:
            logger.error(f"Cascade failure test failed: {e}")
            self.results.append(f"Cascade failure: Failed - {e}")

    async def run_all_docker_tests(self):
        """Run all Docker stress tests."""
        logger.info("🐳 Starting Docker Resource Exhaustion Tests")
        logger.info("=" * 60)

        start_time = time.time()

        # Run async tests
        async_tests = [
            self.test_websocket_memory_exhaustion(),
            self.test_file_descriptor_exhaustion(),
            self.test_disk_space_exhaustion(),
            self.test_network_bandwidth_saturation(),
            self.test_cascade_failure(),
        ]

        await asyncio.gather(*async_tests, return_exceptions=True)

        # Run sync tests
        self.test_cpu_intensive_requests()
        self.test_docker_resource_limits()

        end_time = time.time()
        duration = end_time - start_time

        logger.info("=" * 60)
        logger.info("🏁 Docker Stress Test Results")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("Results:")
        for result in self.results:
            logger.info(f"  - {result}")
        logger.info("=" * 60)

        return self.results


async def main():
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

    logger.info("✅ Server is running, starting Docker stress tests...")
    logger.warning("⚠️  WARNING: These tests may impact system performance!")

    # Run tests
    docker_tests = DockerStressTests()
    results = await docker_tests.run_all_docker_tests()

    # Save results
    with open("docker_stress_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    logger.info("📊 Results saved to docker_stress_test_results.json")
    return 0


if __name__ == "__main__":
    import sys

    result = asyncio.run(main())
    sys.exit(result)

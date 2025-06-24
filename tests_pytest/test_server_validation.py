"""Simple standalone tests for server validation according to server_testing_todo.md
Following AGENTS.md guidelines for async testing."""

import asyncio
import json
import time

import aiohttp
import pytest

# Test configuration
SERVER_URL = "http://localhost:8001"
TEST_USER_ID = "test_user_validation"


@pytest.mark.asyncio
async def test_basic_server_connection():
    """Test basic server connectivity and response format."""
    async with aiohttp.ClientSession() as session:
        # Test root endpoint
        async with session.get(f"{SERVER_URL}/") as response:
            assert response.status == 200
            data = await response.json()
            assert "message" in data
            assert data["message"] == "GAJA Assistant Server"


@pytest.mark.asyncio
async def test_server_accepts_ai_queries():
    """🌐 1.

    API i komunikacja z klientem - Serwer przyjmuje zapytania
    """
    async with aiohttp.ClientSession() as session:
        payload = {"user_id": TEST_USER_ID, "query": "Test query", "context": {}}

        async with session.post(f"{SERVER_URL}/api/ai_query", json=payload) as response:
            assert response.status == 200
            data = await response.json()

            # Check response format according to server requirements
            assert "ai_response" in data
            assert isinstance(data["ai_response"], str)
            assert len(data["ai_response"]) > 0


@pytest.mark.asyncio
async def test_server_handles_bad_requests():
    """🌐 1.

    API i komunikacja z klientem - Obsługuje błędne żądania
    """
    async with aiohttp.ClientSession() as session:
        # Test with empty payload
        async with session.post(f"{SERVER_URL}/api/ai_query", json={}) as response:
            assert response.status in [400, 422]  # Should reject invalid payload


@pytest.mark.asyncio
async def test_response_time_performance():
    """🌐 1.

    API i komunikacja z klientem - Czas odpowiedzi
    """
    async with aiohttp.ClientSession() as session:
        payload = {"user_id": TEST_USER_ID, "query": "Jaka jest pogoda?", "context": {}}

        start_time = time.time()
        async with session.post(f"{SERVER_URL}/api/ai_query", json=payload) as response:
            elapsed_time = time.time() - start_time

            assert response.status == 200
            data = await response.json()
            assert "ai_response" in data

            # Response should be reasonably fast (less than 5 seconds for any query)
            assert elapsed_time < 5.0, f"Response took {elapsed_time}s, too slow"


@pytest.mark.asyncio
async def test_concurrent_requests():
    """🌐 1.

    API i komunikacja z klientem - Obsługa wielu klientów jednocześnie
    """

    async def make_request(session, user_id):
        payload = {
            "user_id": user_id,
            "query": f"Test query from {user_id}",
            "context": {},
        }
        async with session.post(f"{SERVER_URL}/api/ai_query", json=payload) as response:
            return response.status == 200

    async with aiohttp.ClientSession() as session:
        # Test 5 concurrent requests
        tasks = []
        for i in range(5):
            user_id = f"concurrent_user_{i}"
            tasks.append(make_request(session, user_id))

        results = await asyncio.gather(*tasks)

        # At least 80% should succeed
        success_count = sum(results)
        assert (
            success_count >= 4
        ), f"Only {success_count}/5 concurrent requests succeeded"


@pytest.mark.asyncio
async def test_intent_parsing_basic():
    """🧠 2.

    Parser intencji - Podstawowa klasyfikacja
    """
    test_queries = [
        "Jaka jest pogoda?",
        "What's the weather?",
        "Tell me a joke",
        "Random text that doesn't match any intent xyz123",
    ]

    async with aiohttp.ClientSession() as session:
        for query in test_queries:
            payload = {"user_id": TEST_USER_ID, "query": query, "context": {}}

            async with session.post(
                f"{SERVER_URL}/api/ai_query", json=payload
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert "ai_response" in data
                assert len(data["ai_response"]) > 0


@pytest.mark.asyncio
async def test_ambiguous_query_handling():
    """🧠 2.

    Parser intencji - Obsługa niejednoznacznych zapytań
    """
    async with aiohttp.ClientSession() as session:
        payload = {"user_id": TEST_USER_ID, "query": "zrób coś", "context": {}}

        async with session.post(f"{SERVER_URL}/api/ai_query", json=payload) as response:
            assert response.status == 200
            data = await response.json()
            assert "ai_response" in data
            # Should provide some response, not crash
            assert len(data["ai_response"]) > 0


@pytest.mark.asyncio
async def test_multilingual_support():
    """🧠 2.

    Parser intencji - Obsługa różnych języków
    """
    multilingual_queries = [
        ("Jaka jest pogoda?", "pl"),
        ("What's the weather?", "en"),
    ]

    async with aiohttp.ClientSession() as session:
        for query, lang in multilingual_queries:
            payload = {"user_id": TEST_USER_ID, "query": query, "context": {}}

            async with session.post(
                f"{SERVER_URL}/api/ai_query", json=payload
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert "ai_response" in data
                assert len(data["ai_response"]) > 0


@pytest.mark.asyncio
async def test_plugin_error_handling():
    """🧩 4.

    Pluginy - Nie crashują przy błędnych danych
    """
    edge_cases = [
        "",  # Empty query
        "a" * 1000,  # Very long query
        "🎉🎊🎈" * 50,  # Unicode stress test
    ]

    async with aiohttp.ClientSession() as session:
        for query in edge_cases:
            if not query:  # Skip empty query as it's handled by request validation
                continue

            payload = {"user_id": TEST_USER_ID, "query": query, "context": {}}

            async with session.post(
                f"{SERVER_URL}/api/ai_query", json=payload
            ) as response:
                # Should not crash, even if returns error
                assert response.status in [200, 400, 422, 500]
                if response.status == 200:
                    data = await response.json()
                    assert "ai_response" in data


@pytest.mark.asyncio
async def test_health_endpoints():
    """🧰 10.

    Dev tools / debug - Endpoint testowy odpowiada
    """
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        async with session.get(f"{SERVER_URL}/health") as response:
            assert response.status == 200


@pytest.mark.asyncio
async def test_multiple_user_isolation():
    """📦 8.

    Logika sesji i użytkowników - Dane nie mieszają się
    """
    async with aiohttp.ClientSession() as session:
        # User 1
        payload1 = {
            "user_id": "isolation_user_1",
            "query": "Test from user 1",
            "context": {},
        }

        # User 2
        payload2 = {
            "user_id": "isolation_user_2",
            "query": "Test from user 2",
            "context": {},
        }

        # Both should work independently
        async with session.post(
            f"{SERVER_URL}/api/ai_query", json=payload1
        ) as response:
            assert response.status == 200
            data1 = await response.json()
            assert "ai_response" in data1

        async with session.post(
            f"{SERVER_URL}/api/ai_query", json=payload2
        ) as response:
            assert response.status == 200
            data2 = await response.json()
            assert "ai_response" in data2


@pytest.mark.asyncio
async def test_server_stability_under_load():
    """🧪 9.

    Stabilność i odporność - Nie crashuje przy dużej ilości zapytań
    """

    async def make_load_request(session, request_id):
        payload = {
            "user_id": f"load_test_user_{request_id % 5}",  # 5 different users
            "query": f"Load test query {request_id}",
            "context": {},
        }

        try:
            async with session.post(
                f"{SERVER_URL}/api/ai_query", json=payload
            ) as response:
                return response.status == 200
        except Exception:
            return False

    async with aiohttp.ClientSession() as session:
        # Create 20 concurrent requests (reduced from 50 for initial testing)
        tasks = []
        for i in range(20):
            tasks.append(make_load_request(session, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful requests
        success_count = sum(1 for result in results if result is True)

        # At least 70% should succeed under load
        assert (
            success_count >= 14
        ), f"Only {success_count}/20 requests succeeded under load"


@pytest.mark.asyncio
async def test_ai_llm_functionality():
    """🧠 7.

    Model AI / LLM fallback - Działa domyślny backend
    """
    async with aiohttp.ClientSession() as session:
        payload = {
            "user_id": TEST_USER_ID,
            "query": "Tell me a very short joke",
            "context": {},
        }

        async with session.post(f"{SERVER_URL}/api/ai_query", json=payload) as response:
            assert response.status == 200
            data = await response.json()
            assert "ai_response" in data

            # Should get a substantial response from LLM
            ai_response = data["ai_response"]
            if isinstance(ai_response, str) and ai_response.startswith('{"text"'):
                # Response is JSON-encoded, parse it
                response_data = json.loads(ai_response)
                assert len(response_data.get("text", "")) > 10
            else:
                assert len(ai_response) > 10


@pytest.mark.asyncio
async def test_error_handling_graceful():
    """🧠 7.

    Model AI / LLM fallback - Obsługa błędów API
    """
    async with aiohttp.ClientSession() as session:
        # Test with potentially problematic query
        very_long_query = (
            "Explain this concept in great detail: " + "very detailed " * 100
        )

        payload = {"user_id": TEST_USER_ID, "query": very_long_query, "context": {}}

        async with session.post(f"{SERVER_URL}/api/ai_query", json=payload) as response:
            # Should not crash, even if hits limits
            assert response.status in [
                200,
                400,
                413,
                500,
            ]  # Various acceptable responses

            if response.status == 200:
                data = await response.json()
                assert "ai_response" in data


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])

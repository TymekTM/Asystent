import asyncio

import aiohttp


async def final_test():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8001/api/ai_query",
            json={
                "user_id": "final_test",
                "query": "Test if server is still working",
                "context": {},
            },
        ) as response:
            print(f"Status: {response.status}")
            data = await response.json()
            print(f'Response: {data.get("ai_response", "No response")[:100]}...')


if __name__ == "__main__":
    asyncio.run(final_test())

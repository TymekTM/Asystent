#!/usr/bin/env python3
"""Test script for overlay debug tools API endpoints.

Quick verification that the fixes work correctly.
"""

import asyncio
import json

import aiohttp


async def test_overlay_endpoints():
    """Test all overlay endpoints."""
    base_url = "http://localhost:5001"

    async with aiohttp.ClientSession() as session:
        print("🔍 Testing Overlay Debug API Endpoints")
        print("=" * 50)

        # Test 1: Get Status
        print("1. Testing /api/status...")
        try:
            async with session.get(f"{base_url}/api/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(f"   📊 Data: {json.dumps(data, indent=2)}")
                else:
                    print(f"   ❌ Status: {response.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

        # Test 2: Show Overlay
        print("2. Testing /api/overlay/show...")
        try:
            async with session.get(f"{base_url}/api/overlay/show") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(f"   📊 Response: {data}")
                else:
                    print(f"   ❌ Status: {response.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

        # Test 3: Hide Overlay
        print("3. Testing /api/overlay/hide...")
        try:
            async with session.get(f"{base_url}/api/overlay/hide") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(f"   📊 Response: {data}")
                else:
                    print(f"   ❌ Status: {response.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

        # Test 4: Test Wakeword (for text simulation)
        print("4. Testing /api/test/wakeword...")
        try:
            test_text = "Hello from debug test!"
            async with session.get(
                f"{base_url}/api/test/wakeword?query={test_text}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(f"   📊 Response: {data}")
                else:
                    print(f"   ❌ Status: {response.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

        # Test 5: Overlay Status
        print("5. Testing /api/overlay/status...")
        try:
            async with session.get(f"{base_url}/api/overlay/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(f"   📊 Data: {json.dumps(data, indent=2)}")
                else:
                    print(f"   ❌ Status: {response.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()
        print("🎉 API Endpoint Testing Complete!")


if __name__ == "__main__":
    asyncio.run(test_overlay_endpoints())

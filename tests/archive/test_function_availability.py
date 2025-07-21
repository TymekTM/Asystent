#!/usr/bin/env python3
"""Quick test to check if ask_for_clarification is available to AI in container."""


import requests


def test_function_availability():
    """Test if ask_for_clarification function is available through AI."""
    print("🔧 Testing function availability in container...")

    try:
        # Try direct AI query that should trigger clarification
        response = requests.post(
            "http://localhost:8001/ai/process",
            json={
                "query": "ustaw timer",  # Should need clarification for duration
                "context": {},
                "user_id": "test_user",
            },
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ AI process response: {result}")

            # Check if function calling worked
            if result.get("type") == "clarification_request":
                print("🎉 SUCCESS: ask_for_clarification function worked!")
                return True
            else:
                print("❌ ask_for_clarification function not triggered")
                print(f"   Response type: {result.get('type')}")
                print(f"   Message: {result.get('message', 'No message')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def test_functions_list():
    """Test if we can get the list of available functions."""
    print("\n🔧 Testing available functions list...")

    try:
        # Try to get functions list
        response = requests.get("http://localhost:8001/functions", timeout=5)

        if response.status_code == 404:
            print("❌ /functions endpoint not found - that's expected")
            return False
        elif response.status_code == 200:
            functions = response.json()
            print(f"✅ Found {len(functions)} functions")

            # Look for ask_for_clarification
            clarification_found = False
            for func in functions:
                if "ask_for_clarification" in func.get("name", ""):
                    clarification_found = True
                    print(f"🎉 Found: {func['name']}")

            if not clarification_found:
                print("❌ ask_for_clarification not in functions list")
                print("Available functions:")
                for func in functions:
                    print(f"  - {func.get('name', 'unknown')}")

            return clarification_found
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Quick function availability test")
    print("=" * 50)

    functions_available = test_functions_list()
    ai_working = test_function_availability()

    print("\n" + "=" * 50)
    if functions_available and ai_working:
        print("✅ Everything working!")
    elif functions_available:
        print("⚠️ Function exists but AI not using it")
    else:
        print("❌ Function not available to AI")
        print("💡 Check if container has latest code")

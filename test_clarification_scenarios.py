#!/usr/bin/env python3
"""
Test specjalnie dla funkcji ask_for_clarification
Test scenariuszy, gdzie AI powinno poprosić o wyjaśnienie
"""

import asyncio
import json
import websockets
import sys
from pathlib import Path

# Add server path to imports
sys.path.insert(0, str(Path(__file__).parent / "server"))

async def test_clarification_scenarios():
    """Test scenariuszy gdzie AI powinno poprosić o wyjaśnienie"""
    
    print("🔍 Testing ask_for_clarification scenarios")
    print("=" * 60)
    
    # Scenariusze gdzie AI POWINNO poprosić o wyjaśnienie
    clarification_tests = [
        {
            "name": "Weather without location",
            "query": "Jaka jest pogoda?",
            "should_clarify": True,
            "expected_question": "miasto",
            "follow_up": "Warszawa"
        },
        {
            "name": "Music without details",
            "query": "Puść muzykę",
            "should_clarify": True, 
            "expected_question": "muzyk",
            "follow_up": "Halsey"
        },
        {
            "name": "Timer without duration",
            "query": "Ustaw timer",
            "should_clarify": True,
            "expected_question": "długo",
            "follow_up": "5 minut"
        },
        {
            "name": "Reminder without details",
            "query": "Przypomnij mi",
            "should_clarify": True,
            "expected_question": "czym",
            "follow_up": "o spotkaniu jutro o 15:00"
        },
        {
            "name": "Add to list without list name",
            "query": "Dodaj mleko",
            "should_clarify": True,
            "expected_question": "lista",
            "follow_up": "do listy zakupów"
        },
        {
            "name": "Search without topic",
            "query": "Wyszukaj informacje",
            "should_clarify": True,
            "expected_question": "temat",
            "follow_up": "o sztucznej inteligencji"
        }
    ]
    
    clarification_count = 0
    total_tests = len(clarification_tests)
    
    for i, test in enumerate(clarification_tests, 1):
        print(f"\n🧪 Test {i}/{total_tests}: {test['name']}")
        print(f"📝 Query: '{test['query']}'")
        
        try:
            async with websockets.connect("ws://localhost:8001/ws/clarification_test") as websocket:
                # Wait for handshake
                await websocket.recv()
                
                # Send query
                message = {
                    "type": "ai_query",
                    "query": test["query"],
                    "timestamp": "2025-07-21T15:00:00.000Z"
                }
                
                await websocket.send(json.dumps(message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "clarification_request":
                    clarification_count += 1
                    data = response_data.get("data", {})
                    question = data.get("question", "").lower()
                    
                    print("✅ AI ASKED FOR CLARIFICATION!")
                    print(f"❓ Question: {data.get('question', 'No question')}")
                    print(f"📝 Context: {data.get('context', 'No context')}")
                    
                    # Check if question contains expected keywords
                    if test["expected_question"].lower() in question:
                        print("🎯 Question contains expected keywords ✅")
                    else:
                        print(f"⚠️  Expected '{test['expected_question']}' in question")
                    
                    # Test follow-up response
                    follow_up = {
                        "type": "ai_query",
                        "query": test["follow_up"],
                        "timestamp": "2025-07-21T15:00:10.000Z"
                    }
                    
                    await websocket.send(json.dumps(follow_up))
                    final_response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    final_data = json.loads(final_response)
                    
                    print(f"🔄 Follow-up sent: {test['follow_up']}")
                    print(f"✅ Final response type: {final_data.get('type', 'unknown')}")
                    
                elif response_data.get("type") == "ai_response":
                    # Check if AI response contains clarification request in text
                    ai_response = response_data.get("data", {}).get("response", "")
                    try:
                        parsed_response = json.loads(ai_response)
                        ai_text = parsed_response.get("text", "").lower()
                    except:
                        ai_text = ai_response.lower()
                    
                    # Check for clarification indicators in text
                    clarification_words = [
                        "jakiej", "jakiego", "gdzie", "kiedy", "co", 
                        "ile", "który", "która", "sprecyzuj", "podaj",
                        "nie podał", "brakuje", "więcej informacji"
                    ]
                    
                    if any(word in ai_text for word in clarification_words):
                        print("🔄 AI asked for clarification in TEXT (not function)")
                        print(f"💬 Response: {ai_text[:200]}...")
                    else:
                        print("❌ AI did not ask for clarification")
                        print(f"💬 Response: {ai_text[:200]}...")
                else:
                    print(f"❓ Unexpected response: {response_data.get('type', 'unknown')}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Brief pause between tests
        await asyncio.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"📊 CLARIFICATION FUNCTION RESULTS:")
    print(f"   Clarification function used: {clarification_count}/{total_tests}")
    print(f"   Success rate: {clarification_count/total_tests*100:.1f}%")
    
    if clarification_count == 0:
        print(f"\n⚠️  AI did not use ask_for_clarification function!")
        print(f"💡 This is expected - AI needs better prompting to use this function")
        print(f"🔧 Next steps:")
        print(f"   1. Improve system prompt to encourage clarification")
        print(f"   2. Add examples in function description")
        print(f"   3. Train AI with clarification scenarios")
    else:
        print(f"\n🎉 Success! AI is learning to ask for clarification!")
    
    return clarification_count, total_tests

async def main():
    try:
        await test_clarification_scenarios()
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure the server is running first!")

if __name__ == "__main__":
    asyncio.run(main())

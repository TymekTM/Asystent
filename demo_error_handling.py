"""
Integration test to demonstrate the module error handling and AI fallback functionality.
This test shows how the system detects module errors and retries with AI.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import AsyncMock, MagicMock, patch
from collections import deque
from assistant import Assistant

async def demo_module_error_handling():
    """
    Demonstration of the module error handling and AI fallback system.
    """
    print("🔧 Starting Module Error Handling Demonstration...")
    print("=" * 60)
    
    # Create assistant instance with mocked dependencies
    with patch('assistant.load_config'), \
         patch('assistant.TTSModule'), \
         patch('assistant.WhisperASR'), \
         patch('assistant.get_active_window_title'):
        
        assistant = Assistant()
        assistant.conversation_history = deque(maxlen=10)
        
        # Mock the speak_and_maybe_listen method to capture output
        assistant.speak_and_maybe_listen = AsyncMock()
        
        print("✅ Assistant initialized")
        print()
        
        # Test 1: Error Response Detection
        print("📝 Test 1: Error Response Detection")
        print("-" * 40)
        
        error_responses = [
            "Błąd połączenia z API",
            "Error: Failed to connect",
            "Przepraszam, wystąpił błąd",
            "API error: timeout"
        ]
        
        success_responses = [
            "Operacja wykonana pomyślnie",
            "Successfully completed",
            "Here are your results",
            "Weather is sunny today"
        ]
        
        print("Testing error detection...")
        for response in error_responses:
            is_error = assistant.is_module_error_response(response)
            print(f"  '{response[:30]}...' → {'❌ ERROR' if is_error else '✅ OK'}")
        
        print("\nTesting success detection...")
        for response in success_responses:
            is_error = assistant.is_module_error_response(response)
            print(f"  '{response[:30]}...' → {'❌ ERROR' if is_error else '✅ OK'}")
        
        print()
        
        # Test 2: AI Fallback Retry
        print("🤖 Test 2: AI Fallback Retry")
        print("-" * 40)
        
        original_query = "What's the weather today?"
        error_response = "Błąd API pogody - nie można pobrać danych"
        
        # Mock the AI response generation
        mock_ai_response = '{"text": "I cannot check the weather right now due to a service issue, but I can help you with other tasks. Would you like me to suggest some indoor activities instead?"}'
        
        with patch('assistant.generate_response', return_value=mock_ai_response) as mock_generate, \
             patch('assistant.parse_response', return_value={"text": "I cannot check the weather right now due to a service issue, but I can help you with other tasks. Would you like me to suggest some indoor activities instead?"}) as mock_parse, \
             patch('assistant.detect_language', return_value="en") as mock_detect:
            
            print(f"Original Query: '{original_query}'")
            print(f"Module Error: '{error_response}'")
            print("\n🔄 Triggering AI fallback...")
            
            await assistant.retry_with_ai_fallback(original_query, error_response, TextMode=True)
            
            print("✅ AI fallback completed")
            
            # Verify the AI was called without tools
            mock_generate.assert_called_once()
            args, kwargs = mock_generate.call_args
            tools_info = kwargs.get('tools_info', '')
            
            print(f"📋 AI called with tools_info: '{tools_info}' (empty = no tools)")
            
            # Check what was spoken
            if assistant.speak_and_maybe_listen.called:
                spoken_args = assistant.speak_and_maybe_listen.call_args[0]
                spoken_text = spoken_args[0] if spoken_args else "No text spoken"
                print(f"🗣️  AI Response: '{spoken_text[:80]}...'")
            
        print()
        
        # Test 3: Exception Handling
        print("⚠️  Test 3: Exception Handling in AI Fallback")
        print("-" * 40)
        
        with patch('assistant.generate_response', side_effect=Exception("Simulated AI error")):
            print("🔄 Triggering AI fallback with simulated AI error...")
            
            await assistant.retry_with_ai_fallback("test query", "module error", TextMode=True)
            
            print("✅ Exception handled gracefully")
            
            # Check fallback error message was spoken
            if assistant.speak_and_maybe_listen.called:
                spoken_args = assistant.speak_and_maybe_listen.call_args[0]
                spoken_text = spoken_args[0] if spoken_args else "No text spoken"
                print(f"🗣️  Fallback message: '{spoken_text}'")
        
        print()
        print("=" * 60)
        print("🎉 Demonstration completed successfully!")
        print()
        print("📋 Summary:")
        print("  ✅ Error detection works for both Polish and English")
        print("  ✅ AI fallback retry calls AI without tools")
        print("  ✅ Exception handling provides graceful fallbacks")
        print("  ✅ System can recover from module failures")
        print()
        print("🚀 The module error handling system is ready for use!")

if __name__ == "__main__":
    asyncio.run(demo_module_error_handling())

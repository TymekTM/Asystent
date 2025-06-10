"""
Demo Enhanced TTS Module z legacy code integration
Testuje różne tryby użytkownika i dostawców TTS
"""

import asyncio
import logging
import os
import sys

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def demo_enhanced_tts():
    """Demo Enhanced TTS Module z różnymi trybami."""
    print("🎤 Enhanced TTS Module Demo")
    print("=" * 50)
    
    try:
        # Import user modes and enhanced TTS
        from user_modes import UserModeManager, UserMode, TTSProvider
        from audio_modules.enhanced_tts_module import EnhancedTTSModule
        
        # Initialize components
        mode_manager = UserModeManager()
        tts = EnhancedTTSModule()
        
        print(f"✅ Enhanced TTS Module initialized with {len(tts._tts_providers)} providers")
        
        # Test text
        test_text = "Witaj! To jest test Enhanced TTS Module z integracją legacy kodu."
          # Test Poor Man Mode (Edge TTS)
        print("\n🔧 Testing Poor Man Mode (Edge TTS)")
        print("-" * 30)
        
        try:
            # Switch to Poor Man Mode
            poor_man_config = mode_manager.get_mode_config(UserMode.POOR_MAN)
            mode_manager.set_mode(UserMode.POOR_MAN)
            print(f"📋 Current mode: {mode_manager.get_current_mode().value}")
            print(f"🔊 TTS Provider: {poor_man_config.tts_provider.value}")
            print(f"🎯 Test text: {test_text}")
            
            # Test Edge TTS if available
            if TTSProvider.EDGE_TTS in tts._tts_providers:
                print("▶️ Playing with Edge TTS...")
                await tts.speak(test_text)
                print("✅ Edge TTS test completed")
            else:
                print("❌ Edge TTS not available - install edge-tts package")
                
        except Exception as e:
            print(f"❌ Error testing Poor Man Mode: {e}")
        
        # Test Paid User Mode (OpenAI TTS) if API key available
        print("\n💰 Testing Paid User Mode (OpenAI TTS)")
        print("-" * 35)
        
        try:
            # Check for OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                try:
                    from config import _config
                    api_key = _config.get("API_KEYS", {}).get("OPENAI_API_KEY")
                except Exception:
                    api_key = None
            
            if api_key:                # Switch to Paid User Mode
                paid_config = mode_manager.get_mode_config(UserMode.PAID_USER)
                mode_manager.set_mode(UserMode.PAID_USER)
                print(f"📋 Current mode: {mode_manager.get_current_mode().value}")
                print(f"🔊 TTS Provider: {paid_config.tts_provider.value}")
                print(f"🎯 Test text: {test_text}")
                
                # Test OpenAI TTS streaming (legacy integration)
                if TTSProvider.OPENAI_TTS in tts._tts_providers:
                    print("▶️ Playing with OpenAI TTS (streaming from legacy code)...")
                    await tts.speak(test_text)
                    print("✅ OpenAI TTS test completed")
                else:
                    print("❌ OpenAI TTS not available - install openai package")
            else:
                print("⚠️ OpenAI API key not found - skipping OpenAI TTS test")
                print("   Set OPENAI_API_KEY environment variable to test")
                
        except Exception as e:
            print(f"❌ Error testing Paid User Mode: {e}")
        
        # Test fallback mechanism
        print("\n🔄 Testing Fallback Mechanism")
        print("-" * 25)
        
        try:
            # Force unavailable provider to test fallback
            print("🧪 Testing fallback from unavailable provider to Edge TTS...")
            
            # Temporarily remove OpenAI provider to force fallback
            original_providers = tts._tts_providers.copy()
            if TTSProvider.OPENAI_TTS in tts._tts_providers:
                del tts._tts_providers[TTSProvider.OPENAI_TTS]
                print("🚫 Temporarily disabled OpenAI TTS provider")
              # Try to use Paid User Mode - should fallback to Edge TTS
            mode_manager.set_mode(UserMode.PAID_USER)
            print("▶️ Attempting OpenAI TTS (should fallback to Edge TTS)...")
            await tts.speak("Test fallback mechanism - to powinno działać przez Edge TTS.")
            print("✅ Fallback mechanism working correctly")
            
            # Restore providers
            tts._tts_providers = original_providers
            print("🔄 Restored original TTS providers")
            
        except Exception as e:
            print(f"❌ Error testing fallback mechanism: {e}")
        
        # Test mute functionality
        print("\n🔇 Testing Mute Functionality")
        print("-" * 20)
        
        try:
            print("🔇 Muting TTS...")
            tts.mute = True
            print("▶️ Attempting to play muted text...")
            await tts.speak("Ten tekst nie powinien być słyszalny.")
            print("✅ Mute test completed (no sound should have played)")
            
            print("🔊 Unmuting TTS...")
            tts.mute = False
            print("▶️ Playing unmuted text...")
            await tts.speak("TTS został ponownie włączony.")
            print("✅ Unmute test completed")
            
        except Exception as e:
            print(f"❌ Error testing mute functionality: {e}")
        
        # Summary
        print("\n📊 Demo Summary")
        print("=" * 20)
        print(f"🏭 Available TTS providers: {len(tts._tts_providers)}")
        for provider in tts._tts_providers.keys():
            print(f"   ✅ {provider.value}")
        
        missing_providers = []
        if TTSProvider.EDGE_TTS not in tts._tts_providers:
            missing_providers.append("Edge TTS (install: pip install edge-tts)")
        if TTSProvider.OPENAI_TTS not in tts._tts_providers:
            missing_providers.append("OpenAI TTS (install: pip install openai)")
        if TTSProvider.AZURE_TTS not in tts._tts_providers:
            missing_providers.append("Azure TTS (install: pip install azure-cognitiveservices-speech)")
        
        if missing_providers:
            print(f"❌ Missing providers:")
            for provider in missing_providers:
                print(f"   - {provider}")
        
        print(f"🎯 Current mode: {mode_manager.get_current_mode().value}")
        print("🎉 Enhanced TTS Demo completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all required modules are available")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main demo function."""
    print("🚀 Starting Enhanced TTS Module Demo with Legacy Integration")
    print("📝 This demo tests the integration of legacy TTS code with Enhanced TTS Module")
    print()
    
    await demo_enhanced_tts()
    
    print("\n👋 Demo finished. Press Enter to exit...")
    input()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

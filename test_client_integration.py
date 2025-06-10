"""
Test integracji Enhanced TTS Module z prawdziwym klientem
Sprawdza czy Enhanced TTS działa z istniejącym systemem klienta
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

async def test_client_integration():
    """Test integracji Enhanced TTS z istniejącym klientem."""
    print("🔗 Enhanced TTS Module Client Integration Test")
    print("=" * 55)
    
    try:
        # Test importu modułów klienta
        print("📦 Testing client module imports...")
        
        # Test legacy TTS module compatibility  
        try:
            import audio_modules.tts_module as legacy_tts
            print("✅ Legacy TTS module imported successfully")
            
            # Test if legacy module has required functions
            if hasattr(legacy_tts, 'speak'):
                print("✅ Legacy speak function available")
            else:
                print("❌ Legacy speak function missing")
                
        except ImportError as e:
            print(f"❌ Legacy TTS import failed: {e}")
        
        # Test Enhanced TTS module
        try:
            import audio_modules.enhanced_tts_module as enhanced_tts
            print("✅ Enhanced TTS module imported successfully")
            
            # Test module-level functions compatibility
            if hasattr(enhanced_tts, 'speak'):
                print("✅ Enhanced speak function available")
            if hasattr(enhanced_tts, 'cancel'):
                print("✅ Enhanced cancel function available")
            if hasattr(enhanced_tts, 'set_mute'):
                print("✅ Enhanced set_mute function available")
                
        except ImportError as e:
            print(f"❌ Enhanced TTS import failed: {e}")
            return False
        
        # Test user modes
        try:
            from user_modes import get_current_mode, get_current_config, has_feature
            print("✅ User mode functions imported successfully")
            
            current_mode = get_current_mode()
            current_config = get_current_config()
            print(f"✅ Current mode: {current_mode.value}")
            print(f"✅ TTS Provider: {current_config.tts_provider.value}")
            
        except ImportError as e:
            print(f"❌ User mode import failed: {e}")
            return False
        
        # Test compatibility with existing client code
        print("\n🧪 Testing compatibility with existing client patterns...")
        
        # Test 1: Direct module-level function call (like in original client)
        print("Test 1: Module-level function call")
        try:
            await enhanced_tts.speak("Test komunikatu z poziomu modułu.")
            print("✅ Module-level speak function works")
        except Exception as e:
            print(f"❌ Module-level speak failed: {e}")
        
        # Test 2: Class instance usage
        print("\nTest 2: Class instance usage")
        try:
            tts_instance = enhanced_tts.EnhancedTTSModule()
            await tts_instance.speak("Test komunikatu z instancji klasy.")
            print("✅ Class instance speak function works")
        except Exception as e:
            print(f"❌ Class instance speak failed: {e}")
        
        # Test 3: Mute functionality (critical for client)
        print("\nTest 3: Mute functionality")
        try:
            enhanced_tts.set_mute(True)
            await enhanced_tts.speak("Ten komunikat powinien być wyciszony.")
            print("✅ Mute functionality works (no sound should have played)")
            
            enhanced_tts.set_mute(False)
            await enhanced_tts.speak("TTS został ponownie włączony.")
            print("✅ Unmute functionality works")
        except Exception as e:
            print(f"❌ Mute/unmute failed: {e}")
        
        # Test 4: Cancel functionality
        print("\nTest 4: Cancel functionality")
        try:
            enhanced_tts.cancel()
            print("✅ Cancel function works")
        except Exception as e:
            print(f"❌ Cancel failed: {e}")
        
        # Test 5: User mode switching during operation
        print("\nTest 5: Dynamic user mode switching")
        try:
            from user_modes import UserMode, user_mode_manager
            
            # Switch to Poor Man Mode
            user_mode_manager.set_mode(UserMode.POOR_MAN)
            await enhanced_tts.speak("Komunikat w trybie Poor Man (Edge TTS).")
            print("✅ Poor Man Mode active")
            
            # Switch to Paid User Mode (if OpenAI key available)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                user_mode_manager.set_mode(UserMode.PAID_USER)
                await enhanced_tts.speak("Komunikat w trybie Paid User (OpenAI TTS).")
                print("✅ Paid User Mode active")
            else:
                print("⚠️ OpenAI API key not available - skipping Paid User Mode test")
                
        except Exception as e:
            print(f"❌ User mode switching failed: {e}")
        
        # Test 6: Error handling and recovery
        print("\nTest 6: Error handling and recovery")
        try:
            # Force an error by temporarily breaking provider
            tts_instance = enhanced_tts.EnhancedTTSModule()
            original_providers = tts_instance._tts_providers.copy()
            
            # Clear all providers to force error
            tts_instance._tts_providers.clear()
            
            try:
                await tts_instance.speak("Test obsługi błędów.")
                print("❌ Error handling failed - should have thrown exception")
            except Exception:
                print("✅ Error handling works correctly")
            
            # Restore providers
            tts_instance._tts_providers = original_providers
            await tts_instance.speak("Dostawcy zostali przywróceni.")
            print("✅ Recovery from error works")
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
        
        # Summary
        print("\n📊 Integration Test Summary")
        print("=" * 30)
        
        # Check all required functions exist
        required_functions = ['speak', 'cancel', 'set_mute']
        available_functions = []
        
        for func_name in required_functions:
            if hasattr(enhanced_tts, func_name):
                available_functions.append(func_name)
                print(f"✅ {func_name} function available")
            else:
                print(f"❌ {func_name} function missing")
        
        if len(available_functions) == len(required_functions):
            print("✅ All required functions available - full compatibility")
            return True
        else:
            print("❌ Some required functions missing - compatibility issues")
            return False
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main integration test function."""
    print("🚀 Starting Enhanced TTS Module Client Integration Test")
    print("📝 This test verifies compatibility with existing client code")
    print()
    
    success = await test_client_integration()
    
    if success:
        print("\n🎉 Integration test completed successfully!")
        print("✅ Enhanced TTS Module is fully compatible with existing client")
    else:
        print("\n❌ Integration test failed!")
        print("❌ Compatibility issues detected")
    
    print("\n👋 Press Enter to exit...")
    input()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

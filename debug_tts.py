"""
Debug script dla Enhanced TTS Module
Sprawdza stan dostawców TTS i ich dostępność
"""

import logging
import sys
import os

# Setup basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_tts_providers():
    """Debug dostawców TTS."""
    print("🔍 Debug Enhanced TTS Module Providers")
    print("=" * 50)
    
    try:
        # Import dependencies
        print("📦 Checking imports...")
        
        try:
            from edge_tts import Communicate
            print("✅ Edge TTS import successful")
        except ImportError as e:
            print(f"❌ Edge TTS import failed: {e}")
            Communicate = None
        
        try:
            import openai
            print(f"✅ OpenAI import successful (version: {openai.__version__})")
        except ImportError as e:
            print(f"❌ OpenAI import failed: {e}")
            openai = None
        
        try:
            import azure.cognitiveservices.speech as speechsdk
            print("✅ Azure Speech SDK import successful")
        except ImportError as e:
            print(f"❌ Azure Speech SDK import failed: {e}")
            speechsdk = None
        
        # Import user modes
        print("\n🎯 Checking user modes...")
        from user_modes import UserModeManager, UserMode, TTSProvider
        print("✅ User modes imported successfully")
        
        # Initialize Enhanced TTS
        print("\n🎤 Initializing Enhanced TTS Module...")
        from audio_modules.enhanced_tts_module import EnhancedTTSModule
        tts = EnhancedTTSModule()
        
        # Debug providers
        print(f"\n📊 TTS Providers Debug:")
        print(f"   Total providers: {len(tts._tts_providers)}")
        
        for provider_enum, provider_func in tts._tts_providers.items():
            print(f"   ✅ {provider_enum.value} -> {provider_func.__name__}")
        
        # Check TTSProvider enum values
        print(f"\n🔢 TTSProvider enum values:")
        for provider in TTSProvider:
            in_providers = provider in tts._tts_providers
            print(f"   {provider.value}: {'✅' if in_providers else '❌'} {provider}")
        
        # Test mode manager
        print(f"\n⚙️ Mode Manager Debug:")
        mode_manager = UserModeManager()
        current_mode = mode_manager.get_current_mode()
        current_config = mode_manager.get_mode_config()
        
        print(f"   Current mode: {current_mode.value}")
        print(f"   TTS Provider: {current_config.tts_provider.value}")
        print(f"   Whisper Provider: {current_config.whisper_provider.value}")
        
        # Test provider availability for each mode
        print(f"\n🎛️ Provider availability by mode:")
        for mode in UserMode:
            config = mode_manager.get_mode_config(mode)
            provider_available = config.tts_provider in tts._tts_providers
            print(f"   {mode.value}: {config.tts_provider.value} -> {'✅' if provider_available else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_tts_providers()
    input("\n👋 Press Enter to exit...")

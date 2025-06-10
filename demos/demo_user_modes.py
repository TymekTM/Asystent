"""
Demo Script for Enhanced User Mode System
Demonstracja nowego systemu trybów użytkownika
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add project path
sys.path.insert(0, str(Path(__file__).parent))

# Import our new systems
from user_modes import UserMode, get_current_mode, get_current_config
from auth_system import auth_manager, UserRole, Permission
from mode_integrator import user_integrator, authenticate_user_and_setup, speak, check_permission

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_user_modes():
    """Demonstracja systemu trybów użytkownika."""
    
    print("🎯 GAJA Assistant - Enhanced User Mode System Demo")
    print("=" * 50)
    
    # 1. Show available modes
    print("\n📋 Available User Modes:")
    from user_modes import user_mode_manager
    
    for mode, config in user_mode_manager.get_available_modes().items():
        print(f"  • {config.display_name} ({mode.value})")
        print(f"    {config.description}")
        print(f"    TTS: {config.tts_provider.value}, Whisper: {config.whisper_provider.value}")
        print(f"    Max requests/hour: {config.max_requests_per_hour}")
        print()
    
    # 2. Show current mode (default: Poor Man)
    current_mode = get_current_mode()
    current_config = get_current_config()
    print(f"🔧 Current Mode: {current_config.display_name}")
    print(f"   Description: {current_config.description}")
    print(f"   TTS Provider: {current_config.tts_provider.value}")
    print(f"   Whisper Provider: {current_config.whisper_provider.value}")
    print()
    
    # 3. Create demo users if they don't exist
    print("👥 Setting up demo users...")
    
    demo_users = [
        ("user1", "user1@demo.com", "password123", UserRole.USER),
        ("premium1", "premium1@demo.com", "password123", UserRole.PREMIUM),
        ("admin1", "admin1@demo.com", "password123", UserRole.ADMIN),
    ]
    
    for username, email, password, role in demo_users:
        user_id = auth_manager.create_user(username, email, password, role)
        if user_id:
            print(f"   ✅ Created {username} ({role.value})")
        else:
            print(f"   ℹ️  User {username} already exists")
    
    print()
    
    # 4. Demo authentication and mode switching
    print("🔐 Authentication Demo:")
    
    test_users = [
        ("user1", UserMode.POOR_MAN),
        ("premium1", UserMode.PAID_USER),
        ("admin1", UserMode.ENTERPRISE)
    ]
    
    for username, expected_mode in test_users:
        print(f"\n🧪 Testing {username}:")
        
        # Authenticate
        success, message = await authenticate_user_and_setup(username, "password123")
        
        if success:
            print(f"   ✅ {message}")
            
            # Show user info
            user_info = user_integrator.get_user_info()
            if user_info:
                print(f"   👤 User: {user_info['username']} ({user_info['role']})")
                print(f"   🎯 Mode: {user_info['mode_display_name']}")
                print(f"   🔧 Features: {', '.join([k for k, v in user_info['features'].items() if v])}")
            
            # Test TTS if available
            if check_permission(Permission.USE_TTS):
                print("   🔊 Testing TTS...")
                try:
                    success = await speak(f"Hello from {username} in {user_info['current_mode']} mode")
                    if success:
                        print("   ✅ TTS test successful")
                    else:
                        print("   ❌ TTS test failed")
                except Exception as e:
                    print(f"   ⚠️  TTS test error: {e}")
            else:
                print("   ❌ No TTS permission")
            
            # Logout
            user_integrator.logout()
            print("   🚪 Logged out")
            
        else:
            print(f"   ❌ Authentication failed: {message}")
    
    # 5. Mode features comparison
    print("\n📊 Mode Features Comparison:")
    print("-" * 80)
    print(f"{'Feature':<25} {'Poor Man':<12} {'Paid User':<12} {'Enterprise':<12}")
    print("-" * 80)
    
    all_features = set()
    all_configs = {}
    
    for mode in [UserMode.POOR_MAN, UserMode.PAID_USER, UserMode.ENTERPRISE]:
        user_mode_manager.set_mode(mode)
        config = get_current_config()
        all_configs[mode] = config
        all_features.update(config.features.keys())
    
    for feature in sorted(all_features):
        row = f"{feature:<25}"
        for mode in [UserMode.POOR_MAN, UserMode.PAID_USER, UserMode.ENTERPRISE]:
            has_feature = all_configs[mode].features.get(feature, False)
            status = "✅" if has_feature else "❌"
            row += f" {status:<11}"
        print(row)
    
    print("-" * 80)
    
    # 6. Provider information
    print("\n🔧 Provider Configuration:")
    for mode in [UserMode.POOR_MAN, UserMode.PAID_USER, UserMode.ENTERPRISE]:
        config = all_configs[mode]
        print(f"\n{config.display_name}:")
        print(f"  TTS: {config.tts_provider.value}")
        print(f"  Whisper: {config.whisper_provider.value}")
        print(f"  Max requests/hour: {config.max_requests_per_hour}")
        if config.pricing['monthly_cost'] > 0:
            print(f"  Cost: ${config.pricing['monthly_cost']}/month")
        else:
            print(f"  Cost: Free")
    
    # Reset to Poor Man mode
    user_mode_manager.set_mode(UserMode.POOR_MAN)
    
    print("\n🎉 Demo completed! The Enhanced User Mode System is ready.")
    print("\nNext steps:")
    print("1. Install required dependencies: pip install -r requirements_user_modes.txt")
    print("2. For Paid User mode: Set OPENAI_API_KEY environment variable")
    print("3. For Enterprise mode: Set AZURE_SPEECH_KEY environment variable")
    print("4. Start the server and access Web UI for user management")

async def demo_poor_man_mode():
    """Demonstracja Poor Man Mode z Edge TTS."""
    print("\n🆓 Poor Man Mode Demo (Edge TTS)")
    print("=" * 40)
    
    # Ensure we're in Poor Man mode
    from user_modes import user_mode_manager
    user_mode_manager.set_mode(UserMode.POOR_MAN)
    
    # Test texts in different languages
    test_texts = [
        "Witaj! To jest test polskiego głosu Edge TTS.",
        "Hello! This is an English test of Edge TTS.",
        "Dzisiaj jest piękny dzień do testowania nowych funkcji.",
    ]
    
    try:
        # Initialize integrator in Poor Man mode
        from audio_modules.enhanced_tts_module import EnhancedTTSModule
        tts = EnhancedTTSModule()
        
        print("🔊 Testing Edge TTS with different texts...")
        
        for i, text in enumerate(test_texts, 1):
            print(f"   Test {i}: {text}")
            try:
                await tts.speak(text)
                print(f"   ✅ Test {i} completed")
            except Exception as e:
                print(f"   ❌ Test {i} failed: {e}")
            
            # Wait between tests
            await asyncio.sleep(1)
        
        print("✅ Poor Man Mode TTS demo completed!")
        
    except ImportError as e:
        print(f"❌ Edge TTS not available: {e}")
        print("Install with: pip install edge-tts")
    except Exception as e:
        print(f"❌ Demo error: {e}")

async def main():
    """Główna funkcja demo."""
    try:
        await demo_user_modes()
        await demo_poor_man_mode()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

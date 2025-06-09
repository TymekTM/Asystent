#!/usr/bin/env python3
"""
Simple functionality test for GAJA Assistant
Tests core functionality without complex async operations.
"""

import sys
import os
from pathlib import Path

# Add server path to Python path
sys.path.insert(0, str(Path(__file__).parent / "server"))

def test_imports():
    """Test all critical imports."""
    print("🧪 Testing imports...")
    
    try:
        from database_manager import get_database_manager
        print("✅ Database manager import OK")
    except Exception as e:
        print(f"❌ Database manager import failed: {e}")
        return False
    
    try:
        from plugin_manager import PluginManager
        print("✅ Plugin manager import OK")
    except Exception as e:
        print(f"❌ Plugin manager import failed: {e}")
        return False
    
    try:
        from ai_module import AIModule
        print("✅ AI module import OK")
    except Exception as e:
        print(f"❌ AI module import failed: {e}")
        return False
    
    # Test plugin imports
    try:
        from modules.weather_module import get_functions as weather_functions
        from modules.search_module import get_functions as search_functions
        from modules.memory_module import get_functions as memory_functions
        from modules.api_module import get_functions as api_functions
        
        print(f"✅ Plugin imports OK:")
        print(f"  • Weather: {len(weather_functions())} functions")
        print(f"  • Search: {len(search_functions())} functions") 
        print(f"  • Memory: {len(memory_functions())} functions")
        print(f"  • API: {len(api_functions())} functions")
        
    except Exception as e:
        print(f"❌ Plugin imports failed: {e}")
        return False
    
    return True

def test_database():
    """Test database connectivity."""
    print("\n💾 Testing database...")
    
    try:
        from database_manager import get_database_manager
        db = get_database_manager()
        
        # This is synchronous initialization
        print("✅ Database manager created")
        
        # Check if database file exists
        if os.path.exists("gaja_memory.db"):
            print("✅ Database file exists")
        else:
            print("⚠️ Database file not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_plugins_sync():
    """Test plugin function definitions (synchronous)."""
    print("\n🔌 Testing plugin functions...")
    
    try:
        from modules.weather_module import get_functions as weather_functions
        from modules.search_module import get_functions as search_functions
        from modules.memory_module import get_functions as memory_functions
        from modules.api_module import get_functions as api_functions
        
        # Test function definitions
        weather_funcs = weather_functions()
        search_funcs = search_functions()
        memory_funcs = memory_functions()
        api_funcs = api_functions()
        
        print(f"✅ Weather plugin: {len(weather_funcs)} functions")
        for func in weather_funcs:
            print(f"  • {func['name']}: {func['description']}")
        
        print(f"✅ Search plugin: {len(search_funcs)} functions")
        for func in search_funcs:
            print(f"  • {func['name']}: {func['description']}")
        
        print(f"✅ Memory plugin: {len(memory_funcs)} functions")
        for func in memory_funcs:
            print(f"  • {func['name']}: {func['description']}")
        
        print(f"✅ API plugin: {len(api_funcs)} functions")
        for func in api_funcs:
            print(f"  • {func['name']}: {func['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Plugin test failed: {e}")
        return False

def test_client_imports():
    """Test client-side imports."""
    print("\n📱 Testing client imports...")
    
    # Add client path
    sys.path.insert(0, str(Path(__file__).parent / "client"))
    
    try:
        from audio_modules.overlay import create_overlay
        print("✅ Overlay module import OK")
    except Exception as e:
        print(f"❌ Overlay import failed: {e}")
        return False
    
    try:
        from audio_modules.wakeword_detector import create_wakeword_detector
        print("✅ Wakeword detector import OK")
    except Exception as e:
        print(f"❌ Wakeword detector import failed: {e}")
        return False
    
    try:
        from audio_modules.whisper_asr import create_whisper_asr
        print("✅ Whisper ASR import OK")
    except Exception as e:
        print(f"❌ Whisper ASR import failed: {e}")
        return False
    
    return True

def test_configuration():
    """Test configuration files."""
    print("\n⚙️ Testing configuration...")
    
    server_config = Path("server/server_config.json")
    client_config = Path("client/client_config.json")
    
    if server_config.exists():
        print("✅ Server config exists")
    else:
        print("⚠️ Server config missing")
    
    if client_config.exists():
        print("✅ Client config exists")
    else:
        print("⚠️ Client config missing")
    
    return True

def print_summary(tests):
    """Print test summary."""
    print("\n📋 === TEST SUMMARY ===")
    
    passed = sum(1 for result in tests.values() if result)
    total = len(tests)
    
    print(f"🎯 Total tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    
    if total > 0:
        success_rate = (passed / total) * 100
        print(f"📈 Success rate: {success_rate:.1f}%")
    
    print("\n📝 Detailed results:")
    for test_name, result in tests.items():
        status = "✅" if result else "❌"
        print(f"  {status} {test_name}")

def main():
    """Run simple functionality tests."""
    print("🧪 GAJA Assistant - Simple Functionality Test")
    print("=" * 50)
    
    tests = {}
    
    # Run tests
    tests["Imports"] = test_imports()
    tests["Database"] = test_database()
    tests["Plugin Functions"] = test_plugins_sync()
    tests["Client Imports"] = test_client_imports()
    tests["Configuration"] = test_configuration()
    
    # Print summary
    print_summary(tests)
    
    if all(tests.values()):
        print("\n🎉 All tests passed! System is ready.")
    else:
        print("\n⚠️ Some tests failed. Check the details above.")

if __name__ == "__main__":
    main()

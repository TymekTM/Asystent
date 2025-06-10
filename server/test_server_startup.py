"""
Quick server startup test
Szybki test uruchomienia serwera z nowymi modułami
"""

import asyncio
import sys
from pathlib import Path

# Add server path
sys.path.insert(0, str(Path(__file__).parent))

from server_main import ServerApp

async def test_server_startup():
    """Test uruchomienia serwera z nowymi modułami."""
    print("🚀 Testing Server Startup with New Modules")
    print("=" * 50)
    
    try:
        # Create server app
        server_app = ServerApp()
        
        # Initialize
        print("📦 Initializing server components...")
        await server_app.initialize()
        
        print("✅ Server initialization completed successfully!")
        
        # Check components
        print("\n🔍 Checking initialized components:")
        print(f"   - Config loaded: {server_app.config is not None}")
        print(f"   - Database manager: {server_app.db_manager is not None}")
        print(f"   - AI module: {server_app.ai_module is not None}")
        print(f"   - Function system: {server_app.function_system is not None}")
        print(f"   - Onboarding module: {server_app.onboarding_module is not None}")
        print(f"   - Plugin monitor: {server_app.plugin_monitor is not None}")
        print(f"   - Web UI: {server_app.web_ui is not None}")
        
        # Check plugin manager
        if hasattr(server_app, 'plugin_manager'):
            pm = server_app.plugin_manager
            print(f"   - Plugin manager functions: {len(pm.function_registry) if hasattr(pm, 'function_registry') else 0}")
        
        print("\n✅ All components initialized successfully!")
        
        # Cleanup
        if hasattr(server_app, 'plugin_monitor'):
            await server_app.plugin_monitor.stop_monitoring()
        
        print("🎉 Server startup test passed!")
        
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_server_startup())
    sys.exit(0 if success else 1)

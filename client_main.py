#!/usr/bin/env python3
"""
GAJA Assistant Client Entry Point
Dedicated entry point for client-only builds with dependency management.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add client path
sys.path.insert(0, str(Path(__file__).parent / "client"))
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ensure_dependencies():
    """Ensure all required dependencies are installed."""
    try:
        from dependency_manager import get_dependency_manager
        
        dm = get_dependency_manager()
        
        # Check if installation is needed
        if await dm.check_installation_needed():
            print("🔧 First run detected - downloading required dependencies...")
            print("   This may take a few minutes depending on your internet connection.")
            print("   The application will be much faster on subsequent runs.")
            
            success = await dm.install_dependencies()
            if not success:
                print("❌ Failed to install required dependencies!")
                print("   Please check your internet connection and try again.")
                return False
            
            print("✅ All dependencies installed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Dependency management failed: {e}")
        print(f"❌ Dependency error: {e}")
        return False

def main():
    """Client entry point with dependency management."""
    print("🚀 GAJA Assistant Client")
    print("=" * 40)
    
    # Run dependency check first
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        deps_ok = loop.run_until_complete(ensure_dependencies())
        if not deps_ok:
            print("\n❌ Cannot start client due to dependency issues.")
            input("Press Enter to exit...")
            return 1
        
        # Now start the actual client
        from client.client_main import main as client_main
        return client_main()
        
    except KeyboardInterrupt:
        print("\n👋 Client shutdown by user")
        return 0
    except Exception as e:
        logger.error(f"Client startup failed: {e}")
        print(f"\n❌ Client error: {e}")
        input("Press Enter to exit...")
        return 1
    finally:
        loop.close()

if __name__ == "__main__":
    sys.exit(main())

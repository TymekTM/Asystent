#!/usr/bin/env python3
"""
Trigger manual wakeword test with the running client
"""

import asyncio
import sys
import os
from pathlib import Path

# Add client directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the client module to access the running instance
from client_main import *

async def trigger_manual_test():
    """Trigger a manual wakeword test with the running client system"""
    
    print("🎯 Simulating manual wakeword detection...")
    
    # We'll need to find the running client instance
    # For now, let's create a simple message to simulate wakeword trigger
    
    test_query = "Jak się masz?"
    
    print(f"📢 Simulating voice command: {test_query}")
    
    # This would normally be called by the wakeword detector
    # but we'll call it directly for testing
    
    # NOTE: This would require access to the running client instance
    # For now, just print what would happen
    
    print("ℹ️  In a real scenario, this would:")
    print("1. Be detected by wakeword detector")
    print("2. Trigger ASR transcription")
    print("3. Send query to server via WebSocket")
    print("4. Receive AI response")
    print("5. Play TTS audio")
    print("6. Update overlay status")
    
    print("✅ Manual test simulation completed")

if __name__ == "__main__":
    asyncio.run(trigger_manual_test())

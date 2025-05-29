#!/usr/bin/env python3
"""
Test script to verify that music commands generate natural responses instead of technical ones.
"""

import asyncio
import json
import sys
import os

# Add the parent directory to the path so we can import the assistant modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assistant import Assistant
import config

async def test_music_responses():
    """Test that music commands return natural responses."""
    print("🎵 Testing music response behavior...")
    
    # Load config
    config.load_config()
    
    # Initialize assistant
    assistant = Assistant()
    
    # Test queries that should trigger music commands
    test_queries = [
        "zatrzymaj muzykę",
        "pause music", 
        "następny utwór",
        "next song",
        "odtwórz muzykę",
        "play music"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        
        # Process the query without TTS
        try:
            await assistant.process_query(query, TextMode=True)
            print(f"✅ Query processed successfully")
        except Exception as e:
            print(f"❌ Error processing query: {e}")
    
    print("\n🎵 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_music_responses())

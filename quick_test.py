#!/usr/bin/env python3
"""
Test połączenia klient-serwer z zapisem do pliku
"""

import asyncio
import json
import websockets
import sys
from datetime import datetime

async def test_simple():
    log_file = "test_client.log"
    
    def log(message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        print(log_message.strip())
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_message)
    
    try:
        log("=== GAJA Client Test Started ===")
        uri = "ws://localhost:8000/ws/test_user"
        log(f"Connecting to: {uri}")
        
        async with websockets.connect(uri) as websocket:
            log("✅ Connected successfully!")
            
            # Test 1: Podstawowe zapytanie AI
            test_message = {
                "type": "ai_query",
                "query": "Cześć! To jest test klienta.",
                "context": {"test": True}
            }
            
            await websocket.send(json.dumps(test_message))
            log("✅ Message sent, waiting for response...")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                data = json.loads(response)
                log(f"✅ Response received: {data.get('type', 'unknown')}")
                
                if data.get('type') == 'ai_response':
                    response_text = data.get('response', 'No response')[:200]
                    log(f"AI Response: {response_text}...")
                
            except asyncio.TimeoutError:
                log("⚠️ No response within 15 seconds")
            
            # Test 2: Lista pluginów
            log("Testing plugin list...")
            plugin_message = {"type": "plugin_list"}
            await websocket.send(json.dumps(plugin_message))
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                log(f"✅ Plugin list response: {data.get('type', 'unknown')}")
                
                if data.get('plugins'):
                    plugins = data.get('plugins', {})
                    log(f"Available plugins: {list(plugins.keys())}")
                
            except asyncio.TimeoutError:
                log("⚠️ No plugin response within 5 seconds")
            
            # Test 3: Test pamięci
            log("Testing memory plugin...")
            memory_message = {
                "type": "ai_query",
                "query": "Zapisz w pamięci: Test z prostego klienta",
                "context": {}
            }
            await websocket.send(json.dumps(memory_message))
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)
                log(f"✅ Memory test response: {data.get('type', 'unknown')}")
                
            except asyncio.TimeoutError:
                log("⚠️ No memory response within 10 seconds")
            
            log("=== Test completed successfully ===")
            
    except ConnectionRefusedError:
        log("❌ Connection refused - server not running?")
    except Exception as e:
        log(f"❌ Error: {type(e).__name__}: {e}")
    
    log("=== Test finished ===")

if __name__ == "__main__":
    # Usuń poprzedni log
    try:
        import os
        if os.path.exists("test_client.log"):
            os.remove("test_client.log")
    except:
        pass
    
    asyncio.run(test_simple())

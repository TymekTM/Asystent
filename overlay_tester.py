#!/usr/bin/env python3
"""
OVERLAY STATUS TESTER
=====================
Testuje różne statusy overlay w czasie rzeczywistym
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

class OverlayStatusTester:
    def __init__(self, port=6001):
        self.port = port
        self.connected = False
        self.websocket = None
    
    async def connect(self):
        """Connect to client WebSocket."""
        ports = [6001, 6000]
        
        for port in ports:
            try:
                uri = f"ws://localhost:{port}"
                print(f"🔗 Trying to connect to {uri}")
                self.websocket = await websockets.connect(uri)
                self.port = port
                self.connected = True
                print(f"✅ Connected to client WebSocket on port {port}")
                return True
            except Exception as e:
                print(f"❌ Failed to connect to port {port}: {e}")
                continue
        
        print("❌ Could not connect to any WebSocket port")
        return False
    
    async def send_status(self, status_data):
        """Send status update to overlay."""
        if not self.connected or not self.websocket:
            print("❌ Not connected to WebSocket")
            return False
        
        message = {
            "type": "status",
            "data": status_data,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            print(f"📤 Sent: {status_data['status']} - {status_data.get('text', '')}")
            return True
        except Exception as e:
            print(f"❌ Error sending status: {e}")
            self.connected = False
            return False
    
    async def test_status_sequence(self):
        """Test sequence of different overlay states."""
        if not await self.connect():
            return False
        
        # Test sequence of statuses
        test_statuses = [
            {
                "status": "ready",
                "text": "Assistant gotowy",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "show_content": True,
                "monitoring": True
            },
            {
                "status": "słucham",
                "text": "Słucham...",
                "is_listening": True,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "show_content": False,
                "monitoring": True
            },
            {
                "status": "wake_word",
                "text": "Wykryto słowo kluczowe!",
                "is_listening": True,
                "is_speaking": False,
                "wake_word_detected": True,
                "overlay_visible": True,
                "show_content": True,
                "monitoring": True
            },
            {
                "status": "myślę",
                "text": "Przetwarzam zapytanie...",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "show_content": True,
                "monitoring": True
            },
            {
                "status": "mówię",
                "text": "Oto moja odpowiedź na Twoje pytanie",
                "is_listening": False,
                "is_speaking": True,
                "wake_word_detected": False,
                "overlay_visible": True,
                "show_content": True,
                "monitoring": True
            },
            {
                "status": "error",
                "text": "Wystąpił błąd połączenia",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "show_content": True,
                "monitoring": False,
                "critical": True
            },
            {
                "status": "ready",
                "text": "Wszystko w porządku, gotowy do pracy",
                "is_listening": False,
                "is_speaking": False,
                "wake_word_detected": False,
                "overlay_visible": True,
                "show_content": True,
                "monitoring": True
            }
        ]
        
        print(f"\n🎭 Starting overlay status test sequence...")
        print("=" * 50)
        
        for i, status in enumerate(test_statuses, 1):
            print(f"\n📺 Test {i}/{len(test_statuses)}: {status['status'].upper()}")
            print(f"   Text: {status['text']}")
            print(f"   Listening: {status['is_listening']}")
            print(f"   Speaking: {status['is_speaking']}")
            print(f"   Wake Word: {status['wake_word_detected']}")
            print(f"   Show Content: {status['show_content']}")
            
            success = await self.send_status(status)
            if not success:
                print("❌ Failed to send status - stopping test")
                break
            
            print("⏱️ Displaying for 5 seconds...")
            await asyncio.sleep(5)
        
        print(f"\n🎉 Test sequence completed!")
        return True
    
    async def interactive_test(self):
        """Interactive overlay testing."""
        if not await self.connect():
            return False
        
        print(f"\n🎮 INTERACTIVE OVERLAY TESTER")
        print("=" * 40)
        print("Available commands:")
        print("  1 - Ready state")
        print("  2 - Listening")
        print("  3 - Wake word detected") 
        print("  4 - Processing")
        print("  5 - Speaking")
        print("  6 - Error state")
        print("  7 - Custom text")
        print("  s - Run status sequence")
        print("  q - Quit")
        print("=" * 40)
        
        while True:
            try:
                cmd = input("\n🎯 Enter command: ").strip().lower()
                
                if cmd == 'q':
                    break
                elif cmd == 's':
                    await self.test_status_sequence()
                    continue
                elif cmd == '1':
                    status = {
                        "status": "ready",
                        "text": "Assistant gotowy",
                        "is_listening": False,
                        "is_speaking": False,
                        "wake_word_detected": False,
                        "overlay_visible": True,
                        "show_content": True
                    }
                elif cmd == '2':
                    status = {
                        "status": "słucham",
                        "text": "",
                        "is_listening": True,
                        "is_speaking": False,
                        "wake_word_detected": False,
                        "overlay_visible": True,
                        "show_content": False
                    }
                elif cmd == '3':
                    status = {
                        "status": "wake_word",
                        "text": "Wykryto słowo kluczowe!",
                        "is_listening": True,
                        "is_speaking": False,
                        "wake_word_detected": True,
                        "overlay_visible": True,
                        "show_content": True
                    }
                elif cmd == '4':
                    status = {
                        "status": "myślę",
                        "text": "Przetwarzam zapytanie...",
                        "is_listening": False,
                        "is_speaking": False,
                        "wake_word_detected": False,
                        "overlay_visible": True,
                        "show_content": True
                    }
                elif cmd == '5':
                    status = {
                        "status": "mówię",
                        "text": "Oto moja odpowiedź",
                        "is_listening": False,
                        "is_speaking": True,
                        "wake_word_detected": False,
                        "overlay_visible": True,
                        "show_content": True
                    }
                elif cmd == '6':
                    status = {
                        "status": "error",
                        "text": "Wystąpił błąd",
                        "is_listening": False,
                        "is_speaking": False,
                        "wake_word_detected": False,
                        "overlay_visible": True,
                        "show_content": True,
                        "critical": True
                    }
                elif cmd == '7':
                    custom_text = input("Enter custom text: ")
                    status = {
                        "status": "custom",
                        "text": custom_text,
                        "is_listening": False,
                        "is_speaking": False,
                        "wake_word_detected": False,
                        "overlay_visible": True,
                        "show_content": True
                    }
                else:
                    print("❌ Unknown command")
                    continue
                
                await self.send_status(status)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("👋 Interactive tester stopped")
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("🔗 Disconnected from WebSocket")

async def main():
    """Main function."""
    print("🎯 OVERLAY STATUS TESTER")
    print("=" * 30)
    print("This tool tests overlay status updates")
    print("Make sure client WebSocket is running first!")
    print("=" * 30)
    
    tester = OverlayStatusTester()
    
    try:
        # Ask user what to do
        choice = input("\nChoose test mode:\n  1 - Auto sequence\n  2 - Interactive\nChoice: ").strip()
        
        if choice == '1':
            await tester.test_status_sequence()
        elif choice == '2':
            await tester.interactive_test()
        else:
            print("❌ Invalid choice")
    
    except KeyboardInterrupt:
        print("\n⏸️ Test interrupted")
    finally:
        await tester.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

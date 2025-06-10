#!/usr/bin/env python3
"""
Test HTTP server for overlay testing.
Symuluje API klienta z różnymi statusami.
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

class TestOverlayHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.test_status = "idle"
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Symuluj różne statusy
            current_time = int(time.time())
            cycle = current_time % 20  # 20-sekundowy cykl
            
            if cycle < 5:
                # Idle state
                status_data = {
                    "status": "Waiting...",
                    "text": "",
                    "is_listening": False,
                    "is_speaking": False,
                    "wake_word_detected": False
                }
            elif cycle < 8:
                # Wake word detected
                status_data = {
                    "status": "Wake word detected!",
                    "text": "Gaja detected",
                    "is_listening": False,
                    "is_speaking": False,
                    "wake_word_detected": True
                }
            elif cycle < 12:
                # Listening
                status_data = {
                    "status": "Listening...",
                    "text": "Słucham...",
                    "is_listening": True,
                    "is_speaking": False,
                    "wake_word_detected": False
                }
            elif cycle < 16:
                # Processing
                status_data = {
                    "status": "Processing...",
                    "text": "Myślę...",
                    "is_listening": False,
                    "is_speaking": False,
                    "wake_word_detected": False
                }
            else:
                # Speaking
                status_data = {
                    "status": "Speaking...",
                    "text": "To jest test overlay. Sprawdzam czy wszystko działa poprawnie!",
                    "is_listening": False,
                    "is_speaking": True,
                    "wake_word_detected": False
                }
            
            response = json.dumps(status_data, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            print(f"[Test Server] Sent status: {status_data['status']}")
            
        elif parsed_path.path == '/status/stream':
            # SSE endpoint
            self.send_response(200)
            self.send_header('Content-type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Send test SSE data
            for i in range(10):
                if i % 3 == 0:
                    data = {
                        "status": "Listening...",
                        "text": f"SSE Test {i}",
                        "is_listening": True,
                        "is_speaking": False,
                        "wake_word_detected": False
                    }
                elif i % 3 == 1:
                    data = {
                        "status": "Speaking...",
                        "text": f"Mówię przez SSE test {i}",
                        "is_listening": False,
                        "is_speaking": True,
                        "wake_word_detected": False
                    }
                else:
                    data = {
                        "status": "Idle",
                        "text": "",
                        "is_listening": False,
                        "is_speaking": False,
                        "wake_word_detected": False
                    }
                
                event_data = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                self.wfile.write(event_data.encode('utf-8'))
                self.wfile.flush()
                time.sleep(2)
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP logs
        pass

def run_test_server():
    server = HTTPServer(('localhost', 5001), TestOverlayHandler)
    print("🧪 Test Overlay Server running on http://localhost:5001")
    print("📡 Testing URLs:")
    print("   http://localhost:5001/api/status - Status endpoint")
    print("   http://localhost:5001/status/stream - SSE stream")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.shutdown()

if __name__ == "__main__":
    run_test_server()

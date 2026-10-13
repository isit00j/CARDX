from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardx_core import extrapolate_cards

MAX_BODY_SIZE = 1024 * 1024  # 1 MB Limit

class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self, methods='POST, OPTIONS'):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', methods)
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Telegram-Bot-Api-Secret-Token')

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > MAX_BODY_SIZE:
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Payload Too Large"}).encode('utf-8'))
                return

            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''
            data = json.loads(body) if body else {}
            seed_input = data.get("seed", "")
            count = data.get("count", 10)

            result = extrapolate_cards(seed_input, count=count)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

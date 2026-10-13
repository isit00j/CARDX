from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardx_core import TEMPLATES

class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self, methods='GET, OPTIONS'):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', methods)
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Telegram-Bot-Api-Secret-Token')

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"templates": TEMPLATES}).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

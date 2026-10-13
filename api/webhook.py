from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardx_core import handle_telegram_command

MAX_BODY_SIZE = 1024 * 1024  # 1 MB Limit

class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self, methods='GET, POST, OPTIONS'):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', methods)
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Telegram-Bot-Api-Secret-Token')

    def do_POST(self):
        try:
            # Enforce Telegram Secret Token validation when TELEGRAM_SECRET_TOKEN is set or in production
            secret_token = os.environ.get("TELEGRAM_SECRET_TOKEN")
            is_prod = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
            req_secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token")

            if secret_token or is_prod:
                if not secret_token or req_secret != secret_token:
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Unauthorized webhook request"}).encode('utf-8'))
                    return

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > MAX_BODY_SIZE:
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Payload Too Large"}).encode('utf-8'))
                return

            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''
            update = json.loads(body) if body else {}

            message = update.get("message", {}) or update.get("edited_message", {})
            sender = message.get("from", {})
            sender_id = sender.get("id")

            # Check owner ID if TELEGRAM_OWNER_ID is set in environment
            owner_id = os.environ.get("TELEGRAM_OWNER_ID")
            if owner_id:
                if not sender_id or str(sender_id) != str(owner_id):
                    response_text = "🔒 Unauthorized access. Bot usage is restricted to the owner."
                else:
                    text = message.get("text", "")
                    response_text = handle_telegram_command(text)
            else:
                text = message.get("text", "")
                response_text = handle_telegram_command(text)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "method": "sendMessage",
                "chat_id": message.get("chat", {}).get("id"),
                "text": response_text,
                "parse_mode": "HTML"
            }).encode('utf-8'))
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "note": str(e)}).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "online",
            "bot": "CARDX Telegram Webhook Handler",
            "usage": "POST Telegram webhook update payload to this endpoint"
        }).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

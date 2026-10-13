from http.server import BaseHTTPRequestHandler
import json
import re

def luhn_valid(value):
    total = 0
    for i, char in enumerate(reversed(value)):
        digit = int(char)
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0

def brand_hint(value):
    if value.startswith("4"):
        return "Visa-family prefix"
    if value.startswith(("51", "52", "53", "54", "55")) or (len(value) >= 4 and 2221 <= int(value[:4]) <= 2720):
        return "Mastercard-family prefix"
    if value.startswith(("34", "37")):
        return "Amex-family prefix"
    if value.startswith(("6011", "65")):
        return "Discover-family prefix"
    return "Unknown / other"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            size = min(int(self.headers.get("Content-Length", "0")), 2048)
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            raw = str(data.get("number", ""))
            digits = re.sub(r"\D", "", raw)
            format_valid = bool(re.fullmatch(r"\d{12,19}", digits))
            result = {
                "format_valid": format_valid,
                "luhn_valid": bool(format_valid and luhn_valid(digits)),
                "length": len(digits),
                "brand": brand_hint(digits) if digits else "Unknown"
            }
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            body = b'{"error":"Invalid request"}'
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
    def do_GET(self):
        body = b'{"status":"ok","mode":"sandbox-only"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

from http.server import BaseHTTPRequestHandler
import json
import re

# Deliberately illustrative records, not an authoritative BIN/IIN database.
SAMPLES = {
    "424242": {"brand":"Visa-family prefix","country":"Illustrative only"},
    "555555": {"brand":"Mastercard-family prefix","country":"Illustrative only"},
    "378282": {"brand":"Amex-family prefix","country":"Illustrative only"}
}
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            size = min(int(self.headers.get("Content-Length", "0")), 1024)
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            digits = re.sub(r"\D", "", str(data.get("bin", "")))[:8]
            # Only fixed, published demo prefixes are returned; arbitrary lookups are not performed.
            rec = SAMPLES.get(digits[:6]) if len(digits) >= 6 else None
            result = {"found": bool(rec), "brand": rec["brand"] if rec else "", "country": rec["country"] if rec else "", "note":"Static demo metadata only; not a live issuer lookup."}
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

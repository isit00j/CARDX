import unittest
import json
from io import BytesIO
import cardx_core
from api.check import handler as check_handler
from api.generate import handler as generate_handler
from api.bin import handler as bin_handler
from api.bulk import handler as bulk_handler
from api.extrapolate import handler as extrapolate_handler
from api.templates import handler as templates_handler
from api.settings import handler as settings_handler
from api.export import handler as export_handler
from api.webhook import handler as webhook_handler

class DummyRequest:
    def __init__(self, body_bytes):
        self.rfile = BytesIO(body_bytes)
        self.wfile = BytesIO()
        self.headers = {'Content-Length': str(len(body_bytes))}
        self.response_code = None
        self.response_headers = {}

    def send_response(self, code):
        self.response_code = code

    def send_header(self, keyword, value):
        self.response_headers[keyword] = value

    def end_headers(self):
        pass


def call_api_handler(handler_class, body_dict):
    body_bytes = json.dumps(body_dict).encode('utf-8')
    req = DummyRequest(body_bytes)
    # Instantiate handler using __new__ to skip BaseHTTPRequestHandler.__init__ socket binding
    h = handler_class.__new__(handler_class)
    h.rfile = req.rfile
    h.wfile = req.wfile
    h.headers = req.headers
    h.send_response = req.send_response
    h.send_header = req.send_header
    h.end_headers = req.end_headers
    h.do_POST()

    req.wfile.seek(0)
    response_data = req.wfile.read().decode('utf-8')
    return req.response_code, json.loads(response_data) if response_data else {}


class TestCardXCore(unittest.TestCase):
    def test_luhn_validation(self):
        card = cardx_core.generate_single_card("Visa")
        self.assertTrue(cardx_core.luhn_valid(card["pan"]))
        self.assertFalse(cardx_core.luhn_valid("1234567890123456"))

    def test_generate_cards(self):
        cards = cardx_core.generate_cards(brand="Mastercard", count=5)
        self.assertEqual(len(cards), 5)
        for c in cards:
            self.assertEqual(c["brand"], "Mastercard")
            self.assertTrue(c["luhn_valid"])

    def test_bin_lookup(self):
        info = cardx_core.lookup_bin("400016")
        self.assertEqual(info["bin"], "400016")
        self.assertEqual(info["brand"], "Visa")

    def test_validate_card(self):
        card = cardx_core.generate_single_card("Amex")
        res = cardx_core.validate_card(card["pipe_format"])
        self.assertTrue(res["overall_valid"])
        self.assertEqual(res["brand"], "Amex")

    def test_bulk_check(self):
        cards = cardx_core.generate_cards("Visa", 3)
        cards_text = "\n".join(c["pipe_format"] for c in cards)
        res = cardx_core.bulk_check(cards_text)
        self.assertEqual(res["total"], 3)
        self.assertEqual(res["passed"], 3)


class TestAPIHandlers(unittest.TestCase):
    def test_check_handler(self):
        card = cardx_core.generate_single_card("Visa")
        code, body = call_api_handler(check_handler, {"card": card["pipe_format"]})
        self.assertEqual(code, 200)
        self.assertTrue(body["overall_valid"])

    def test_generate_handler(self):
        code, body = call_api_handler(generate_handler, {"brand": "Visa", "count": 3})
        self.assertEqual(code, 200)
        self.assertEqual(body["count"], 3)
        self.assertEqual(len(body["cards"]), 3)

    def test_bin_handler(self):
        code, body = call_api_handler(bin_handler, {"bin": "400016"})
        self.assertEqual(code, 200)
        self.assertEqual(body["issuer"], "Chase Bank")

    def test_bulk_handler(self):
        card = cardx_core.generate_single_card("Visa")
        code, body = call_api_handler(bulk_handler, {"cards_text": card["pipe_format"]})
        self.assertEqual(code, 200)
        self.assertEqual(body["total"], 1)

    def test_extrapolate_handler(self):
        card = cardx_core.generate_single_card("Visa")
        code, body = call_api_handler(extrapolate_handler, {"seed": card["pan"], "count": 3})
        self.assertEqual(code, 200)
        self.assertEqual(body["count"], 3)

    def test_templates_handler(self):
        req = DummyRequest(b"")
        h = templates_handler.__new__(templates_handler)
        h.rfile = req.rfile
        h.wfile = req.wfile
        h.headers = req.headers
        h.send_response = req.send_response
        h.send_header = req.send_header
        h.end_headers = req.end_headers
        h.do_GET()

        req.wfile.seek(0)
        body = json.loads(req.wfile.read().decode('utf-8'))
        self.assertEqual(req.response_code, 200)
        self.assertIn("templates", body)

    def test_settings_handler(self):
        code, body = call_api_handler(settings_handler, {"default_brand": "Visa"})
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "saved")

    def test_export_handler(self):
        records = [{"pan": "4000161234567890", "brand": "Visa", "expiry": "12/28", "cvv": "123", "status": "PASS"}]
        code, body = call_api_handler(export_handler, {"records": records, "format": "json"})
        self.assertEqual(code, 200)
        self.assertIn("filename", body)

    def test_webhook_handler(self):
        payload = {"update_id": 1, "message": {"text": "/start", "chat": {"id": 12345}}}
        code, body = call_api_handler(webhook_handler, payload)
        self.assertEqual(code, 200)
        self.assertEqual(body["method"], "sendMessage")


if __name__ == '__main__':
    unittest.main()

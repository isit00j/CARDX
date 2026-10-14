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

    def test_generate_cards_bounds(self):
        # Check count clamping (max 100)
        cards = cardx_core.generate_cards(brand="Visa", count=200)
        self.assertEqual(len(cards), 100)

    def test_bin_lookup(self):
        info = cardx_core.lookup_bin("400016")
        self.assertEqual(info["bin"], "400016")
        self.assertEqual(info["brand"], "Visa")

    def test_validate_card(self):
        card = cardx_core.generate_single_card("Amex")
        res = cardx_core.validate_card(card["pipe_format"])
        self.assertTrue(res["overall_valid"])
        self.assertEqual(res["brand"], "Amex")

    def test_validate_card_empty(self):
        res = cardx_core.validate_card("")
        self.assertFalse(res["overall_valid"])
        self.assertIn("error", res)

    def test_extrapolate_cards_validity_and_length(self):
        # Visa seed PAN (16 digits)
        visa_seed = "4000123456789010"
        res = cardx_core.extrapolate_cards(visa_seed, count=5)
        self.assertEqual(res["count"], 5)
        self.assertEqual(res["brand"], "Visa")
        for item in res["extrapolated"]:
            self.assertEqual(len(item["pan"]), 16)
            self.assertTrue(cardx_core.luhn_valid(item["pan"]))
            self.assertEqual(item["brand"], "Visa")

        # Amex seed PAN (15 digits)
        amex_seed = cardx_core.generate_single_card("Amex")["pan"]
        res_amex = cardx_core.extrapolate_cards(amex_seed, count=5)
        self.assertEqual(res_amex["count"], 5)
        self.assertEqual(res_amex["brand"], "Amex")
        for item in res_amex["extrapolated"]:
            self.assertEqual(len(item["pan"]), 15)
            self.assertTrue(cardx_core.luhn_valid(item["pan"]))
            self.assertEqual(item["brand"], "Amex")

    def test_extrapolate_invalid_seed(self):
        res = cardx_core.extrapolate_cards("123")
        self.assertIn("error", res)

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
        # Test JSON format
        code, body = call_api_handler(export_handler, {"records": records, "format": "json"})
        self.assertEqual(code, 200)
        self.assertIn("filename", body)
        self.assertEqual(body["mime_type"], "application/json")

        # Test CSV format
        code_csv, body_csv = call_api_handler(export_handler, {"records": records, "format": "csv"})
        self.assertEqual(code_csv, 200)
        self.assertEqual(body_csv["mime_type"], "text/csv")
        self.assertIn("PAN,Brand,Expiry,CVV,Status,Masked", body_csv["content"])

        # Test TXT format
        code_txt, body_txt = call_api_handler(export_handler, {"records": records, "format": "txt"})
        self.assertEqual(code_txt, 200)
        self.assertEqual(body_txt["mime_type"], "text/plain")
        self.assertIn("4000161234567890|12/28|123", body_txt["content"])

    def test_extrapolated_records_csv_export_status(self):
        # Generate extrapolated records
        extrap_res = cardx_core.extrapolate_cards("4000123456789010", count=2)
        records = extrap_res["extrapolated"]
        self.assertGreaterEqual(len(records), 1)

        # Export as CSV
        code, body = call_api_handler(export_handler, {"records": records, "format": "csv"})
        self.assertEqual(code, 200)
        csv_content = body["content"]
        lines = csv_content.strip().split("\n")
        self.assertGreaterEqual(len(lines), 2)
        # Verify status column for extrapolated records shows "PASS" and not "N/A"
        for line in lines[1:]:
            self.assertIn('"PASS"', line)
            self.assertNotIn('"N/A"', line)

    def test_session_records_collection_and_export_across_all_ops(self):
        session_records = []

        # 1. Card Generation
        _, gen_body = call_api_handler(generate_handler, {"brand": "Visa", "count": 2})
        session_records.extend(gen_body.get("cards", []))

        # 2. Single Card Validation
        _, check_body = call_api_handler(check_handler, {"card": "4000123456789010|12/28|123"})
        session_records.append(check_body)

        # 3. Bulk Validation
        _, bulk_body = call_api_handler(bulk_handler, {"cards_text": "5156761234567890|05/29|456"})
        bulk_records = [r["res"] for r in bulk_body.get("results", []) if "res" in r]
        session_records.extend(bulk_records)

        # 4. Card Extrapolation
        _, extrap_body = call_api_handler(extrapolate_handler, {"seed": "4000123456789010", "count": 2})
        session_records.extend(extrap_body.get("extrapolated", []))

        # Export session records across all 4 operations
        code, body = call_api_handler(export_handler, {"records": session_records, "format": "csv"})
        self.assertEqual(code, 200)
        csv_lines = body["content"].strip().split("\n")
        # Header + 2 gen + 1 check + 1 bulk + 2 extrap = 7 lines
        self.assertEqual(len(csv_lines), 7)

    def test_settings_get_and_post(self):
        # Test GET request
        req = DummyRequest(b"")
        h = settings_handler.__new__(settings_handler)
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
        self.assertIn("generator", body)

        # Test POST payload size limit exceeded (413 Payload Too Large)
        huge_data = "a" * (1024 * 1024 + 100)
        req_huge = DummyRequest(huge_data.encode('utf-8'))
        h_huge = settings_handler.__new__(settings_handler)
        h_huge.rfile = req_huge.rfile
        h_huge.wfile = req_huge.wfile
        h_huge.headers = req_huge.headers
        h_huge.send_response = req_huge.send_response
        h_huge.send_header = req_huge.send_header
        h_huge.end_headers = req_huge.end_headers
        h_huge.do_POST()
        self.assertEqual(req_huge.response_code, 413)

    def test_webhook_handler(self):
        payload = {"update_id": 1, "message": {"text": "/start", "chat": {"id": 12345}}}
        code, body = call_api_handler(webhook_handler, payload)
        self.assertEqual(code, 200)
        self.assertEqual(body["method"], "sendMessage")

    def test_webhook_secret_token_validation(self):
        import os
        os.environ["TELEGRAM_SECRET_TOKEN"] = "my_secret_token"
        try:
            # Test missing secret token header -> 401
            payload = {"update_id": 1, "message": {"text": "/help", "chat": {"id": 12345}}}
            req = DummyRequest(json.dumps(payload).encode('utf-8'))
            h = webhook_handler.__new__(webhook_handler)
            h.rfile = req.rfile
            h.wfile = req.wfile
            h.headers = req.headers
            h.send_response = req.send_response
            h.send_header = req.send_header
            h.end_headers = req.end_headers
            h.do_POST()
            self.assertEqual(req.response_code, 401)

            # Test valid secret token header -> 200
            req2 = DummyRequest(json.dumps(payload).encode('utf-8'))
            req2.headers['X-Telegram-Bot-Api-Secret-Token'] = "my_secret_token"
            h2 = webhook_handler.__new__(webhook_handler)
            h2.rfile = req2.rfile
            h2.wfile = req2.wfile
            h2.headers = req2.headers
            h2.send_response = req2.send_response
            h2.send_header = req2.send_header
            h2.end_headers = req2.end_headers
            h2.do_POST()
            self.assertEqual(req2.response_code, 200)
        finally:
            os.environ.pop("TELEGRAM_SECRET_TOKEN", None)

    def test_webhook_production_secret_enforcement(self):
        import os
        # Ensure TELEGRAM_SECRET_TOKEN is explicitly cleared to test missing secret behavior
        old_secret = os.environ.pop("TELEGRAM_SECRET_TOKEN", None)

        prod_vars = [
            ("VERCEL", "1"),
            ("VERCEL_ENV", "production"),
            ("ENV", "production"),
            ("ENVIRONMENT", "production"),
            ("NODE_ENV", "production")
        ]

        try:
            payload = {"update_id": 1, "message": {"text": "/help", "chat": {"id": 12345}}}
            for env_key, env_val in prod_vars:
                os.environ[env_key] = env_val
                try:
                    req = DummyRequest(json.dumps(payload).encode('utf-8'))
                    h = webhook_handler.__new__(webhook_handler)
                    h.rfile = req.rfile
                    h.wfile = req.wfile
                    h.headers = req.headers
                    h.send_response = req.send_response
                    h.send_header = req.send_header
                    h.end_headers = req.end_headers
                    h.do_POST()
                    self.assertEqual(req.response_code, 401, f"Failed closed check for {env_key}={env_val}")
                finally:
                    os.environ.pop(env_key, None)
        finally:
            if old_secret is not None:
                os.environ["TELEGRAM_SECRET_TOKEN"] = old_secret

    def test_webhook_owner_id_restriction(self):
        import os
        os.environ["TELEGRAM_OWNER_ID"] = "999888"
        try:
            # Test missing or wrong sender ID -> unauthorized message
            payload_wrong = {
                "update_id": 1,
                "message": {"from": {"id": 111222}, "text": "/gen", "chat": {"id": 12345}}
            }
            code, body = call_api_handler(webhook_handler, payload_wrong)
            self.assertEqual(code, 200)
            self.assertIn("Unauthorized access", body["text"])

            # Test valid owner ID -> authorized message
            payload_owner = {
                "update_id": 1,
                "message": {"from": {"id": 999888}, "text": "/help", "chat": {"id": 12345}}
            }
            code2, body2 = call_api_handler(webhook_handler, payload_owner)
            self.assertEqual(code2, 200)
            self.assertIn("CARDX Cyberpunk Toolkit Bot", body2["text"])
        finally:
            os.environ.pop("TELEGRAM_OWNER_ID", None)


if __name__ == '__main__':
    unittest.main()

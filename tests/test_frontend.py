import unittest
import os
import json
import time
import subprocess
from playwright.sync_api import sync_playwright

class TestFrontendSessionCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start background HTTP server serving public/ on port 3000
        cls.server_proc = subprocess.Popen(
            ["python3", "-m", "http.server", "3000", "--directory", "public"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        if cls.server_proc:
            cls.server_proc.terminate()
            cls.server_proc.wait()

    def test_real_browser_session_collection(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:3000")
            page.wait_for_timeout(500)

            # Mock API endpoints so front-end actions execute cleanly
            page.route("**/api/generate", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"count": 2, "cards": [
                    {"pan": "4000161111111111", "brand": "Visa", "pipe_format": "4000161111111111|12/28|123", "formatted": "4000 1611 1111 1111", "masked": "400016xxxxxx1111"},
                    {"pan": "4000162222222222", "brand": "Visa", "pipe_format": "4000162222222222|12/28|123", "formatted": "4000 1622 2222 2222", "masked": "400016xxxxxx2222"}
                ]})
            ))

            page.route("**/api/check", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "pan": "4000123456789010", "brand": "Visa", "formatted": "4000 1234 5678 9010", "masked": "400012xxxxxx9010",
                    "overall_valid": True, "is_luhn_valid": True, "length": 16, "expected_length": 16, "is_length_valid": True,
                    "expiry": "12/28", "is_expiry_valid": True, "cvv": "123", "is_cvv_valid": True,
                    "bin_info": {"issuer": "Chase Bank", "flag": "🇺🇸", "country": "US"}
                })
            ))

            page.route("**/api/bulk", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "total": 1, "passed": 1, "failed": 0,
                    "results": [{
                        "id": 1,
                        "res": {
                            "pan": "5156761234567890", "brand": "Mastercard", "masked": "515676xxxxxx7890",
                            "overall_valid": True, "bin_info": {"issuer": "Citibank", "country": "US"}
                        }
                    }]
                })
            ))

            page.route("**/api/extrapolate", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "seed": "4000123456789010", "brand": "Visa", "count": 1,
                    "extrapolated": [
                        {"pan": "4000169999999999", "brand": "Visa", "pipe_format": "4000169999999999|12/28|123", "masked": "400016xxxxxx9999", "luhn_valid": True, "status": "PASS", "method": "BIN-Extrapolation"}
                    ]
                })
            ))

            # 1. Trigger Card Generator
            page.get_by_role("button", name="⚡ Generate Test Cards").click()
            page.wait_for_timeout(300)

            # 2. Trigger Card Validator
            page.get_by_role("tab", name="✅ Validator").click()
            page.locator("#check-input").fill("4000123456789010|12/28|123")
            page.get_by_role("button", name="🔍 Validate Card Now").click()
            page.wait_for_timeout(300)

            # 3. Trigger Bulk Checker
            page.get_by_role("tab", name="📂 Bulk Checker").click()
            page.locator("#bulk-input").fill("5156761234567890|05/29|456")
            page.get_by_role("button", name="🚀 Run Bulk Validation").click()
            page.wait_for_timeout(300)

            # 4. Trigger Extrapolator
            page.get_by_role("tab", name="🔮 Extrapolator").click()
            page.locator("#extrap-seed").fill("4000123456789010")
            page.get_by_role("button", name="🔮 Extrapolate Cards").click()
            page.wait_for_timeout(300)

            # Retrieve real in-browser appState.lastRecords length and content
            last_records = page.evaluate("window.appState.lastRecords")
            self.assertEqual(len(last_records), 5, "appState.lastRecords should collect 5 records across 4 operations")
            self.assertEqual(last_records[0]["pan"], "4000161111111111")
            self.assertEqual(last_records[1]["pan"], "4000162222222222")
            self.assertEqual(last_records[2]["pan"], "4000123456789010")
            self.assertEqual(last_records[3]["pan"], "5156761234567890")
            self.assertEqual(last_records[4]["pan"], "4000169999999999")

            browser.close()

if __name__ == "__main__":
    unittest.main()

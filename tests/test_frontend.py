import unittest
import os
import json
import time
import subprocess
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class TestFrontendSessionCollection(unittest.TestCase):
    def setUp(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise unittest.SkipTest("Playwright is not installed in the environment.")
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

    def test_generator_unmasked_pan_display_and_copy(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
            page = context.new_page()
            page.goto("http://localhost:3000")
            page.wait_for_timeout(500)

            fake_generated = [
                {"pan": "4000161111111111", "brand": "Visa", "pipe_format": "400016xxxxxx1111|12/28|123", "formatted": "4000 16xx xxxx 1111", "masked": "400016xxxxxx1111", "expiry": "12/28", "cvv": "123"},
                {"pan": "4000162222222222", "brand": "Visa", "pipe_format": "400016xxxxxx2222|12/28|123", "formatted": "4000 16xx xxxx 2222", "masked": "400016xxxxxx2222", "expiry": "12/28", "cvv": "123"}
            ]

            page.route("**/api/generate", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"count": 2, "cards": fake_generated})
            ))

            # 1. Generate test cards with default validator masking ENABLED
            page.get_by_role("button", name="⚡ Generate Test Cards").click()
            page.wait_for_timeout(300)

            gen_results_html = page.locator("#gen-results").inner_html()
            # Verify complete PAN is present and no xxxxx masking appears in generator output
            self.assertIn("4000161111111111", gen_results_html, "Complete synthetic test PAN must appear in generator output DOM")
            self.assertIn("4000162222222222", gen_results_html, "Complete synthetic test PAN must appear in generator output DOM")
            self.assertNotIn("400016xxxxxx1111", gen_results_html, "Masked xxxxx PAN must not appear in generator output DOM")

            # 2. Test individual card Copy button
            first_copy_btn = page.locator("#gen-results .card-item").first.get_by_role("button", name="📋 Copy")
            first_copy_btn.click()
            page.wait_for_timeout(200)

            copied_single = page.evaluate("navigator.clipboard.readText()")
            self.assertEqual(copied_single, "4000161111111111|12/28|123", "Individual card Copy button must copy the complete displayed pipe_format value")

            # 3. Test Copy All button
            copy_all_btn = page.locator("#btn-copy-gen")
            copy_all_btn.click()
            page.wait_for_timeout(200)

            copied_all = page.evaluate("navigator.clipboard.readText()")
            expected_all = "4000161111111111|12/28|123\n4000162222222222|12/28|123"
            self.assertEqual(copied_all, expected_all, "Copy All action must copy all complete generated test values")

            browser.close()

    def test_masked_pan_rendering_no_full_pan_leak(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:3000")
            page.wait_for_timeout(500)

            fake_pan = "4000123456789010"
            page.route("**/api/check", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "pan": fake_pan, "brand": "Visa", "formatted": "4000 1234 5678 9010", "masked": "400012xxxxxx9010",
                    "overall_valid": True, "is_luhn_valid": True, "length": 16, "expected_length": 16, "is_length_valid": True,
                    "expiry": "12/28", "is_expiry_valid": True, "cvv": "123", "is_cvv_valid": True,
                    "bin_info": {"issuer": "Chase Bank", "flag": "🇺🇸", "country": "US"}
                })
            ))

            # 1. Verify with masking ENABLED (default)
            page.get_by_role("tab", name="✅ Validator").click()
            page.locator("#check-input").fill(fake_pan)
            page.get_by_role("button", name="🔍 Validate Card Now").click()
            page.wait_for_timeout(300)

            results_html = page.locator("#check-results").inner_html()
            self.assertNotIn("4000123456789010", results_html, "Full unmasked PAN must not appear in rendered DOM when masking is enabled")
            self.assertNotIn("4000 1234 5678 9010", results_html, "Formatted unmasked PAN must not appear in rendered DOM when masking is enabled")
            self.assertIn("400012xxxxxx9010", results_html, "Masked PAN must be present in rendered DOM when masking is enabled")

            # 2. Toggle masking DISABLED in Settings
            page.get_by_role("tab", name="⚙️ Settings").click()
            page.locator("#setting-mask-output").uncheck()
            page.get_by_role("button", name="💾 Save Configuration").click()
            page.wait_for_timeout(200)

            # Re-run validation with masking DISABLED
            page.get_by_role("tab", name="✅ Validator").click()
            page.get_by_role("button", name="🔍 Validate Card Now").click()
            page.wait_for_timeout(300)

            unmasked_html = page.locator("#check-results").inner_html()
            self.assertIn("4000 1234 5678 9010", unmasked_html, "Formatted PAN should appear in DOM when masking is explicitly disabled")

            browser.close()

    def test_real_frontend_export_flow(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:3000")
            page.wait_for_timeout(500)

            export_payload_holder = []

            def handle_export_route(route):
                request_data = json.loads(route.request.post_data)
                export_payload_holder.append(request_data)
                # Formulate escaped CSV response
                records = request_data.get("records", [])
                csv_lines = ["PAN,Brand,Expiry,CVV,Status,Masked"]
                for r in records:
                    pan = r.get("pan", "")
                    if pan.startswith("="):
                        pan = "'" + pan
                    csv_lines.append(f'"{pan}","{r.get("brand","")}","{r.get("expiry","")}","{r.get("cvv","")}","PASS","{r.get("masked","")}"')
                content = "\n".join(csv_lines)

                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "content": content,
                        "mime_type": "text/csv",
                        "filename": "cardx_export.csv"
                    })
                )

            page.route("**/api/export", handle_export_route)

            page.route("**/api/check", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "pan": "=SUM(1,2)", "brand": "Visa", "formatted": "=SUM(1,2)", "masked": "400012xxxxxx9010",
                    "overall_valid": True, "is_luhn_valid": True, "length": 16, "expected_length": 16, "is_length_valid": True,
                    "expiry": "12/28", "is_expiry_valid": True, "cvv": "123", "is_cvv_valid": True,
                    "bin_info": {"issuer": "Chase Bank", "flag": "🇺🇸", "country": "US"}
                })
            ))

            # 1. Run validation
            page.get_by_role("tab", name="✅ Validator").click()
            page.locator("#check-input").fill("4000123456789010|12/28|123")
            page.get_by_role("button", name="🔍 Validate Card Now").click()
            page.wait_for_timeout(300)

            # 2. Trigger Export UI Action
            page.get_by_role("tab", name="📤 Export").click()
            page.wait_for_timeout(200)

            with page.expect_download() as download_info:
                page.locator("#btn-export-download").click()

            download = download_info.value
            self.assertEqual(download.suggested_filename, "cardx_export.csv")

            # Verify intercepted export request payload
            self.assertEqual(len(export_payload_holder), 1)
            records = export_payload_holder[0]["records"]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["pan"], "=SUM(1,2)")

            browser.close()

if __name__ == "__main__":
    unittest.main()

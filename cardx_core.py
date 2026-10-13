# -*- coding: utf-8 -*-
"""
CARDX Core Logic Engine
Contains card generation, Luhn validation, BIN lookup, bulk processing,
extrapolation, templates, export, and Telegram bot handling.
"""

import random
import re
import json
from datetime import datetime

BRANDS = {
    "Visa": {"prefixes": ["4"], "length": 16},
    "Mastercard": {"prefixes": ["51", "52", "53", "54", "55", "2221"], "length": 16},
    "Amex": {"prefixes": ["34", "37"], "length": 15},
    "Discover": {"prefixes": ["6011", "65"], "length": 16},
    "Diners": {"prefixes": ["36", "300"], "length": 14},
    "JCB": {"prefixes": ["3528", "3589"], "length": 16},
    "UnionPay": {"prefixes": ["62"], "length": 16},
    "Maestro": {"prefixes": ["5018", "5020", "5038"], "length": 16},
}

BIN_DB = [
    {"bin": "400016", "brand": "Visa", "type": "Debit", "level": "Classic", "issuer": "Chase Bank", "country": "US", "flag": "🇺🇸"},
    {"bin": "515676", "brand": "Mastercard", "type": "Credit", "level": "World", "issuer": "Citibank", "country": "US", "flag": "🇺🇸"},
    {"bin": "340005", "brand": "Amex", "type": "Credit", "level": "Gold", "issuer": "American Express", "country": "US", "flag": "🇺🇸"},
    {"bin": "601100", "brand": "Discover", "type": "Credit", "level": "Discover It", "issuer": "Discover Bank", "country": "US", "flag": "🇺🇸"},
    {"bin": "490301", "brand": "Visa", "type": "Debit", "level": "Electron", "issuer": "Revolut", "country": "GB", "flag": "🇬🇧"},
    {"bin": "520473", "brand": "Mastercard", "type": "Prepaid", "level": "Standard", "issuer": "N26", "country": "DE", "flag": "🇩🇪"},
    {"bin": "371449", "brand": "Amex", "type": "Credit", "level": "Platinum", "issuer": "American Express", "country": "GB", "flag": "🇬🇧"},
    {"bin": "621234", "brand": "UnionPay", "type": "Debit", "level": "Gold", "issuer": "Bank of China", "country": "CN", "flag": "🇨🇳"},
    {"bin": "414720", "brand": "Visa", "type": "Credit", "level": "Signature", "issuer": "Capital One", "country": "US", "flag": "🇺🇸"},
    {"bin": "542418", "brand": "Mastercard", "type": "Credit", "level": "Platinum", "issuer": "Barclays Bank", "country": "GB", "flag": "🇬🇧"},
]

TEMPLATES = [
    {"name": "visa-classic", "pattern": "4###############", "description": "Visa 16-digit standard test pattern"},
    {"name": "mastercard-2series", "pattern": "2221##########", "description": "Mastercard 2-series BIN range test pattern"},
    {"name": "amex-corporate", "pattern": "37############", "description": "American Express 15-digit test pattern"},
    {"name": "discover-it", "pattern": "6011############", "description": "Discover 16-digit test pattern"},
    {"name": "full-pipe-format", "pattern": "4###############|12/29|###", "description": "Full pipe format: PAN|MM/YY|CVV"},
]

SETTINGS_DEFAULT = {
    "generator": {
        "default_brand": "Visa",
        "default_count": 10,
        "include_expiry": True,
        "include_cvv": True,
        "expiry_years_ahead": 3
    },
    "validator": {
        "luhn_check": True,
        "brand_detection": True,
        "expiry_check": True,
        "cvv_check": True,
        "mask_output": True
    },
    "export": {
        "default_format": "csv"
    }
}


def only_digits(s: str) -> str:
    """Extract digits from string."""
    return "".join(c for c in str(s) if c.isdigit())


def luhn_check_digit(payload: str) -> int:
    """Compute Luhn check digit for payload digits."""
    digits = [int(d) for d in only_digits(payload)]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10


def luhn_valid(number: str) -> bool:
    """Check if number satisfies Luhn mod-10 algorithm."""
    digits = [int(d) for d in only_digits(number)]
    if len(digits) < 12:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def detect_brand(number: str) -> str:
    """Detect card brand based on PAN digits."""
    d = only_digits(number)
    if not d:
        return "Unknown"

    if d.startswith("4"):
        return "Visa"
    if d.startswith("34") or d.startswith("37"):
        return "Amex"
    if d.startswith("6011") or d.startswith("65"):
        return "Discover"
    if d.startswith("62"):
        return "UnionPay"
    if d.startswith("36") or d.startswith("300"):
        return "Diners"
    if d.startswith("3528") or d.startswith("3589"):
        return "JCB"
    if d.startswith("5018") or d.startswith("5020") or d.startswith("5038"):
        return "Maestro"

    # Mastercard checks
    if any(d.startswith(p) for p in ["51", "52", "53", "54", "55"]):
        return "Mastercard"
    if len(d) >= 4 and 2221 <= int(d[:4]) <= 2720:
        return "Mastercard"

    return "Unknown"


def mask_pan(number: str) -> str:
    """Mask card number showing first 6 and last 4 digits."""
    d = only_digits(number)
    if len(d) < 10:
        return d
    return f"{d[:6]}{'x' * (len(d) - 10)}{d[-4:]}"


def format_pan(number: str) -> str:
    """Format digits with spaces every 4 digits."""
    d = only_digits(number)
    return " ".join(d[i:i + 4] for i in range(0, len(d), 4))


def generate_expiry(years_ahead=3) -> str:
    """Generate random expiry date MM/YY."""
    month = random.randint(1, 12)
    current_year = datetime.now().year % 100
    year = random.randint(current_year + 1, current_year + years_ahead)
    return f"{month:02d}/{year:02d}"


def generate_cvv(brand="Visa") -> str:
    """Generate 3 or 4 digit CVV."""
    length = 4 if brand.lower() == "amex" else 3
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def generate_single_card(brand="Visa", prefix="", custom_length=None):
    """Generate a single valid card number."""
    brand_info = BRANDS.get(brand, BRANDS["Visa"])
    if not prefix:
        prefix = random.choice(brand_info["prefixes"])
    length = custom_length or brand_info["length"]

    needed = length - len(prefix) - 1
    if needed <= 0:
        # Prefix is too long or exact
        body = prefix[:length-1]
    else:
        body = prefix + "".join(str(random.randint(0, 9)) for _ in range(needed))

    check_digit = luhn_check_digit(body)
    full_number = body + str(check_digit)

    expiry = generate_expiry()
    cvv = generate_cvv(brand)

    return {
        "pan": full_number,
        "formatted": format_pan(full_number),
        "masked": mask_pan(full_number),
        "brand": detect_brand(full_number),
        "expiry": expiry,
        "cvv": cvv,
        "pipe_format": f"{full_number}|{expiry}|{cvv}",
        "luhn_valid": True
    }


def generate_cards(brand="Visa", count=10, bin_prefix="", custom_pattern=""):
    """Generate multiple cards according to criteria or pattern."""
    try:
        count = int(count)
    except (ValueError, TypeError):
        count = 10
    count = max(1, min(count, 100))
    results = []

    if custom_pattern and str(custom_pattern).strip():
        for _ in range(count):
            results.append(generate_from_pattern(str(custom_pattern).strip()))
        return results

    # Determine brand from bin_prefix if prefix provided
    if bin_prefix:
        detected = detect_brand(bin_prefix)
        if detected != "Unknown":
            brand = detected

    for _ in range(count):
        results.append(generate_single_card(brand=brand, prefix=bin_prefix))

    return results


def generate_from_pattern(pattern: str):
    """
    Parse pattern like '414720xxxxxxxxxx|12/28|xxx' or '4###############'.
    '#' or 'x' or 'X' replaced with random digits, preserving Luhn check.
    """
    parts = pattern.split("|")
    pan_pattern = parts[0].strip()

    # Replace wildcard characters
    digits = []
    for char in pan_pattern:
        if char in ["#", "x", "X"]:
            digits.append(str(random.randint(0, 9)))
        elif char.isdigit():
            digits.append(char)

    raw_payload = "".join(digits)
    brand = detect_brand(raw_payload)
    brand_info = BRANDS.get(brand, BRANDS["Visa"])
    target_length = brand_info["length"]

    if len(raw_payload) < target_length - 1:
        raw_payload += "".join(str(random.randint(0, 9)) for _ in range(target_length - 1 - len(raw_payload)))
    elif len(raw_payload) >= target_length:
        raw_payload = raw_payload[:target_length - 1]

    check_digit = luhn_check_digit(raw_payload)
    pan = raw_payload + str(check_digit)

    expiry = parts[1].strip() if len(parts) > 1 else generate_expiry()
    cvv = parts[2].strip() if len(parts) > 2 else generate_cvv(brand)

    # Fill wildcards in expiry / cvv if any
    expiry = "".join(str(random.randint(0, 9)) if c in ["#", "x", "X"] else c for c in expiry)
    cvv = "".join(str(random.randint(0, 9)) if c in ["#", "x", "X"] else c for c in cvv)

    return {
        "pan": pan,
        "formatted": format_pan(pan),
        "masked": mask_pan(pan),
        "brand": brand,
        "expiry": expiry,
        "cvv": cvv,
        "pipe_format": f"{pan}|{expiry}|{cvv}",
        "luhn_valid": luhn_valid(pan)
    }


def validate_card(card_input: str):
    """
    Validate single card string (accepts PAN or PAN|MM/YY|CVV).
    Returns complete breakdown of validity metrics.
    """
    if not card_input or not isinstance(card_input, str):
        return {
            "valid": False,
            "error": "No card input provided",
            "overall_valid": False,
            "status": "DECLINED / FAIL"
        }

    parts = [p.strip() for p in card_input.split("|")]
    raw_pan = only_digits(parts[0])

    exp_input = parts[1] if len(parts) > 1 else None
    cvv_input = parts[2] if len(parts) > 2 else None

    if not raw_pan:
        return {
            "valid": False,
            "error": "No digits found in input",
            "overall_valid": False,
            "status": "DECLINED / FAIL"
        }

    brand = detect_brand(raw_pan)
    is_luhn = luhn_valid(raw_pan)

    expected_length = BRANDS.get(brand, {}).get("length", 16)
    length_valid = len(raw_pan) == expected_length

    # Expiry check
    exp_valid = True
    if exp_input:
        exp_match = re.match(r"^(\d{2})[\/\.-]?(\d{2}|\d{4})$", exp_input)
        if exp_match:
            month, year = int(exp_match.group(1)), int(exp_match.group(2))
            if month < 1 or month > 12:
                exp_valid = False
        else:
            exp_valid = False

    # CVV check
    cvv_valid = True
    if cvv_input:
        req_len = 4 if brand == "Amex" else 3
        cvv_valid = cvv_input.isdigit() and len(cvv_input) == req_len

    bin_info = lookup_bin(raw_pan[:6])

    overall_valid = is_luhn and length_valid and exp_valid and cvv_valid

    return {
        "pan": raw_pan,
        "formatted": format_pan(raw_pan),
        "masked": mask_pan(raw_pan),
        "brand": brand,
        "is_luhn_valid": is_luhn,
        "length": len(raw_pan),
        "expected_length": expected_length,
        "is_length_valid": length_valid,
        "expiry": exp_input or "N/A",
        "is_expiry_valid": exp_valid,
        "cvv": cvv_input or "N/A",
        "is_cvv_valid": cvv_valid,
        "overall_valid": overall_valid,
        "bin_info": bin_info,
        "status": "APPROVED / PASS" if overall_valid else "DECLINED / FAIL"
    }


def lookup_bin(bin_prefix: str):
    """Lookup BIN details from offline database or fallback heuristics."""
    clean_bin = only_digits(bin_prefix)[:6]
    if len(clean_bin) < 6:
        return {
            "bin": clean_bin,
            "brand": "Unknown",
            "type": "Unknown",
            "level": "Unknown",
            "issuer": "Unknown",
            "country": "Unknown",
            "flag": "🌐"
        }

    for item in BIN_DB:
        if item["bin"] == clean_bin:
            return item

    brand = detect_brand(clean_bin)
    return {
        "bin": clean_bin,
        "brand": brand,
        "type": "Credit / Debit",
        "level": "Standard",
        "issuer": "Global Issuer",
        "country": "International",
        "flag": "🌐"
    }


def bulk_check(cards_text: str):
    """
    Process multiple card lines (e.g. from file or textarea).
    Returns summary statistics and per-card verification results.
    """
    lines = [line.strip() for line in cards_text.splitlines() if line.strip()]
    results = []

    passed_count = 0
    failed_count = 0

    for idx, line in enumerate(lines, 1):
        res = validate_card(line)
        if res.get("overall_valid"):
            passed_count += 1
        else:
            failed_count += 1

        results.append({
            "id": idx,
            "input": line,
            "res": res
        })

    return {
        "total": len(lines),
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": f"{(passed_count / max(1, len(lines))) * 100:.1f}%",
        "results": results
    }


def extrapolate_cards(seed_input: str, count=10):
    """
    Extrapolate candidate cards from a base PAN or seed card line.
    Uses pattern variation on middle/last digits with Luhn verification.
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        count = 10
    count = max(1, min(count, 50))

    seed_res = validate_card(seed_input)
    pan = seed_res.get("pan", "")
    brand = seed_res.get("brand", "Unknown")

    if not pan or len(pan) < 12:
        return {"error": "Seed PAN must be at least 12 digits"}

    bin_6 = pan[:6]
    last_4 = pan[-4:] if len(pan) >= 10 else pan[-2:]
    middle_len = len(pan) - len(bin_6) - 1  # exclude check digit

    extrapolated = []
    seen = set()

    # 1. Same BIN & pattern variation
    for _ in range(count * 3):
        if len(extrapolated) >= count:
            break
        # Vary middle digits while maintaining prefix
        mid_digits = "".join(str(random.randint(0, 9)) for _ in range(middle_len - len(bin_6)))
        body = bin_6 + mid_digits
        check = luhn_check_digit(body)
        candidate = body + str(check)

        if candidate not in seen:
            seen.add(candidate)
            expiry = seed_res["expiry"] if seed_res["expiry"] != "N/A" else generate_expiry()
            cvv = seed_res["cvv"] if seed_res["cvv"] != "N/A" else generate_cvv(brand)
            extrapolated.append({
                "pan": candidate,
                "formatted": format_pan(candidate),
                "masked": mask_pan(candidate),
                "brand": brand,
                "expiry": expiry,
                "cvv": cvv,
                "pipe_format": f"{candidate}|{expiry}|{cvv}",
                "method": "BIN-Extrapolation"
            })

    return {
        "seed": seed_input,
        "seed_pan": pan,
        "brand": brand,
        "count": len(extrapolated),
        "extrapolated": extrapolated
    }


def search_bin_db(query=""):
    """Search offline BIN database by BIN number, brand, issuer or country."""
    q = query.strip().lower()
    if not q:
        return BIN_DB

    filtered = []
    for item in BIN_DB:
        if (q in item["bin"].lower() or
            q in item["brand"].lower() or
            q in item["issuer"].lower() or
            q in item["country"].lower() or
            q in item["type"].lower()):
            filtered.append(item)

    return filtered


def export_records(records, export_format="csv"):
    """
    Format records for download in CSV, JSON, or TXT.
    """
    export_format = export_format.lower()

    if export_format == "json":
        return json.dumps(records, indent=2), "application/json", "cardx_export.json"

    elif export_format == "csv":
        headers = ["PAN", "Brand", "Expiry", "CVV", "Status", "Masked"]
        lines = [",".join(headers)]
        for r in records:
            pan = r.get("pan") or r.get("pipe_format", "").split("|")[0]
            brand = r.get("brand", "Unknown")
            expiry = r.get("expiry", "N/A")
            cvv = r.get("cvv", "N/A")
            status = r.get("status") or ("PASS" if r.get("luhn_valid") or r.get("overall_valid") else "N/A")
            masked = r.get("masked", mask_pan(pan))
            lines.append(f'"{pan}","{brand}","{expiry}","{cvv}","{status}","{masked}"')
        return "\n".join(lines), "text/csv", "cardx_export.csv"

    else:  # TXT
        lines = []
        for r in records:
            pipe = r.get("pipe_format") or f"{r.get('pan')}|{r.get('expiry')}|{r.get('cvv')}"
            lines.append(pipe)
        return "\n".join(lines), "text/plain", "cardx_export.txt"


def handle_telegram_command(text: str):
    """
    Process commands for Telegram Bot webhook (/start, /chk, /gen, /bin, /extrap, /templates, /help).
    Returns response text string.
    """
    text = text.strip()
    if not text:
        return "⚡ CARDX Bot - Ready. Type /help for available commands."

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ["/start", "/help"]:
        return (
            "⚡ <b>CARDX Cyberpunk Toolkit Bot</b>\n\n"
            "<b>Available Commands:</b>\n"
            "• <code>/chk [card|pipe]</code> - Validate card (Luhn, brand, format)\n"
            "• <code>/gen [brand/bin] [count]</code> - Generate Luhn-valid cards\n"
            "• <code>/bin [6-digit bin]</code> - Lookup issuer BIN info\n"
            "• <code>/extrap [card]</code> - Extrapolate PAN variations\n"
            "• <code>/templates</code> - View generation templates\n\n"
            "<i>Example: /chk 4000123456789010|12/28|123</i>"
        )

    elif cmd == "/chk":
        if not args:
            return "❌ Please provide a card number or pipe format: <code>/chk 4000123456789010|12/28|123</code>"
        res = validate_card(args)
        status_emoji = "✅" if res["overall_valid"] else "❌"
        return (
            f"⚡ <b>CARDX Validation Result</b>\n\n"
            f"<b>Card:</b> <code>{res['masked']}</code>\n"
            f"<b>Brand:</b> {res['brand']}\n"
            f"<b>Luhn Check:</b> {'PASS' if res['is_luhn_valid'] else 'FAIL'}\n"
            f"<b>Length:</b> {res['length']} (Expected {res['expected_length']})\n"
            f"<b>Issuer:</b> {res['bin_info']['issuer']} ({res['bin_info']['flag']} {res['bin_info']['country']})\n"
            f"<b>Status:</b> {status_emoji} <b>{res['status']}</b>"
        )

    elif cmd == "/gen":
        brand = "Visa"
        count = 5
        if args:
            subparts = args.split()
            brand = subparts[0]
            if len(subparts) > 1 and subparts[1].isdigit():
                count = int(subparts[1])
        cards = generate_cards(brand=brand, count=count)
        lines = [f"⚡ <b>Generated {len(cards)} Cards ({brand}):</b>\n"]
        for c in cards:
            lines.append(f"<code>{c['pipe_format']}</code>")
        return "\n".join(lines)

    elif cmd == "/bin":
        if not args:
            return "❌ Please provide BIN prefix: <code>/bin 400016</code>"
        info = lookup_bin(args)
        return (
            f"🏷️ <b>BIN Lookup: {info['bin']}</b>\n\n"
            f"<b>Brand:</b> {info['brand']}\n"
            f"<b>Type:</b> {info['type']}\n"
            f"<b>Level:</b> {info['level']}\n"
            f"<b>Issuer:</b> {info['issuer']}\n"
            f"<b>Country:</b> {info['flag']} {info['country']}"
        )

    elif cmd == "/extrap":
        if not args:
            return "❌ Please provide base card: <code>/extrap 4000123456789010</code>"
        res = extrapolate_cards(args, count=5)
        if "error" in res:
            return f"❌ {res['error']}"
        lines = [f"🔮 <b>Extrapolated Cards for {res['brand']}:</b>\n"]
        for item in res["extrapolated"]:
            lines.append(f"<code>{item['pipe_format']}</code>")
        return "\n".join(lines)

    elif cmd == "/templates":
        lines = ["🧩 <b>CARDX Generation Templates:</b>\n"]
        for t in TEMPLATES:
            lines.append(f"• <b>{t['name']}</b>: <code>{t['pattern']}</code>\n  <i>{t['description']}</i>")
        return "\n".join(lines)

    return f"❓ Unknown command: {cmd}. Send /help for command list."

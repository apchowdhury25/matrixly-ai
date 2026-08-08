#!/usr/bin/env python3
"""Translate sitewide catalog keys (site.*) into all locales via deep-translator."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "i18n"
CATALOG = ROOT / "_sitewide_en_catalog.json"
LANGS = ["es", "fr", "de", "ar", "bn", "ms"]

PROTECT = [
    "Matrixly", "SocialForge", "BookWise", "SupportForge", "InvoiceForge", "ContentForge",
    "SEOForge", "MeetWise", "PipelineForge", "DocForge", "ConnectForge", "Lead Qualifier",
    "Email Assistant", "Shipping Assistant", "CRM Assistant", "Starter Pack", "Invoice Processor",
    "ETF Portfolio Analyzer", "ETF Analyzer", "White Glove", "Shopify", "Gmail", "QuickBooks",
    "HubSpot", "ShipStation", "Slack", "Square", "Stripe", "Zapier", "ChatGPT", "Salesforce",
    "Google Business", "Google Calendar", "Google Biz", "UPS", "FedEx", "USPS", "WooCommerce",
    "Xero", "Zoom", "LinkedIn", "Notion", "Hermes", "MCP", "Grok", "SOC 2", "GDPR", "HITL",
    "ROI", "SEO", "CRM", "API", "PDF", "OCR", "POS", "NAV", "WISMO", "Klaviyo", "Buffer",
]


def protect(text: str):
    tokens = []
    out = text
    for i, brand in enumerate(sorted(PROTECT, key=len, reverse=True)):
        if brand in out:
            tok = f"XXBRAND{i}XX"
            out = out.replace(brand, tok)
            tokens.append((tok, brand))
    return out, tokens


def unprotect(text: str, tokens) -> str:
    for tok, brand in tokens:
        text = text.replace(tok, brand)
    return re.sub(r"\s+", " ", text).strip()


def set_path(root: dict, path: str, value: str):
    parts = path.split(".")
    cur = root
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def get_path(root: dict, path: str):
    cur = root
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def translate_one(translator, text: str) -> str:
    if not text or not text.strip():
        return text
    p, toks = protect(text)
    try:
        t = translator.translate(p[:4500])
        return unprotect(t, toks)
    except Exception as e:
        print(f"  fail: {e!r} :: {text[:50]}")
        return text


def main():
    if not CATALOG.exists():
        raise SystemExit("Run sitewide-i18n-coverage.py first")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    print(f"Catalog: {len(catalog)} keys")
    packs_dir = I18N / "packs"
    packs_dir.mkdir(exist_ok=True)

    for lang in LANGS:
        print(f"\n=== {lang} ===")
        pack_path = packs_dir / f"site_{lang}.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8")) if pack_path.exists() else {}
        translator = GoogleTranslator(source="en", target=lang)
        items = list(catalog.items())
        for i, (key, en_text) in enumerate(items, 1):
            if key in pack and pack[key] and pack[key] != en_text:
                continue
            pack[key] = translate_one(translator, en_text)
            if i % 30 == 0:
                print(f"  {i}/{len(items)}")
                pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                time.sleep(0.35)
            else:
                time.sleep(0.07)
        pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        loc_path = I18N / f"{lang}.json"
        data = json.loads(loc_path.read_text(encoding="utf-8"))
        for key, en_text in catalog.items():
            set_path(data, key, pack.get(key, en_text))
        if lang == "ar":
            data.setdefault("meta", {})["dir"] = "rtl"
        loc_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        non_en = sum(1 for k, en in catalog.items() if get_path(data, k) != en)
        print(f"  non-English: {non_en}/{len(catalog)}")


if __name__ == "__main__":
    main()

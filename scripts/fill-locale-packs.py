#!/usr/bin/env python3
"""
Translate full.* catalog keys into es/fr/de/ar/bn/ms using deep-translator (Google).
Preserves Matrixly + product brand tokens. Merges into i18n/{lang}.json.
"""
from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from pathlib import Path

from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "i18n"
CATALOG = ROOT / "_full_en_catalog.json"

LANGS = ["es", "fr", "de", "ar", "bn", "ms"]

PROTECT = [
    "Matrixly",
    "SocialForge",
    "BookWise",
    "SupportForge",
    "InvoiceForge",
    "ContentForge",
    "SEOForge",
    "MeetWise",
    "PipelineForge",
    "DocForge",
    "ConnectForge",
    "Lead Qualifier",
    "Email Assistant",
    "Shipping Assistant",
    "CRM Assistant",
    "Starter Pack",
    "Invoice Processor",
    "ETF Portfolio Analyzer",
    "White Glove",
    "Shopify",
    "Gmail",
    "QuickBooks",
    "HubSpot",
    "ShipStation",
    "Slack",
    "Square",
    "Stripe",
    "Zapier",
    "ChatGPT",
    "Salesforce",
    "Google Business",
    "Google Calendar",
    "Google Biz",
    "UPS",
    "FedEx",
    "USPS",
    "WooCommerce",
    "Xero",
    "Zoom",
    "LinkedIn",
    "Notion",
    "Hermes",
    "MCP",
    "Grok",
    "SOC 2",
    "GDPR",
    "HITL",
    "ROI",
    "SEO",
    "CRM",
    "API",
    "PDF",
    "OCR",
    "POS",
    "NAV",
    "WISMO",
    "UrbanThread",
    "CoolAir HVAC",
    "Peak Legal",
    "BrightPath Dental",
    "Metro Home Pros",
    "Marcus Rivera",
    "Jordan Lee",
    "Aisha Khan",
    "Sofia Patel",
    "Nina Walsh",
]


def protect(text: str):
    tokens = []
    out = text
    # longest first
    for i, brand in enumerate(sorted(PROTECT, key=len, reverse=True)):
        if brand in out:
            tok = f"XXBRAND{i}XX"
            out = out.replace(brand, tok)
            tokens.append((tok, brand))
    return out, tokens


def unprotect(text: str, tokens) -> str:
    for tok, brand in tokens:
        text = text.replace(tok, brand)
        # sometimes translator spaces tokens
        text = text.replace(tok.replace("XX", " XX ").strip(), brand)
    # cleanup common artifacts
    text = re.sub(r"\s+", " ", text).strip()
    return text


def deep_merge(a: dict, b: dict) -> dict:
    out = deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


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


def translate_one(translator: GoogleTranslator, text: str) -> str:
    if not text or len(text.strip()) < 1:
        return text
    p, toks = protect(text)
    # Google has length limits; chunk if needed
    try:
        if len(p) > 4500:
            # split by sentences
            parts = re.split(r"(?<=[.!?])\s+", p)
            out_parts = []
            for part in parts:
                if not part.strip():
                    continue
                out_parts.append(translator.translate(part))
                time.sleep(0.05)
            t = " ".join(out_parts)
        else:
            t = translator.translate(p)
        return unprotect(t, toks)
    except Exception as e:
        print(f"    translate fail: {e!r} :: {text[:50]}")
        return text


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    print(f"Catalog: {len(catalog)} strings")
    packs_dir = I18N / "packs"
    packs_dir.mkdir(exist_ok=True)

    for lang in LANGS:
        print(f"\n=== {lang} ===")
        pack_path = packs_dir / f"{lang}.json"
        pack = {}
        if pack_path.exists():
            pack = json.loads(pack_path.read_text(encoding="utf-8"))

        translator = GoogleTranslator(source="en", target=lang)
        items = list(catalog.items())
        done = 0
        for key, en_text in items:
            if key in pack and pack[key] and pack[key] != en_text:
                done += 1
                continue
            # skip very short numeric-like
            tr = translate_one(translator, en_text)
            pack[key] = tr
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(items)}")
                pack_path.write_text(
                    json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                time.sleep(0.4)
            else:
                time.sleep(0.08)

        pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  pack saved: {len(pack)}")

        # merge into locale
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

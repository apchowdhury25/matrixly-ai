#!/usr/bin/env python3
"""
Full 100% i18n coverage for index.html landing page.

1. Collect every user-visible text node without data-i18n
2. Assign stable keys under page.{section}.{slug}
3. Merge into all locale files (EN source + translations for new keys)
4. Wire data-i18n attributes on index.html

Brand/product names stay English (no attribute added).
"""
from __future__ import annotations

import json
import re
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
I18N = ROOT / "i18n"

BRAND_KEEP = {
    "Matrixly",
    "Shopify",
    "Gmail",
    "QuickBooks",
    "HubSpot",
    "ShipStation",
    "Slack",
    "Square",
    "Stripe",
    "Lead Qualifier",
    "Email Assistant",
    "Shipping Assistant",
    "CRM Assistant",
    "SupportForge",
    "SocialForge",
    "BookWise",
    "InvoiceForge",
    "ContentForge",
    "SEOForge",
    "SEO Forge",
    "MeetWise",
    "PipelineForge",
    "Starter Pack",
    "DocForge",
    "ConnectForge",
    "Invoice Processor",
    "ETF Portfolio Analyzer",
    "White Glove",
    "Grow",
    "Scale",
    "Explore",
    "Pro",
    "Starter",
    "Free",
    "Executive",
    "Zapier + ChatGPT",
    "UPS / FedEx",
    "Meta Ads",
    "Google Biz",
    "Google Business",
    "PICK",
    "CONNECT",
    "RUN",
    "GROW",
    "KNOW",
    "THINK",
    "LINK",
    "LEAD",
    "MAIL",
    "SHIP",
    "RATE",
    "TRACK",
    "FIX",
    "Marcus Rivera",
    "Jordan Lee",
    "Aisha Khan",
    "Sofia Patel",
    "Nina Walsh",
    "Order #48291",
    "Shopify · UrbanThread Co.",
    "CoolAir HVAC",
    "UrbanThread",
    "Peak Legal",
    "BrightPath Dental",
    "Metro Home Pros",
    "Salesforce",
    "Outlook",
    "Xero",
    "Zoom",
    "Teams",
    "Meet",
    "Meta",
    "LinkedIn",
    "Buffer",
    "Grok",
    "Notion",
    "Hermes",
    "MCP",
    "SOC 2",
    "GDPR",
}

# Category labels that appear as agent tags — translate these
# Product names above stay English


def section_spans(html: str):
    spans = [(0, "page")]
    for m in re.finditer(r"<section([^>]*)>", html, re.I):
        idm = re.search(r'id="([^"]+)"', m.group(1))
        sid = idm.group(1) if idm else f"sec{m.start()}"
        spans.append((m.start(), sid))
    if re.search(r"<footer\b", html, re.I):
        spans.append((re.search(r"<footer\b", html, re.I).start(), "footer"))
    spans.sort()
    return spans


def section_at(spans, pos: int) -> str:
    cur = "page"
    for start, sid in spans:
        if pos >= start:
            cur = sid
        else:
            break
    return cur


def slugify(text: str, i: int) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    if not s:
        s = f"t{i}"
    if not s[0].isalpha():
        s = "t_" + s
    return s[:48]


def collect(html: str):
    spans = section_spans(html)
    items = []
    for m in re.finditer(
        r"<(h[1-6]|p|button|a|label|span|li|th|td)(\s[^>]*)?>([^<]{2,400})</\1>",
        html,
        re.I,
    ):
        tag, attrs, text = m.group(1), m.group(2) or "", m.group(3)
        if "data-i18n" in attrs:
            continue
        if "aria-hidden" in attrs and "true" in attrs:
            continue
        raw = text
        text = re.sub(r"\s+", " ", text.strip())
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        if len(text) < 2:
            continue
        if re.match(r"^[\d\s$%+\-–—·•✓←→/<>&;.,:x×↓↑#]+$", text):
            continue
        if text in BRAND_KEEP:
            continue
        # skip pure entity-ish
        if text in {"&times;", "×", "—", "·"}:
            continue
        sec = section_at(spans, m.start())
        items.append(
            {
                "section": sec,
                "tag": tag.lower(),
                "text": text,
                "raw": raw,
                "start": m.start(),
                "end": m.end(),
                "full": m.group(0),
                "open": m.group(0)[: m.group(0).find(">") + 1],
            }
        )
    return items


def build_catalog(items):
    by_text = OrderedDict()
    for it in items:
        by_text.setdefault(it["text"], []).append(it)
    catalog = OrderedDict()
    mapping = []  # (key, text, occs)
    used = set()
    for i, (text, occs) in enumerate(by_text.items()):
        sec = re.sub(r"[^a-zA-Z0-9_]", "_", occs[0]["section"])
        key = f"full.{sec}.{slugify(text, i)}"
        base = key
        n = 2
        while key in used:
            key = f"{base}_{n}"
            n += 1
        used.add(key)
        catalog[key] = text
        mapping.append((key, text, occs))
    return catalog, mapping


def unflatten_path(root: dict, path: str, value: str):
    parts = path.split(".")
    cur = root
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def flatten(obj, prefix="", out=None):
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(v, f"{prefix}.{k}" if prefix else k, out)
    else:
        out[prefix] = obj
    return out


# ---------------------------------------------------------------------------
# Translation helpers — glossary-aware phrase dictionary + pass-through brands
# For long strings we provide language-specific overrides when present.
# ---------------------------------------------------------------------------

def translate_text(text: str, lang: str) -> str:
    """Translate UI string. Falls back to English if no mapping."""
    if lang == "en":
        return text
    # exact overrides first
    pack = TRANSLATIONS.get(lang, {})
    if text in pack:
        return pack[text]
    # try without smart quotes variants
    alt = text.replace("’", "'").replace("“", '"').replace("”", '"')
    if alt in pack:
        return pack[alt]
    return text  # temporary; filled below for all langs via big dict


# We'll build TRANSLATIONS densely for es, fr, de, ar, bn, ms for ALL catalog strings
# by loading from generated packs after first EN extract.

TRANSLATIONS: dict[str, dict[str, str]] = {c: {} for c in ["es", "fr", "de", "ar", "bn", "ms"]}


def wire_html(html: str, mapping) -> str:
    """
    Inject data-i18n into opening tags for each occurrence.
    Process from end to start so offsets stay valid.
    """
    # Build list of (start_of_open_tag, end_of_open_tag, key) for each occurrence
    ops = []
    for key, text, occs in mapping:
        for it in occs:
            full = it["full"]
            # open tag ends at first >
            gt = full.find(">")
            if gt < 0:
                continue
            open_tag = full[: gt + 1]
            if "data-i18n=" in open_tag:
                continue
            # insert before closing >
            if open_tag.endswith("/>"):
                continue
            new_open = open_tag[:-1] + f' data-i18n="{key}">'
            # absolute positions in html
            start = it["start"]
            ops.append((start, start + gt + 1, new_open))

    ops.sort(key=lambda x: x[0], reverse=True)
    for start, end, new_open in ops:
        html = html[:start] + new_open + html[end:]
    return html


def load_json(code: str) -> dict:
    return json.loads((I18N / f"{code}.json").read_text(encoding="utf-8"))


def save_json(code: str, data: dict) -> None:
    (I18N / f"{code}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def merge_flat_into(data: dict, flat: dict) -> dict:
    data = deepcopy(data)
    for path, value in flat.items():
        unflatten_path(data, path, value)
    return data


def main():
    html = INDEX.read_text(encoding="utf-8")
    items = collect(html)
    catalog, mapping = build_catalog(items)
    print(f"Collected {len(items)} nodes, {len(catalog)} unique strings to wire")

    # Save EN catalog for translation tooling
    (ROOT / "_full_en_catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Wire HTML
    new_html = wire_html(html, mapping)
    # count
    before = html.count("data-i18n")
    after = new_html.count("data-i18n")
    INDEX.write_text(new_html, encoding="utf-8")
    print(f"index.html data-i18n: {before} → {after}")

    # Merge into en.json
    en = load_json("en")
    en = merge_flat_into(en, catalog)
    save_json("en", en)

    # For other locales: use translations if available, else English fallback
    # Load optional packs from i18n/packs/{lang}.json if present
    packs_dir = I18N / "packs"
    for lang in ["es", "fr", "de", "ar", "bn", "ms"]:
        data = load_json(lang)
        flat_new = {}
        pack_path = packs_dir / f"{lang}.json"
        pack = {}
        if pack_path.exists():
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
        for key, en_text in catalog.items():
            # pack maps english -> translated OR key -> translated
            if key in pack:
                flat_new[key] = pack[key]
            elif en_text in pack:
                flat_new[key] = pack[en_text]
            elif en_text in TRANSLATIONS.get(lang, {}):
                flat_new[key] = TRANSLATIONS[lang][en_text]
            else:
                flat_new[key] = en_text  # English fallback until pack filled
        data = merge_flat_into(data, flat_new)
        if lang == "ar":
            data.setdefault("meta", {})["dir"] = "rtl"
        save_json(lang, data)
        translated = sum(1 for k, v in flat_new.items() if v != catalog[k])
        print(f"{lang}: {translated}/{len(flat_new)} newly translated (rest EN fallback for now)")

    # Re-check residual unwired (excluding brands)
    residual = collect(INDEX.read_text(encoding="utf-8"))
    print(f"Residual unwired (non-brand) text nodes: {len(residual)}")
    if residual:
        for it in residual[:20]:
            print("  residual:", it["section"], it["text"][:70])


if __name__ == "__main__":
    main()

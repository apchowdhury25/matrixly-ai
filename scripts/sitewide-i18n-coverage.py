#!/usr/bin/env python3
"""
Site-wide i18n: wire every marketing page + expand locale catalogs.

Skips internal agent dashboards (agents/*/static) and admin.
Product/brand names stay English.
"""
from __future__ import annotations

import json
import re
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "i18n"

SKIP_SUBSTR = [
    "agents/book-wise",
    "agents\\book-wise",
    "agents/connect-forge",
    "agents\\connect-forge",
    "agents/content-forge",
    "agents\\content-forge",
    "agents/doc-forge",
    "agents\\doc-forge",
    "agents/etf-analyzer",
    "agents\\etf-analyzer",
    "agents/invoice-forge",
    "agents\\invoice-forge",
    "agents/meet-wise",
    "agents\\meet-wise",
    "agents/pipeline-forge",
    "agents\\pipeline-forge",
    "agents/seo-bespoke",
    "agents\\seo-bespoke",
    "agents/seo-forge",
    "agents\\seo-forge",
    "agents/social-forge",
    "agents\\social-forge",
    "agents/starter-pack",
    "agents\\starter-pack",
    "agents/support-forge",
    "agents\\support-forge",
    "admin/",
    "admin\\",
    "node_modules",
]

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
    "ETF Analyzer",
    "White Glove",
    "Grow",
    "Scale",
    "Explore",
    "Pro",
    "Starter",
    "Free",
    "Executive",
    "Zapier + ChatGPT",
    "Zapier",
    "ChatGPT",
    "UPS / FedEx",
    "Meta Ads",
    "Google Biz",
    "Google Business",
    "Google Calendar",
    "Salesforce",
    "Outlook",
    "Xero",
    "Zoom",
    "Teams",
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
    "CoolAir HVAC",
    "UrbanThread",
    "Peak Legal",
    "BrightPath Dental",
    "Metro Home Pros",
    "Buffer",
    "Klaviyo",
    "WooCommerce",
    "USPS",
    "UPS",
    "FedEx",
}


def should_skip(path: Path) -> bool:
    s = str(path)
    return any(x in s for x in SKIP_SUBSTR)


def page_slug(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return "home"
    return re.sub(r"[^a-zA-Z0-9]+", "_", rel.replace("/index.html", "")).strip("_").lower()


def section_spans(html: str):
    spans = [(0, "page")]
    for m in re.finditer(r"<section([^>]*)>", html, re.I):
        idm = re.search(r'id="([^"]+)"', m.group(1))
        sid = idm.group(1) if idm else f"s{m.start()}"
        spans.append((m.start(), re.sub(r"[^a-zA-Z0-9_]", "_", sid)))
    fm = re.search(r"<footer\b", html, re.I)
    if fm:
        spans.append((fm.start(), "footer"))
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
    return s[:40]


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )


def collect_nodes(html: str):
    spans = section_spans(html)
    items = []
    for m in re.finditer(
        r"<(h[1-6]|p|button|a|label|span|li|th|td)(\s[^>]*)?>([^<]{2,500})</\1>",
        html,
        re.I,
    ):
        tag, attrs, text = m.group(1), m.group(2) or "", m.group(3)
        if "data-i18n" in attrs:
            continue
        if "aria-hidden" in attrs and "true" in attrs:
            continue
        text_n = normalize_text(text)
        if len(text_n) < 2:
            continue
        if re.match(r"^[\d\s$%+\-–—·•✓←→/<>&;.,:#x×↓↑]+$", text_n):
            continue
        if text_n in BRAND_KEEP:
            continue
        # skip pure single tech words already brand-like
        if text_n in {"Live", "Demo", "Mktg", "Sales", "Support", "Logistics"} and tag.lower() == "span":
            # still translate status badges like Live via catalog if desired — include them
            pass
        items.append(
            {
                "section": section_at(spans, m.start()),
                "tag": tag.lower(),
                "text": text_n,
                "raw": text,
                "start": m.start(),
                "full": m.group(0),
            }
        )
    return items


def ensure_scripts(html: str) -> str:
    if "/js/i18n.js" in html and "/js/lang-selector.js" in html:
        return html
    block = '  <script src="/js/i18n.js" defer></script>\n  <script src="/js/lang-selector.js" defer></script>\n'
    if "/js/i18n.js" in html and "/js/lang-selector.js" not in html:
        return html.replace(
            '<script src="/js/i18n.js" defer></script>',
            block.rstrip() + "\n",
            1,
        )
    if re.search(r"</body>", html, re.I):
        return re.sub(r"</body>", block + "</body>", html, count=1, flags=re.I)
    return html + "\n" + block


def wire_page(html: str, page: str, global_catalog: OrderedDict, page_keys: list):
    """
    Assign keys and inject data-i18n. Reuses existing catalog key if same English already exists.
    """
    # reverse map text -> key for reuse
    text_to_key = {v: k for k, v in global_catalog.items()}

    items = collect_nodes(html)
    # group by text for this page
    by_text = OrderedDict()
    for it in items:
        by_text.setdefault(it["text"], []).append(it)

    ops = []  # (start, end_open, new_open)
    for i, (text, occs) in enumerate(by_text.items()):
        if text in text_to_key:
            key = text_to_key[text]
        else:
            sec = re.sub(r"[^a-zA-Z0-9_]", "_", occs[0]["section"])
            key = f"site.{page}.{sec}.{slugify(text, i)}"
            base = key
            n = 2
            while key in global_catalog:
                key = f"{base}_{n}"
                n += 1
            global_catalog[key] = text
            text_to_key[text] = key
            page_keys.append(key)

        for it in occs:
            full = it["full"]
            gt = full.find(">")
            if gt < 0:
                continue
            open_tag = full[: gt + 1]
            if "data-i18n=" in open_tag:
                continue
            new_open = open_tag[:-1] + f' data-i18n="{key}">'
            ops.append((it["start"], it["start"] + gt + 1, new_open))

    ops.sort(key=lambda x: x[0], reverse=True)
    for start, end, new_open in ops:
        html = html[:start] + new_open + html[end:]
    return html


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


def flatten_existing_en(en: dict) -> dict:
    """Build text->key map from existing en values for reuse."""
    out = OrderedDict()

    def walk(o, prefix=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(o, str):
            # prefer first key for a given string
            if o not in out.values():
                out[prefix] = o

    walk(en)
    return out


def main():
    pages = sorted(
        p for p in ROOT.rglob("index.html") if not should_skip(p)
    )
    print(f"Pages to process: {len(pages)}")

    en_path = I18N / "en.json"
    en = json.loads(en_path.read_text(encoding="utf-8"))
    # seed global catalog from existing EN strings (path -> text)
    existing_flat = flatten_existing_en(en)
    global_catalog = OrderedDict(existing_flat)  # key -> text

    # Prefer shorter keys for reuse: also map text -> best key
    # When wiring, we reuse if text already in catalog values

    new_keys = []
    changed_pages = []

    for path in pages:
        html = path.read_text(encoding="utf-8", errors="replace")
        html = ensure_scripts(html)
        slug = page_slug(path)
        before = html.count("data-i18n")
        page_new = []
        html2 = wire_page(html, slug, global_catalog, page_new)
        after = html2.count("data-i18n")
        if html2 != html or after != before:
            path.write_text(html2, encoding="utf-8")
            changed_pages.append((str(path.relative_to(ROOT)), before, after, len(page_new)))
            new_keys.extend(page_new)
            print(f"  {path.relative_to(ROOT)}: data-i18n {before} → {after} (+{len(page_new)} new keys)")

    # Merge ALL global_catalog into en.json (includes existing + new)
    for key, text in global_catalog.items():
        set_path(en, key, text)
    en_path.write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # For other locales: copy new keys as English placeholder if missing
    for lang in ["es", "fr", "de", "ar", "bn", "ms"]:
        loc_path = I18N / f"{lang}.json"
        data = json.loads(loc_path.read_text(encoding="utf-8"))
        added = 0
        for key, text in global_catalog.items():
            if get_path(data, key) is None:
                set_path(data, key, text)
                added += 1
        if lang == "ar":
            data.setdefault("meta", {})["dir"] = "rtl"
        loc_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  {lang}: added {added} missing keys (EN placeholder)")

    # Save delta catalog for translation
    delta = {k: global_catalog[k] for k in new_keys}
    # also any site.* keys
    site_keys = {k: v for k, v in global_catalog.items() if k.startswith("site.")}
    catalog_out = {**site_keys}
    # include new only unique
    for k, v in delta.items():
        catalog_out[k] = v
    (ROOT / "_sitewide_en_catalog.json").write_text(
        json.dumps(catalog_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\nChanged pages: {len(changed_pages)}")
    print(f"New keys this run: {len(new_keys)}")
    print(f"Site catalog size: {len(catalog_out)}")
    print("Next: python scripts/fill-sitewide-packs.py")


if __name__ == "__main__":
    main()

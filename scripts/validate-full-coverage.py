#!/usr/bin/env python3
import json
import re
from pathlib import Path

cat = json.loads(Path("_full_en_catalog.json").read_text(encoding="utf-8"))


def get(o, p):
    cur = o
    for x in p.split("."):
        if not isinstance(cur, dict) or x not in cur:
            return None
        cur = cur[x]
    return cur


for lang in ["en", "es", "fr", "de", "ar", "bn", "ms"]:
    d = json.loads(Path(f"i18n/{lang}.json").read_text(encoding="utf-8"))
    miss = [k for k in cat if get(d, k) is None]
    nonen = sum(1 for k, v in cat.items() if get(d, k) != v)
    print(f"{lang}: missing={len(miss)} translated={nonen}/{len(cat)}")
    if lang == "ar":
        print("  compare:", d.get("compare", {}).get("title"), d.get("compare", {}).get("titleHighlight"))
        k = list(cat.keys())[10]
        print("  sample full:", k, "=>", (get(d, k) or "")[:90])

html = Path("index.html").read_text(encoding="utf-8")
print("data-i18n count:", html.count("data-i18n"))
print("double attrs:", len(re.findall(r'data-i18n="[^"]+"[^>]*data-i18n=', html)))
print("scripts:", "/js/i18n.js" in html, "/js/lang-selector.js" in html)

# residual non-brand text
from scripts.full_coverage_i18n import collect  # may fail path

# inline residual check
BRAND = {"Matrixly", "Shopify", "Gmail"}
count = 0
for m in re.finditer(
    r"<(h[1-6]|p|button|a|label|span|li|th|td)(\s[^>]*)?>([^<]{3,200})</\1>", html, re.I
):
    attrs, text = m.group(2) or "", m.group(3).strip()
    if "data-i18n" in attrs:
        continue
    if re.match(r"^[\d\s$%+\-–—·•✓←→/<>&;.,:]+$", text):
        continue
    count += 1
print("residual unwired text nodes:", count)

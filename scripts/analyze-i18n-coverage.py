#!/usr/bin/env python3
from pathlib import Path
import re

html = Path("index.html").read_text(encoding="utf-8")
print("data-i18n count:", len(re.findall(r"data-i18n", html)))

for m in re.finditer(r"<section([^>]*)>(.*?)(?=<section|</main>)", html, re.S | re.I):
    attrs_s, body = m.group(1), m.group(2)
    idm = re.search(r'id="([^"]+)"', attrs_s)
    sid = idm.group(1) if idm else "(no-id)"
    di = len(re.findall(r"data-i18n", body))
    tags = len(re.findall(r"<(?:h[1-6]|p|button|a|label|span|li|th|td)\b", body, re.I))
    print(f"{sid:25} data-i18n={di:3} text-tags~={tags:3}")

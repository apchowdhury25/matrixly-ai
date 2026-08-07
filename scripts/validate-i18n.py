#!/usr/bin/env python3
import json
import re
from pathlib import Path

html = Path("index.html").read_text(encoding="utf-8")
keys = set(re.findall(r'data-i18n(?:-html|-attr)?="([^"]+)"', html))
flat = set()
for k in keys:
    if ":" in k:
        for pair in k.split(","):
            pair = pair.strip()
            if ":" in pair:
                flat.add(pair.split(":", 1)[1])
            else:
                flat.add(pair)
    else:
        flat.add(k)

en = json.loads(Path("i18n/en.json").read_text(encoding="utf-8"))


def get(o, p):
    cur = o
    for part in p.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


missing = [k for k in sorted(flat) if get(en, k) is None]
print("data-i18n keys used:", len(flat))
print("missing keys:", missing)
print("i18n script:", "/js/i18n.js" in html)
print("lang-selector script:", "/js/lang-selector.js" in html)
print("lang-selector css:", ".lang-selector" in html)

for f in sorted(Path("i18n").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    print(f.name, "bytes", f.stat().st_size, "dir", d["meta"]["dir"], "native", d["meta"]["nativeName"])

# key parity across locales
en_paths = set()


def walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, f"{prefix}.{k}" if prefix else k)
    else:
        en_paths.add(prefix)


walk(en)
for code in ["es", "fr", "ar", "bn", "de"]:
    data = json.loads(Path(f"i18n/{code}.json").read_text(encoding="utf-8"))
    paths = set()

    def w(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                w(v, f"{prefix}.{k}" if prefix else k)
        else:
            paths.add(prefix)

    w(data)
    if paths != en_paths:
        print(code, "KEY MISMATCH missing", en_paths - paths, "extra", paths - en_paths)
    else:
        print(code, "key parity OK")

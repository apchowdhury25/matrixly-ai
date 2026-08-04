#!/usr/bin/env python3
"""Fix UTF-8 mojibake (â€”, Â·, â€œ, etc.) from CP1252 mis-encoding."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXTS = {".html", ".md", ".js", ".mjs", ".css", ".txt", ".yaml", ".yml", ".json"}
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "data",
    "reports",
}

# Longest-first replacements (mojibake -> correct Unicode)
REPLACEMENTS: list[tuple[str, str]] = [
    # Full multi-byte mojibake sequences
    ("â€¦", "\u2026"),  # …
    ("â€”", "\u2014"),  # —
    ("â€“", "\u2013"),  # –
    ("â€˜", "\u2018"),  # ‘
    ("â€™", "\u2019"),  # ’
    ("â€œ", "\u201c"),  # “
    ("â€\x9d", "\u201d"),  # ” (partial: raw 0x9D third byte)
    ("â€\u009d", "\u201d"),
    ("â€\u201d", "\u201d"),  # sometimes already half-fixed
    ("â€\u201c", "\u201c"),
    ("â†’", "\u2192"),  # →
    ("â†\x90", "\u2190"),  # ← (partial)
    ("â†\u0090", "\u2190"),
    ("â†‘", "\u2191"),  # ↑
    ("â†“", "\u2193"),  # ↓
    ("âœ“", "\u2713"),  # ✓
    ("âœ‰", "\u2709"),  # ✉
    ("âˆ’", "\u2212"),  # −
    ("Â·", "\u00b7"),  # ·
    ("Â©", "\u00a9"),  # ©
    ("Â®", "\u00ae"),  # ®
    ("Ã—", "\u00d7"),  # ×
    ("Ã—", "\u00d7"),
    # Corrupted SSO lock emoji (was 🔐)
    ("ðŸ”—", "\U0001f510"),  # 🔐
    ("ðŸ”\u2014", "\U0001f510"),
    # Stray C1 controls left after partial decode
    ("\x9d", "\u201d"),  # remaining raw 0x9D as ”
    ("\x90", "\u2190"),  # remaining raw 0x90 if alone after â† removed
]

# Markers that mean file still needs work
MARKERS = re.compile(
    r"â€|Â·|Â©|Ã—|â€™|â€œ|â†|âœ|âˆ|Weâ|youâ|donâ|Whatâ|Youâ|Iâ|didnâ|whereâ|companyâ|privacyâ|ðŸ"
)


def looks_mojibake(s: str) -> bool:
    if MARKERS.search(s):
        return True
    if "\x9d" in s or "\x90" in s:
        return True
    return False


def fix_text(text: str) -> str:
    for bad, good in REPLACEMENTS:
        if bad in text:
            text = text.replace(bad, good)
    # Normalize double-encoded HTML ampersand display issues only when literal
    # &amp;amp; (keep normal &amp; — that is correct HTML)
    text = text.replace("&amp;amp;", "&amp;")
    return text


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in EXTS:
            continue
        if path.name == "fix-mojibake.py":
            continue
        yield path


def main() -> int:
    fixed_files: list[str] = []
    still_bad: list[str] = []
    scanned = 0

    for path in sorted(iter_files(ROOT)):
        scanned += 1
        try:
            raw = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"SKIP {path.relative_to(ROOT)}: {e}")
            continue

        if not looks_mojibake(raw) and "&amp;amp;" not in raw:
            continue

        # Preserve original newlines style
        new = fix_text(raw)
        if new == raw:
            still_bad.append(f"{path.relative_to(ROOT)} (no change)")
            continue

        # Write UTF-8 without BOM; keep \n as produced by replace (same as input)
        path.write_bytes(new.encode("utf-8"))
        rel = str(path.relative_to(ROOT))
        fixed_files.append(rel)
        if looks_mojibake(new):
            still_bad.append(rel)

    print(f"Scanned {scanned} files.")
    print(f"Fixed {len(fixed_files)} file(s):")
    for f in fixed_files:
        print(f"  OK  {f}")
    if still_bad:
        print(f"Still has markers ({len(still_bad)}):")
        for f in still_bad:
            print(f"  BAD {f}")
            # show remaining non-ascii clusters
            p = ROOT / f.split(" ")[0]
            if p.is_file():
                t = p.read_text(encoding="utf-8")
                clusters = sorted(set(re.findall(r"[^\x00-\x7f]{1,8}", t)))
                print("       remaining:", clusters[:40])
        return 1

    # Final verification on index.html
    idx = (ROOT / "index.html").read_text(encoding="utf-8")
    sample_i = idx.find("department")
    print("Sample:", repr(idx[sample_i : sample_i + 55]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

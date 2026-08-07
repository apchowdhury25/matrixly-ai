#!/usr/bin/env python3
"""
Wire i18n scripts + common nav/footer data-i18n attributes across marketing pages.
Skips agent internal dashboards under agents/*/static and admin.
Brand product names (SocialForge, BookWise, etc.) are left as English.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_PARTS = (
    "agents\\book-wise",
    "agents/book-wise",
    "agents\\connect-forge",
    "agents/connect-forge",
    "agents\\content-forge",
    "agents/content-forge",
    "agents\\doc-forge",
    "agents/doc-forge",
    "agents\\etf-analyzer",
    "agents/etf-analyzer",
    "agents\\invoice-forge",
    "agents/invoice-forge",
    "agents\\meet-wise",
    "agents/meet-wise",
    "agents\\pipeline-forge",
    "agents/pipeline-forge",
    "agents\\seo-bespoke",
    "agents/seo-bespoke",
    "agents\\seo-forge",
    "agents/seo-forge",
    "agents\\social-forge",
    "agents/social-forge",
    "agents\\starter-pack",
    "agents/starter-pack",
    "agents\\support-forge",
    "agents/support-forge",
    "admin\\",
    "admin/",
    "node_modules",
)

# Exact text → data-i18n key (nav/common only; product names intentionally omitted)
TEXT_TO_KEY = [
    (r">How it Works<", r' data-i18n="nav.howItWorks">How it Works<'),
    (r">Agents<", r' data-i18n="nav.agents">Agents<'),
    (r">Resources<", r' data-i18n="nav.resources">Resources<'),
    (r">Integrations<", r' data-i18n="nav.integrations">Integrations<'),
    (r">Pricing<", r' data-i18n="nav.pricing">Pricing<'),
    (r">Get Started<", r' data-i18n="nav.getStarted">Get Started<'),
    (r">Privacy<", r' data-i18n="footer.privacy">Privacy<'),
    (r">Terms<", r' data-i18n="footer.terms">Terms<'),
    (r">Contact<", r' data-i18n="footer.contact">Contact<'),
    (r">Learn more<", r' data-i18n="common.learnMore">Learn more<'),
    (r">Try free<", r' data-i18n="common.tryFree">Try free<'),
]

SCRIPT_BLOCK = (
    '  <script src="/js/i18n.js" defer></script>\n'
    '  <script src="/js/lang-selector.js" defer></script>\n'
)


def should_skip(path: Path) -> bool:
    s = str(path)
    return any(p in s for p in SKIP_PARTS)


def wire_scripts(html: str) -> str:
    if "/js/i18n.js" in html:
        if "/js/lang-selector.js" not in html:
            html = html.replace(
                '<script src="/js/i18n.js" defer></script>',
                SCRIPT_BLOCK.rstrip() + "\n",
                1,
            )
        return html
    # insert before </body>
    if re.search(r"</body>", html, re.I):
        return re.sub(r"</body>", SCRIPT_BLOCK + "</body>", html, count=1, flags=re.I)
    return html + "\n" + SCRIPT_BLOCK


def wire_nav_attrs(html: str) -> str:
    # Only add if not already present on that occurrence — simple replacements for common nav
    for pattern, replacement in TEXT_TO_KEY:
        # Avoid double-wiring: skip if data-i18n already near this text
        def replacer(m, rep=replacement):
            # look back 80 chars for data-i18n
            start = m.start()
            window = html[max(0, start - 80) : start]
            if "data-i18n=" in window:
                return m.group(0)
            return rep

        # Use iterative safe replace for first N of each
        # Simpler: replace only tags without data-i18n already
        plain = pattern  # like >Agents<
        key_attr = re.search(r'data-i18n="([^"]+)"', replacement)
        if not key_attr:
            continue
        key = key_attr.group(1)
        # Replace <a ...>Agents</a> style without existing data-i18n for that key nearby
        tag_re = re.compile(
            r"(<(?:a|button|span|p|h[1-6]|li)[^>]*?)(?<!data-i18n=\"" + re.escape(key) + r"\")(>)("
            + re.escape(plain.strip("<>"))
            + r")(</)",
            re.I,
        )

        def tag_sub(m):
            open_tag = m.group(1)
            if "data-i18n=" in open_tag:
                return m.group(0)
            return f'{open_tag} data-i18n="{key}"{m.group(2)}{m.group(3)}{m.group(4)}'

        html = tag_re.sub(tag_sub, html)
    return html


def process(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    html = original
    html = wire_scripts(html)
    html = wire_nav_attrs(html)
    if html != original:
        path.write_text(html, encoding="utf-8")
        return True
    return False


def main():
    changed = []
    for path in sorted(ROOT.rglob("index.html")):
        if should_skip(path):
            continue
        if process(path):
            changed.append(str(path.relative_to(ROOT)))
    print(f"Updated {len(changed)} pages:")
    for c in changed:
        print(" ", c)


if __name__ == "__main__":
    main()

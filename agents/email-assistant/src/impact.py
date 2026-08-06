"""First 24-hour impact report for SMB owners (screenshot-friendly)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .config import SUMMARIES_DIR
from .triage import TriageItem


def build_impact_report(
    items: list[TriageItem],
    cfg: dict[str, Any] | None = None,
    *,
    mailbox: str | None = None,
    backend: str | None = None,
    test_mode: bool = False,
) -> str:
    """Short 'Your first 24-hour impact report' after the first successful triage."""
    cfg = cfg or {}
    account = cfg.get("account") or {}
    primary = mailbox or account.get("primary_email") or "your inbox"
    agent = cfg.get("agent") or {}
    be = backend or agent.get("backend") or "gmail"
    now = datetime.now().astimezone()

    urgent = [i for i in items if i.is_urgent or i.category == "urgent"]
    needs = [i for i in items if i.category == "needs_reply"]
    news = [i for i in items if i.category == "newsletter"]
    auto = [i for i in items if i.category == "automated"]
    labeled = sum(1 for i in items if i.labels_applied)

    # Rough time-saved heuristic for SMB demo (conservative, not a guarantee)
    minutes_saved = max(5, len(items) * 2 + len(urgent) * 5 + len(needs) * 3)

    mode_line = (
        "_Generated in **Test Mode** with sample messages — connect Gmail for live results._"
        if test_mode
        else "_Generated from your live mailbox. Drafts only — nothing was sent to customers._"
    )

    lines = [
        "# Your first 24-hour impact report",
        "",
        f"**Business mailbox:** {primary}",
        f"**Connected via:** {be}",
        f"**Report time:** {now.strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "## What your Email Assistant just did",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| Messages reviewed | {len(items)} |",
        f"| Flagged urgent | {len(urgent)} |",
        f"| Needs your reply | {len(needs)} |",
        f"| Newsletters / automated | {len(news) + len(auto)} |",
        f"| Labels applied | {labeled} |",
        f"| Est. minutes you get back | ~{minutes_saved} |",
        "",
        "## Top items needing you",
        "",
    ]

    top = (urgent + [i for i in needs if i not in urgent])[:5]
    if not top:
        lines.append("_Inbox looks calm — no urgent or reply-needed items in this pass._")
        lines.append("")
    else:
        for n, i in enumerate(top, 1):
            m = i.message
            subj = m.get("subject") or "(no subject)"
            frm = m.get("from_email") or m.get("from") or "?"
            tag = "URGENT" if (i.is_urgent or i.category == "urgent") else "REPLY"
            lines.append(f"{n}. **[{tag}]** {subj}")
            lines.append(f"   - From: {frm}")
            lines.append(f"   - Why: {'; '.join((i.reasons or ['priority'])[:2])}")
            lines.append("")

    lines.extend(
        [
            "## How Matrixly protects you",
            "",
            "- **Drafts only** for customer replies — you always hit Send.",
            "- Your emails stay under **your** Google account control.",
            "- We **do not train** on your mail. Revoke access anytime in Google Account → Security.",
            "",
            "## Next 3 steps (under 5 minutes)",
            "",
            "1. Open Gmail and check the new **Matrixly/** labels.",
            "2. Review any **draft** replies the assistant prepared.",
            "3. Run `python -m src.cli summary` for a daily brief in your own inbox.",
            "",
            mode_line,
            "",
            "— Matrixly Email Assistant · Built for small business owners",
        ]
    )
    return "\n".join(lines)


def write_impact_report(text: str, *, stamp: str | None = None) -> Path:
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    name = stamp or datetime.now().strftime("%Y-%m-%d")
    path = SUMMARIES_DIR / f"impact-first-24h-{name}.md"
    path.write_text(text, encoding="utf-8")
    # Also keep a stable latest path for easy open/screenshot
    latest = SUMMARIES_DIR / "impact-first-24h-latest.md"
    latest.write_text(text, encoding="utf-8")
    return path

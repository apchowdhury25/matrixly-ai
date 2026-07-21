"""Pipeline hygiene checks (Attio/SF-style cleanliness)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import HygieneIssue
from .store import CRMStore


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def run_hygiene(store: CRMStore, cfg: dict[str, Any]) -> list[HygieneIssue]:
    h = cfg.get("hygiene") or {}
    stale_days = int(h.get("stale_deal_days") or 14)
    act_days = int(h.get("max_open_deals_without_activity_days") or 7)
    now = datetime.now(timezone.utc)
    issues: list[HygieneIssue] = []

    for c in store.list_contacts():
        if h.get("require_email_on_contact", True) and not c.email:
            issues.append(
                HygieneIssue("contact", c.id, "high", "missing_email", f"{c.full_name or c.id} missing email")
            )
        if not c.company_name:
            issues.append(
                HygieneIssue("contact", c.id, "medium", "missing_company", f"{c.email} missing company")
            )
        if h.get("require_owner", True) and not c.owner:
            issues.append(
                HygieneIssue("contact", c.id, "low", "missing_owner", f"{c.email} missing owner")
            )

    for d in store.list_deals():
        if h.get("require_owner", True) and not d.owner:
            issues.append(
                HygieneIssue("deal", d.id, "medium", "missing_owner", f"Deal '{d.name}' missing owner")
            )
        if h.get("require_next_step", True) and not d.next_step:
            issues.append(
                HygieneIssue("deal", d.id, "high", "missing_next_step", f"Deal '{d.name}' missing next step")
            )
        last = _parse_ts(d.last_activity_at) or _parse_ts(d.updated_at)
        if last:
            age = (now - last).days
            if age >= stale_days:
                issues.append(
                    HygieneIssue(
                        "deal",
                        d.id,
                        "high",
                        "stale_deal",
                        f"Deal '{d.name}' stale ({age}d since activity)",
                    )
                )
            elif age >= act_days:
                issues.append(
                    HygieneIssue(
                        "deal",
                        d.id,
                        "medium",
                        "inactive_deal",
                        f"Deal '{d.name}' inactive {age}d",
                    )
                )

    # Severity order
    order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda i: (order.get(i.severity, 9), i.entity_type))
    return issues


def hygiene_report(issues: list[HygieneIssue]) -> str:
    lines = ["# CRM Hygiene Report", ""]
    if not issues:
        lines.append("No issues found. Pipeline looks clean.")
        return "\n".join(lines)
    by: dict[str, int] = {}
    for i in issues:
        by[i.severity] = by.get(i.severity, 0) + 1
    lines.append(f"**Total issues:** {len(issues)}")
    for s in ("high", "medium", "low"):
        if s in by:
            lines.append(f"- **{s}:** {by[s]}")
    lines.append("")
    for i in issues:
        lines.append(f"- [{i.severity.upper()}] `{i.code}` {i.entity_type}/{i.entity_id}: {i.message}")
    return "\n".join(lines)

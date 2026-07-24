"""Report Agent — AR aging and processing summary."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from ..models import InvoiceStatus, ReportSummary
from ..services.store import InvoiceStore


def generate_report(store: InvoiceStore, cfg: dict) -> ReportSummary:
    items = store.list(limit=1000)
    by_status: dict[str, int] = defaultdict(int)
    exceptions = 0
    posted = 0
    open_ar = 0.0
    aging: dict[str, float] = {"current": 0.0, "1-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    currency = (cfg.get("business") or {}).get("currency") or "USD"
    today = datetime.now(timezone.utc).date()

    for inv in items:
        by_status[inv.status.value] += 1
        if inv.status in {InvoiceStatus.exception, InvoiceStatus.pending_hitl} or inv.exceptions:
            exceptions += 1
        if inv.status == InvoiceStatus.posted:
            posted += 1
        if inv.ar_status in {"open", "reminded"} and inv.status != InvoiceStatus.void:
            amt = float(inv.amount_due or inv.total or 0)
            open_ar += amt
            if inv.due_date:
                try:
                    due = datetime.strptime(inv.due_date[:10], "%Y-%m-%d").date()
                    days = (today - due).days
                    if days <= 0:
                        aging["current"] += amt
                    elif days <= 30:
                        aging["1-30"] += amt
                    elif days <= 60:
                        aging["31-60"] += amt
                    elif days <= 90:
                        aging["61-90"] += amt
                    else:
                        aging["90+"] += amt
                except ValueError:
                    aging["current"] += amt
            else:
                aging["current"] += amt

    return ReportSummary(
        total_invoices=len(items),
        by_status=dict(by_status),
        exceptions=exceptions,
        posted=posted,
        open_ar_total=round(open_ar, 2),
        aging={k: round(v, 2) for k, v in aging.items()},
        currency=currency,
    )


def report_markdown(summary: ReportSummary) -> str:
    lines = [
        f"# InvoiceForge AR Report",
        f"",
        f"- Total invoices: **{summary.total_invoices}**",
        f"- Posted: **{summary.posted}**",
        f"- Exceptions / HITL: **{summary.exceptions}**",
        f"- Open AR: **{summary.currency} {summary.open_ar_total:,.2f}**",
        f"",
        f"## By status",
    ]
    for k, v in sorted(summary.by_status.items()):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Aging")
    for k, v in summary.aging.items():
        lines.append(f"- {k}: {summary.currency} {v:,.2f}")
    return "\n".join(lines) + "\n"

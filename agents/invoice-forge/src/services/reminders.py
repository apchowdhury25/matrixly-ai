"""AR payment reminders."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..models import Invoice, new_id, utc_now


class ReminderService:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.dir = Path(data_dir) / "reminders"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg

    def schedule_for_invoice(self, invoice: Invoice) -> list[dict[str, Any]]:
        ar = self.cfg.get("ar") or {}
        if not ar.get("enabled", True):
            return []
        if not invoice.due_date:
            return []
        try:
            due = datetime.strptime(invoice.due_date[:10], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return []

        created: list[dict[str, Any]] = []
        for days in ar.get("reminder_days_after_due") or [1, 7, 14]:
            due_at = due + timedelta(days=int(days))
            item = {
                "id": new_id("rem_"),
                "invoice_id": invoice.id,
                "days_after_due": days,
                "due_at": due_at.isoformat(),
                "status": "scheduled",
                "to": invoice.vendor_email or "ap-team@example.com",
                "message": (
                    f"Payment reminder: Invoice {invoice.invoice_number or invoice.id} "
                    f"from {invoice.vendor_name or 'vendor'} total "
                    f"{invoice.currency} {invoice.total or invoice.amount_due} "
                    f"was due {invoice.due_date}. Please arrange payment or update status."
                ),
                "created_at": utc_now(),
            }
            (self.dir / f"{item['id']}.json").write_text(
                json.dumps(item, indent=2), encoding="utf-8"
            )
            created.append(item)
        return created

    def due(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        out: list[dict[str, Any]] = []
        for p in self.dir.glob("*.json"):
            try:
                item = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if item.get("status") != "scheduled":
                continue
            try:
                due = datetime.fromisoformat(item["due_at"].replace("Z", "+00:00"))
            except Exception:
                continue
            if due <= now:
                out.append(item)
        return out

    def mark_sent(self, reminder_id: str) -> None:
        p = self.dir / f"{reminder_id}.json"
        if not p.exists():
            return
        item = json.loads(p.read_text(encoding="utf-8"))
        item["status"] = "sent"
        item["sent_at"] = utc_now()
        p.write_text(json.dumps(item, indent=2), encoding="utf-8")

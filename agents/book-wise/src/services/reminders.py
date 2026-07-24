"""Smart reminder scheduling for no-show reduction."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..models import Booking, new_id, utc_now


class ReminderService:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.dir = Path(data_dir) / "reminders"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg

    def schedule_for_booking(self, booking: Booking) -> list[dict[str, Any]]:
        rem = self.cfg.get("reminders") or {}
        if not rem.get("enabled", True):
            return []
        hours_list = rem.get("hours_before") or [24, 2]
        try:
            start = datetime.fromisoformat(booking.start_iso.replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        except Exception:
            return []

        created: list[dict[str, Any]] = []
        for h in hours_list:
            due = start - timedelta(hours=float(h))
            if due <= datetime.now(timezone.utc):
                continue
            item = {
                "id": new_id("rem_"),
                "booking_id": booking.id,
                "hours_before": h,
                "due_at": due.isoformat(),
                "status": "scheduled",
                "channel": "email" if booking.customer.email else "chat",
                "customer_email": booking.customer.email,
                "message": (
                    f"Reminder: your {booking.service_name} is at {booking.start_iso} "
                    f"({booking.timezone}). Reply CANCEL to cancel or RESCHEDULE to move it."
                ),
                "created_at": utc_now(),
            }
            path = self.dir / f"{item['id']}.json"
            path.write_text(json.dumps(item, indent=2), encoding="utf-8")
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

    def cancel_for_booking(self, booking_id: str) -> int:
        n = 0
        for p in self.dir.glob("*.json"):
            try:
                item = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if item.get("booking_id") == booking_id and item.get("status") == "scheduled":
                item["status"] = "cancelled"
                p.write_text(json.dumps(item, indent=2), encoding="utf-8")
                n += 1
        return n

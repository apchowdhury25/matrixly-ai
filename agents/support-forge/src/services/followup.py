"""Simple follow-up queue (JSON files; process via CLI)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..models import new_id, utc_now


class FollowupQueue:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "followups"
        self.dir.mkdir(parents=True, exist_ok=True)

    def schedule(
        self,
        ticket_id: str,
        message: str,
        hours_from_now: float = 24,
        channel: str = "email",
        customer_email: str | None = None,
    ) -> dict[str, Any]:
        due = datetime.now(timezone.utc) + timedelta(hours=hours_from_now)
        item = {
            "id": new_id("fu_"),
            "ticket_id": ticket_id,
            "message": message,
            "channel": channel,
            "customer_email": customer_email,
            "due_at": due.isoformat(),
            "status": "scheduled",
            "created_at": utc_now(),
        }
        path = self.dir / f"{item['id']}.json"
        path.write_text(json.dumps(item, indent=2), encoding="utf-8")
        return item

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

    def mark_done(self, followup_id: str) -> None:
        p = self.dir / f"{followup_id}.json"
        if not p.exists():
            return
        item = json.loads(p.read_text(encoding="utf-8"))
        item["status"] = "done"
        item["completed_at"] = utc_now()
        p.write_text(json.dumps(item, indent=2), encoding="utf-8")

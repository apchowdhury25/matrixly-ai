"""HITL queue for outbound SMS approval."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import HitlAction, new_id, utc_now


class HitlQueue:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "hitl"
        self.dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, kind: str, payload: dict[str, Any]) -> HitlAction:
        action = HitlAction(id=new_id("hitl_"), kind=kind, payload=payload)
        self._write(action)
        return action

    def _write(self, action: HitlAction) -> None:
        path = self.dir / f"{action.id}.json"
        path.write_text(
            json.dumps(action.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get(self, action_id: str) -> HitlAction | None:
        path = self.dir / f"{action_id}.json"
        if not path.exists():
            return None
        return HitlAction(**json.loads(path.read_text(encoding="utf-8")))

    def list_pending(self, limit: int = 50) -> list[HitlAction]:
        items: list[HitlAction] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                a = HitlAction(**json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
            if a.status == "pending":
                items.append(a)
            if len(items) >= limit:
                break
        return items

    def decide(
        self,
        action_id: str,
        *,
        approve: bool,
        decided_by: str = "owner",
        note: str = "",
    ) -> HitlAction | None:
        action = self.get(action_id)
        if not action:
            return None
        action.status = "approved" if approve else "rejected"
        action.decided_at = utc_now()
        action.decided_by = decided_by
        action.note = note or None
        self._write(action)
        return action

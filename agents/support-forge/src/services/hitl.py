"""Human-in-the-loop approval queue."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import HitlAction, new_id, utc_now


class HitlQueue:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "hitl"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, action_id: str) -> Path:
        return self.dir / f"{action_id}.json"

    def enqueue(
        self,
        kind: str,
        payload: dict[str, Any],
        ticket_id: str | None = None,
        session_id: str | None = None,
    ) -> HitlAction:
        action = HitlAction(
            id=new_id("hitl_"),
            kind=kind,
            payload=payload,
            ticket_id=ticket_id,
            session_id=session_id,
        )
        self._write(action)
        return action

    def get(self, action_id: str) -> HitlAction | None:
        p = self._path(action_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return HitlAction(**json.load(f))

    def list_pending(self) -> list[HitlAction]:
        out: list[HitlAction] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    a = HitlAction(**json.load(f))
                if a.status == "pending":
                    out.append(a)
            except Exception:
                continue
        return out

    def list_all(self, limit: int = 50) -> list[HitlAction]:
        out: list[HitlAction] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True)[:limit]:
            try:
                with p.open(encoding="utf-8") as f:
                    out.append(HitlAction(**json.load(f)))
            except Exception:
                continue
        return out

    def decide(
        self,
        action_id: str,
        approve: bool,
        decided_by: str = "admin",
        note: str | None = None,
    ) -> HitlAction | None:
        action = self.get(action_id)
        if not action or action.status != "pending":
            return None
        action.status = "approved" if approve else "rejected"
        action.decided_at = utc_now()
        action.decided_by = decided_by
        action.note = note
        self._write(action)
        return action

    def _write(self, action: HitlAction) -> None:
        with self._path(action.id).open("w", encoding="utf-8") as f:
            json.dump(action.model_dump(), f, indent=2, ensure_ascii=False)

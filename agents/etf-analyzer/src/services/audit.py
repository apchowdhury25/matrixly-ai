"""Audit log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import utc_now


class AuditLog:
    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / "audit" / "events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **detail: Any) -> dict[str, Any]:
        row = {"event": event, "ts": utc_now(), **detail}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(out))

"""Append-only audit log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import utc_now


class AuditLog:
    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / "audit" / "events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **kwargs: Any) -> None:
        row = {"event": event, "ts": utc_now(), **kwargs}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

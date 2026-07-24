"""Append-only audit logging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import utc_now


class AuditLog:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "audit"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "events.jsonl"

    def write(self, event: str, **detail: Any) -> dict[str, Any]:
        row = {"event": event, "ts": utc_now(), **detail}
        # Light redaction of obvious secrets in string values
        safe = {k: _redact(v) for k, v in row.items()}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe, ensure_ascii=False) + "\n")
        return safe

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(out))


def _redact(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    import re

    v = re.sub(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*\S+", r"\1=***", v)
    v = re.sub(r"\b\d{13,19}\b", "[card]", v)
    return v

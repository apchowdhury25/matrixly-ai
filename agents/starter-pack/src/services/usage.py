"""Pack-level usage tracking hooks (for future SaaS billing)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..models import utc_now


class UsageMeter:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "usage"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "usage.jsonl"

    def record(self, action: str, agent_id: str = "", **extra: Any) -> dict[str, Any]:
        row = {"ts": utc_now(), "action": action, "agent_id": agent_id, **extra}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return row

    def summary(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"events": 0, "by_action": {}, "by_agent": {}}
        by_a: dict[str, int] = defaultdict(int)
        by_g: dict[str, int] = defaultdict(int)
        n = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += 1
            by_a[row.get("action") or "unknown"] += 1
            by_g[row.get("agent_id") or "pack"] += 1
        return {"events": n, "by_action": dict(by_a), "by_agent": dict(by_g)}

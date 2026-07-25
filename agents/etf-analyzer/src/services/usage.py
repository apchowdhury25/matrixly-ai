"""Usage tracking."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..llm import cost_usd
from ..models import utc_now


class UsageMeter:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.path = Path(data_dir) / "usage" / "usage.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        action: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        report_id: str = "",
    ) -> dict[str, Any]:
        est = cost_usd(self.cfg, tokens_in, tokens_out)
        row = {
            "ts": utc_now(),
            "action": action,
            "report_id": report_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "estimated_cost_usd": round(est, 6),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return row

    def summary(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"events": 0, "by_action": {}}
        by_a: dict[str, int] = defaultdict(int)
        n = tin = tout = 0
        cost = 0.0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += 1
            by_a[row.get("action") or "unknown"] += 1
            tin += int(row.get("tokens_in") or 0)
            tout += int(row.get("tokens_out") or 0)
            cost += float(row.get("estimated_cost_usd") or 0)
        return {
            "events": n,
            "tokens_in": tin,
            "tokens_out": tout,
            "estimated_cost_usd": round(cost, 4),
            "by_action": dict(by_a),
        }

"""Usage + cost tracking."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..llm import cost_usd
from ..models import utc_now


class UsageMeter:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.dir = Path(data_dir) / "usage"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "usage.jsonl"
        self.cfg = cfg

    def record(
        self,
        *,
        action: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        campaign_id: str = "",
    ) -> dict[str, Any]:
        est = cost_usd(self.cfg, tokens_in, tokens_out)
        row = {
            "ts": utc_now(),
            "action": action,
            "campaign_id": campaign_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "estimated_cost_usd": round(est, 6),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return row

    def summary(self, days: int = 30) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "events": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "estimated_cost_usd": 0.0,
                "by_action": {},
            }
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        events = tin = tout = 0
        cost = 0.0
        by_a: dict[str, int] = defaultdict(int)
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = row.get("ts") or ""
            try:
                t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except ValueError:
                t = 0
            if t < cutoff:
                continue
            events += 1
            tin += int(row.get("tokens_in") or 0)
            tout += int(row.get("tokens_out") or 0)
            cost += float(row.get("estimated_cost_usd") or 0)
            by_a[row.get("action") or "unknown"] += 1
        return {
            "events": events,
            "tokens_in": tin,
            "tokens_out": tout,
            "estimated_cost_usd": round(cost, 4),
            "by_action": dict(by_a),
            "days": days,
        }

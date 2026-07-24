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
        channel: str,
        session_id: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        action: str = "",
        message_id: str = "",
    ) -> dict[str, Any]:
        est = cost_usd(self.cfg, tokens_in, tokens_out)
        row = {
            "ts": utc_now(),
            "channel": channel,
            "session_id": session_id,
            "message_id": message_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "estimated_cost_usd": round(est, 6),
            "action": action,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return row

    def summary(self, days: int = 30) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "messages": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "estimated_cost_usd": 0.0,
                "by_channel": {},
            }
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        messages = tin = tout = 0
        cost = 0.0
        by_ch: dict[str, int] = defaultdict(int)
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
            messages += 1
            tin += int(row.get("tokens_in") or 0)
            tout += int(row.get("tokens_out") or 0)
            cost += float(row.get("estimated_cost_usd") or 0)
            by_ch[row.get("channel") or "unknown"] += 1
        return {
            "messages": messages,
            "tokens_in": tin,
            "tokens_out": tout,
            "estimated_cost_usd": round(cost, 4),
            "by_channel": dict(by_ch),
            "days": days,
        }

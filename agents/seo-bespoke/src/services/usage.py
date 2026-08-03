"""Token / cost usage meter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..llm import cost_usd
from ..models import utc_now


class UsageMeter:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.path = Path(data_dir) / "usage" / "meter.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"entries": [], "totals": {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}})

    def _read(self) -> dict[str, Any]:
        with self.path.open(encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record(
        self,
        action: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        data = self._read()
        c = cost_usd(self.cfg, tokens_in, tokens_out)
        entry = {
            "action": action,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(c, 6),
            "run_id": run_id,
            "ts": utc_now(),
        }
        data.setdefault("entries", []).append(entry)
        totals = data.setdefault("totals", {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0})
        totals["tokens_in"] = int(totals.get("tokens_in") or 0) + tokens_in
        totals["tokens_out"] = int(totals.get("tokens_out") or 0) + tokens_out
        totals["cost_usd"] = round(float(totals.get("cost_usd") or 0) + c, 6)
        self._write(data)
        return entry

    def summary(self) -> dict[str, Any]:
        return self._read().get("totals") or {}

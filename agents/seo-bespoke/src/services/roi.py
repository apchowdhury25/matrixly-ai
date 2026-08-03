"""ROI ledger — hours saved, leads, revenue (owner-attributed only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import new_id, utc_now


class RoiLedger:
    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / "roi" / "ledger.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"events": []})

    def _read(self) -> dict[str, Any]:
        with self.path.open(encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record(
        self,
        *,
        hours_saved: float = 0.0,
        leads_attributed: int = 0,
        revenue_usd: float = 0.0,
        note: str = "",
        run_id: str | None = None,
        profile_id: str | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        data = self._read()
        event = {
            "id": new_id("roi_"),
            "hours_saved": hours_saved,
            "leads_attributed": leads_attributed,
            "revenue_usd": revenue_usd,
            "note": note,
            "run_id": run_id,
            "profile_id": profile_id,
            "source": source,
            "created_at": utc_now(),
        }
        data.setdefault("events", []).append(event)
        self._write(data)
        return event

    def summary(self) -> dict[str, Any]:
        events = self._read().get("events") or []
        return {
            "events": len(events),
            "hours_saved": round(sum(float(e.get("hours_saved") or 0) for e in events), 2),
            "leads_attributed": sum(int(e.get("leads_attributed") or 0) for e in events),
            "revenue_usd": round(sum(float(e.get("revenue_usd") or 0) for e in events), 2),
            "disclaimer": "All ROI figures are owner-reported or pipeline time estimates — not invented traffic/revenue claims.",
        }

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        events = self._read().get("events") or []
        return list(reversed(events[-limit:]))

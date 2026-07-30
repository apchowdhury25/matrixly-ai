"""ROI events for Matrixly dashboard feed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import utc_now


class RoiLedger:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "roi"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "events.jsonl"
        self.summary_path = self.dir / "summary.json"

    def record(
        self,
        *,
        hours_saved: float = 0.0,
        leads_attributed: int = 0,
        revenue_usd: float = 0.0,
        note: str = "",
        job_id: str = "",
        source: str = "manual",
    ) -> dict[str, Any]:
        row = {
            "ts": utc_now(),
            "hours_saved": float(hours_saved),
            "leads_attributed": int(leads_attributed),
            "revenue_usd": float(revenue_usd),
            "note": note,
            "job_id": job_id,
            "source": source,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        self._refresh_summary()
        return row

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
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

    def summary(self) -> dict[str, Any]:
        if self.summary_path.exists():
            try:
                return json.loads(self.summary_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._refresh_summary()

    def _refresh_summary(self) -> dict[str, Any]:
        hours = leads = revenue = 0.0
        count = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                count += 1
                hours += float(row.get("hours_saved") or 0)
                leads += int(row.get("leads_attributed") or 0)
                revenue += float(row.get("revenue_usd") or 0)
        summary = {
            "events": count,
            "hours_saved": round(hours, 2),
            "leads_attributed": int(leads),
            "revenue_usd": round(revenue, 2),
            "updated_at": utc_now(),
            "agent": "seo-forge",
        }
        self.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

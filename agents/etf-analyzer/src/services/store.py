"""Report + session persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import AnalysisReport, utc_now


class ReportStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "reports"
        self.sessions = Path(data_dir) / "sessions"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.sessions.mkdir(parents=True, exist_ok=True)

    def save(self, report: AnalysisReport) -> AnalysisReport:
        path = self.dir / f"{report.id}.json"
        path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
        md = self.dir / f"{report.id}.md"
        md.write_text(report.markdown or "", encoding="utf-8")
        return report

    def get(self, report_id: str) -> AnalysisReport | None:
        p = self.dir / f"{report_id}.json"
        if not p.exists():
            return None
        return AnalysisReport(**json.loads(p.read_text(encoding="utf-8")))

    def list(self, limit: int = 30) -> list[AnalysisReport]:
        items: list[AnalysisReport] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                items.append(AnalysisReport(**json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
            if len(items) >= limit:
                break
        return items

    def save_session(self, session_id: str, data: dict[str, Any]) -> None:
        data = {**data, "updated_at": utc_now()}
        (self.sessions / f"{session_id}.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        p = self.sessions / f"{session_id}.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

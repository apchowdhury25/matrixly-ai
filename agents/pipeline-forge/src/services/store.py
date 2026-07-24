"""Pipeline run persistence + exports."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..models import PipelineRun, utc_now


class PipelineStore:
    def __init__(self, data_dir: str | Path) -> None:
        data_dir = Path(data_dir)
        self.dir = data_dir / "pipeline"
        self.lists = data_dir / "lists"
        self.exports = data_dir / "exports"
        self.scores_dir = data_dir / "scores"
        self.insights_dir = data_dir / "insights"
        for d in (self.dir, self.lists, self.exports, self.scores_dir, self.insights_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save(self, run: PipelineRun) -> PipelineRun:
        run.updated_at = utc_now()
        path = self.dir / f"{run.id}.json"
        path.write_text(json.dumps(run.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return run

    def get(self, run_id: str) -> PipelineRun | None:
        p = self.dir / f"{run_id}.json"
        if not p.exists():
            return None
        return PipelineRun(**json.loads(p.read_text(encoding="utf-8")))

    def list(self, status: str | None = None, limit: int = 50) -> list[PipelineRun]:
        items: list[PipelineRun] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                run = PipelineRun(**json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
            if status and run.status.value != status:
                continue
            items.append(run)
            if len(items) >= limit:
                break
        return items

    def export(self, run: PipelineRun) -> list[str]:
        base = self.exports / run.id
        base.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        def write(name: str, text: str) -> None:
            p = base / name
            p.write_text(text, encoding="utf-8")
            paths.append(str(p))

        write("run.json", json.dumps(run.model_dump(), indent=2, ensure_ascii=False))
        write("scores.json", json.dumps([s.model_dump() for s in run.scores], indent=2))
        write(
            "priority.json",
            json.dumps([p.model_dump() for p in run.priority_list], indent=2),
        )
        write("risks.json", json.dumps([r.model_dump() for r in run.risks], indent=2))
        write("insights.json", json.dumps(run.insights, indent=2))
        write("crm_updates.json", json.dumps([c.model_dump() for c in run.crm_updates], indent=2))

        # CSV priority list for reps
        csv_path = base / "priority.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["rank", "opportunity_id", "name", "score", "rep", "due", "next_action", "why"])
            for item in run.priority_list:
                w.writerow(
                    [
                        item.rank,
                        item.opportunity_id,
                        item.name,
                        item.score,
                        item.rep,
                        item.due,
                        item.next_action,
                        item.why,
                    ]
                )
        paths.append(str(csv_path))

        # copy latest list
        list_path = self.lists / f"{run.id}.json"
        list_path.write_text(
            json.dumps(
                {
                    "run_id": run.id,
                    "title": run.list_title,
                    "items": [p.model_dump() for p in run.priority_list],
                    "created_at": run.created_at,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        paths.append(str(list_path))

        run.export_paths = paths
        self.save(run)
        return paths

    def latest_list(self) -> dict[str, Any] | None:
        files = sorted(self.lists.glob("*.json"), reverse=True)
        if not files:
            return None
        return json.loads(files[0].read_text(encoding="utf-8"))

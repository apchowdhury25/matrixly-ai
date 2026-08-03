"""Graph run persistence + file exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import GraphRun, utc_now


class RunStore:
    def __init__(self, data_dir: str | Path) -> None:
        data_dir = Path(data_dir)
        self.dir = data_dir / "runs"
        self.outputs = data_dir / "outputs"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.outputs.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.dir / f"{run_id}.json"

    def save(self, run: GraphRun) -> GraphRun:
        run.updated_at = utc_now()
        with self._path(run.id).open("w", encoding="utf-8") as f:
            json.dump(run.model_dump(), f, indent=2, ensure_ascii=False)
        return run

    def get(self, run_id: str) -> GraphRun | None:
        p = self._path(run_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return GraphRun(**json.load(f))

    def list(self, status: str | None = None, limit: int = 50) -> list[GraphRun]:
        items: list[GraphRun] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    run = GraphRun(**json.load(f))
            except Exception:
                continue
            if status and run.status.value != status:
                continue
            items.append(run)
            if len(items) >= limit:
                break
        return items

    def export_run(self, run: GraphRun) -> list[str]:
        base = self.outputs / run.id
        base.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        def write(name: str, text: str) -> None:
            p = base / name
            p.write_text(text, encoding="utf-8")
            paths.append(str(p))

        if run.profile:
            write("profile.json", json.dumps(run.profile.model_dump(), indent=2, ensure_ascii=False))
            if run.profile.summary_markdown:
                write("profile.md", run.profile.summary_markdown)

        write(
            "run_summary.json",
            json.dumps(
                {
                    "id": run.id,
                    "status": run.status.value,
                    "package_path": run.package_path,
                    "hitl_id": run.hitl_id,
                    "nodes": [
                        {
                            "id": n.node_id,
                            "name": n.name,
                            "status": n.status.value,
                            "duration_ms": n.duration_ms,
                        }
                        for n in run.node_results
                    ],
                    "safety": run.safety,
                    "smoke": run.smoke,
                },
                indent=2,
                ensure_ascii=False,
            ),
        )
        if run.architecture:
            write("architecture.json", json.dumps(run.architecture, indent=2, ensure_ascii=False))
        if run.package:
            write("package_manifest.json", json.dumps(run.package, indent=2, ensure_ascii=False))

        run.metadata["export_paths"] = paths
        return paths

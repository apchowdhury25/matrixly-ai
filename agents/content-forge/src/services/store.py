"""Job persistence + file exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import ContentJob, JobStatus, utc_now


class JobStore:
    def __init__(self, data_dir: str | Path) -> None:
        data_dir = Path(data_dir)
        self.dir = data_dir / "jobs"
        self.outputs = data_dir / "outputs"
        self.schedule_dir = data_dir / "schedule"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.schedule_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self.dir / f"{job_id}.json"

    def save(self, job: ContentJob) -> ContentJob:
        job.updated_at = utc_now()
        with self._path(job.id).open("w", encoding="utf-8") as f:
            json.dump(job.model_dump(), f, indent=2, ensure_ascii=False)
        return job

    def get(self, job_id: str) -> ContentJob | None:
        p = self._path(job_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return ContentJob(**json.load(f))

    def list(self, status: str | None = None, limit: int = 50) -> list[ContentJob]:
        items: list[ContentJob] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    job = ContentJob(**json.load(f))
            except Exception:
                continue
            if status and job.status.value != status:
                continue
            items.append(job)
            if len(items) >= limit:
                break
        return items

    def export_job(self, job: ContentJob) -> list[str]:
        """Write markdown/json exports under data/outputs/."""
        base = self.outputs / job.id
        base.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        def write(name: str, text: str) -> None:
            p = base / name
            p.write_text(text, encoding="utf-8")
            paths.append(str(p))

        edited = job.edited or job.draft or {}
        title = edited.get("title") or job.source_title or "content"
        body = edited.get("body_markdown") or ""
        if body:
            write(
                "blog.md",
                f"# {title}\n\n{body}\n",
            )
        meta = {
            "title": title,
            "meta_description": edited.get("meta_description"),
            "slug": edited.get("slug"),
            "quality_score": job.quality_score,
        }
        write("seo.json", json.dumps(meta, indent=2))

        assets = job.assets or {}
        if assets.get("linkedin"):
            write("linkedin.txt", str(assets["linkedin"]))
        if assets.get("twitter_thread"):
            write(
                "twitter_thread.txt",
                "\n\n".join(f"{i+1}/ {t}" for i, t in enumerate(assets["twitter_thread"])),
            )
        if assets.get("instagram"):
            write("instagram.txt", str(assets["instagram"]))
        if assets.get("newsletter"):
            nl = assets["newsletter"]
            if isinstance(nl, dict):
                write(
                    "newsletter.md",
                    f"Subject: {nl.get('subject','')}\n"
                    f"Preheader: {nl.get('preheader','')}\n\n"
                    f"{nl.get('body_markdown','')}\n",
                )
        if assets.get("ads"):
            write("ads.json", json.dumps(assets["ads"], indent=2))
        if assets.get("ideas"):
            write(
                "ideas.md",
                "# Content ideas\n\n" + "\n".join(f"- {i}" for i in assets["ideas"]) + "\n",
            )

        write("job.json", json.dumps(job.model_dump(), indent=2, ensure_ascii=False))
        job.export_paths = paths
        self.save(job)
        return paths

    def schedule(self, item: dict[str, Any]) -> Path:
        sid = item.get("id") or f"sch_{utc_now().replace(':','').replace('-','')[:16]}"
        item["id"] = sid
        path = self.schedule_dir / f"{sid}.json"
        path.write_text(json.dumps(item, indent=2), encoding="utf-8")
        return path

    def list_schedule(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for p in sorted(self.schedule_dir.glob("*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out

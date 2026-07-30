"""Job persistence + file exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import SeoJob, utc_now


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

    def save(self, job: SeoJob) -> SeoJob:
        job.updated_at = utc_now()
        with self._path(job.id).open("w", encoding="utf-8") as f:
            json.dump(job.model_dump(), f, indent=2, ensure_ascii=False)
        return job

    def get(self, job_id: str) -> SeoJob | None:
        p = self._path(job_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return SeoJob(**json.load(f))

    def list(self, status: str | None = None, limit: int = 50) -> list[SeoJob]:
        items: list[SeoJob] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    job = SeoJob(**json.load(f))
            except Exception:
                continue
            if status and job.status.value != status:
                continue
            items.append(job)
            if len(items) >= limit:
                break
        return items

    def export_job(self, job: SeoJob) -> list[str]:
        base = self.outputs / job.id
        base.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        def write(name: str, text: str) -> None:
            p = base / name
            p.write_text(text, encoding="utf-8")
            paths.append(str(p))

        draft = job.draft or {}
        title = draft.get("title") or job.title or "seo-content"
        body = draft.get("body_markdown") or ""
        if body:
            write(
                "content.md",
                f"# {title}\n\n"
                f"**Meta:** {draft.get('meta_description', '')}\n\n"
                f"**Slug:** {draft.get('slug', '')}\n\n"
                f"{body}\n",
            )
        write(
            "seo.json",
            json.dumps(
                {
                    "title": title,
                    "meta_description": draft.get("meta_description"),
                    "slug": draft.get("slug"),
                    "primary_keyword": draft.get("primary_keyword"),
                    "schema_suggestions": draft.get("schema_suggestions"),
                    "quality_score": job.quality_score,
                    "confidence": job.confidence,
                },
                indent=2,
            ),
        )
        if draft.get("social_variants"):
            write("social.json", json.dumps(draft["social_variants"], indent=2))
        if draft.get("gbp_post"):
            write("gbp_post.txt", str(draft["gbp_post"]))
        if draft.get("publishing_checklist"):
            write(
                "checklist.md",
                "# Publishing checklist\n\n"
                + "\n".join(f"- [ ] {i}" for i in draft["publishing_checklist"])
                + "\n",
            )
        if job.plan:
            write("plan.json", json.dumps(job.plan, indent=2))
        if job.research:
            write("research.json", json.dumps(job.research, indent=2))
        if job.local:
            write("local_seo.json", json.dumps(job.local, indent=2))
        if job.audit:
            write("audit.json", json.dumps(job.audit, indent=2))
        if job.roi_snapshot:
            write("roi.json", json.dumps(job.roi_snapshot, indent=2))
        write("job.json", json.dumps(job.model_dump(), indent=2, ensure_ascii=False))
        job.export_paths = paths
        self.save(job)
        return paths

    def schedule(self, item: dict[str, Any]) -> Path:
        sid = item.get("id") or f"sch_{utc_now().replace(':', '').replace('-', '')[:16]}"
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

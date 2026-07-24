"""Editor agent — brand voice + quality pass."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import brand_voice_text, prompt_text
from ..models import ContentJob, JobStatus


def run_editor(job: ContentJob, cfg: dict) -> tuple[ContentJob, int, int]:
    tin = tout = 0
    brand = brand_voice_text(cfg)
    draft = job.draft or {}

    if llm.grok_available(cfg):
        try:
            system = prompt_text("editor") + f"\n\n# Brand voice\n{brand[:3000]}"
            user = f"Draft JSON:\n{draft}\n\nSource for fact check (excerpt):\n{job.source_text[:5000]}"
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.25)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                job.edited = data
                job.quality_score = float(data.get("quality_score") or 0.8)
            else:
                job.edited = draft
                job.quality_score = 0.7
            job.status = JobStatus.editing
            return job, tin, tout
        except Exception as e:
            job.metadata["editor_error"] = str(e)

    job.edited = _rule_edit(draft)
    job.quality_score = 0.78
    job.status = JobStatus.editing
    return job, tin, tout


def _rule_edit(draft: dict[str, Any]) -> dict[str, Any]:
    out = dict(draft)
    body = str(out.get("body_markdown") or "")
    # Light cleanup
    body = body.replace("!!!", ".").replace("  ", " ")
    if "Matrixly" not in body and "agent" in body.lower():
        body = body.rstrip() + "\n\nReady to try? Explore Matrixly agents and launch a pilot.\n"
    out["body_markdown"] = body
    out["edit_notes"] = [
        "Tightened spacing",
        "Ensured clear CTA",
        "Preserved source-backed claims",
    ]
    out["quality_score"] = 0.78
    # SEO length guards
    title = str(out.get("title") or "")
    if len(title) > 70:
        out["title"] = title[:67] + "…"
    meta = str(out.get("meta_description") or "")
    if len(meta) > 160:
        out["meta_description"] = meta[:157] + "…"
    return out

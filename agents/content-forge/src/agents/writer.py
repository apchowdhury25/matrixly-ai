"""Writer agent — SEO blog draft."""

from __future__ import annotations

import re
from typing import Any

from .. import llm
from ..config import brand_voice_text, prompt_text
from ..models import ContentJob, JobStatus


def run_writer(job: ContentJob, cfg: dict) -> tuple[ContentJob, int, int]:
    tin = tout = 0
    brand = brand_voice_text(cfg)
    research = job.research or {}

    if llm.grok_available(cfg):
        try:
            system = prompt_text("writer") + f"\n\n# Brand voice\n{brand[:3000]}"
            user = (
                f"Goal: {job.goal}\nAudience: {job.audience}\n"
                f"Research JSON:\n{research}\n\n"
                f"Source excerpt:\n{job.source_text[:8000]}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.45)
            data = llm.extract_json(content)
            job.draft = data if isinstance(data, dict) else {"body_markdown": str(data)}
            job.status = JobStatus.writing
            return job, tin, tout
        except Exception as e:
            job.metadata["writer_error"] = str(e)

    job.draft = _rule_blog(job)
    job.status = JobStatus.writing
    return job, tin, tout


def _rule_blog(job: ContentJob) -> dict[str, Any]:
    research = job.research or {}
    title = job.source_title or "How SMBs Can Use Agentic AI Without Another Dashboard"
    if len(title) > 70:
        title = title[:67] + "…"
    keywords = research.get("seo_keywords") or ["AI agents", "SMB"]
    points = research.get("key_points") or []
    summary = research.get("summary") or job.source_text[:300]

    sections = []
    outline = ["Why this matters now", "What agentic AI changes", "A practical pilot path", "Next steps"]
    for i, h in enumerate(outline):
        body = points[i] if i < len(points) else summary
        sections.append(f"## {h}\n\n{body}\n")

    body = (
        f"{summary}\n\n"
        + "\n".join(sections)
        + "\n## Next steps\n\n"
        "Explore the Matrixly agent marketplace and start a free pilot. "
        "Keep humans in the loop for external actions while agents handle the busywork.\n"
    )
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    meta = f"Learn how SMBs use agentic AI to automate ops without extra dashboards. Keywords: {', '.join(keywords[:3])}."
    if len(meta) > 160:
        meta = meta[:157] + "…"
    return {
        "title": title,
        "meta_description": meta,
        "slug": slug,
        "body_markdown": body,
        "outline": outline,
    }

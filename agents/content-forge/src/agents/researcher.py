"""Researcher agent — extract angles, keywords, key points."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .. import llm
from ..config import brand_voice_text, prompt_text
from ..models import ContentJob


def run_researcher(job: ContentJob, cfg: dict) -> tuple[ContentJob, int, int]:
    tin = tout = 0
    text = job.source_text[: int((cfg.get("content") or {}).get("max_source_chars") or 40000)]
    brand = brand_voice_text(cfg)

    if llm.grok_available(cfg):
        try:
            system = prompt_text("researcher") + f"\n\n# Brand voice\n{brand[:3000]}"
            user = (
                f"Title: {job.source_title or '(untitled)'}\n"
                f"Goal: {job.goal}\nAudience: {job.audience or 'SMBs'}\n\n"
                f"Source:\n{text}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.3)
            data = llm.extract_json(content)
            job.research = data if isinstance(data, dict) else {"summary": str(data)}
            job.status = job.status  # type: ignore
            from ..models import JobStatus

            job.status = JobStatus.researching
            return job, tin, tout
        except Exception as e:
            job.metadata["research_error"] = str(e)

    job.research = _rule_research(text, job)
    from ..models import JobStatus

    job.status = JobStatus.researching
    return job, tin, tout


def _rule_research(text: str, job: ContentJob) -> dict[str, Any]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    stop = {
        "that",
        "this",
        "with",
        "from",
        "your",
        "have",
        "will",
        "they",
        "them",
        "about",
        "into",
        "when",
        "what",
        "which",
        "their",
        "than",
        "then",
        "also",
        "more",
        "most",
        "just",
        "like",
        "only",
        "other",
        "some",
        "such",
        "through",
        "after",
        "before",
        "because",
        "being",
        "while",
        "where",
        "would",
        "could",
        "should",
        "there",
        "these",
        "those",
        "using",
        "used",
        "make",
        "made",
    }
    counts = Counter(w for w in words if w not in stop)
    keywords = [w for w, _ in counts.most_common(8)]
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40][:6]
    points = sentences[:5] if sentences else [text[:200]]
    summary = " ".join(sentences[:2]) if sentences else text[:280]
    return {
        "summary": summary,
        "audience": job.audience or "SMB operators and founders",
        "key_points": points,
        "seo_keywords": keywords[:6] or ["AI agents", "SMB automation"],
        "angles": [
            "Problem → agentic solution",
            "Practical pilot path",
            "Human-in-the-loop trust",
        ],
        "cta_ideas": [
            "Browse the Matrixly agent catalog",
            "Start a free pilot this week",
        ],
        "risks": ["Avoid unverified ROI claims"],
    }

#!/usr/bin/env python3
"""Smoke test ContentForge pipeline without API key."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import JobStatus
from src.orchestrator import ContentForge


def main() -> int:
    cfg = load_config()
    agent = ContentForge(cfg)
    job = agent.demo()
    assert job.id
    assert job.research.get("key_points") or job.research.get("summary")
    assert (job.edited or job.draft or {}).get("body_markdown")
    assert job.assets.get("linkedin")
    assert job.assets.get("newsletter")
    assert job.export_paths
    assert job.status in {JobStatus.pending_review, JobStatus.approved}
    ideas = agent.suggest_ideas("content for SMB shipping automation", count=3)
    assert ideas.get("ideas")
    print(
        "SMOKE OK",
        {
            "job": job.id,
            "status": job.status.value,
            "quality": job.quality_score,
            "exports": len(job.export_paths),
            "ideas": len(ideas["ideas"]),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

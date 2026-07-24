#!/usr/bin/env python3
"""Smoke test PipelineForge without API key."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import RunStatus
from src.orchestrator import PipelineForge


def main() -> int:
    cfg = load_config()
    agent = PipelineForge(cfg)

    run = agent.demo()
    assert run.id
    assert run.scores
    assert run.priority_list
    assert run.insights
    assert run.export_paths
    assert run.status in {RunStatus.pending_review, RunStatus.applied}

    # tiers present
    tiers = {s.tier for s in run.scores}
    assert tiers & {"hot", "warm", "cold"}

    if run.hitl_id:
        approved = agent.approve(run.hitl_id)
        assert approved
        assert approved.status == RunStatus.applied
        assert any(u.applied for u in approved.crm_updates) or not approved.crm_updates

    st = agent.status()
    assert st["runs"] >= 1

    print(
        "SMOKE OK",
        {
            "run": run.id,
            "status": run.status.value,
            "scores": len(run.scores),
            "priority": len(run.priority_list),
            "risks": len(run.risks),
            "crm_updates": len(run.crm_updates),
            "health": (run.insights or {}).get("health_score"),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

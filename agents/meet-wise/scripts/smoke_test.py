#!/usr/bin/env python3
"""Smoke test MeetWise without API key."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import MeetingStatus
from src.orchestrator import MeetWise


def main() -> int:
    cfg = load_config()
    agent = MeetWise(cfg)
    m = agent.demo()
    assert m.id
    assert m.summary
    assert m.decisions or m.discussion_points
    assert m.action_items
    assert m.recap_subject and m.recap_body
    assert m.crm_payload.get("tasks") or m.crm_payload.get("notes")
    assert m.export_paths
    assert m.status in {MeetingStatus.pending_review, MeetingStatus.applied}
    print(
        "SMOKE OK",
        {
            "meeting": m.id,
            "status": m.status.value,
            "actions": len(m.action_items),
            "follow_ups": len(m.follow_ups),
            "exports": len(m.export_paths),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Smoke test SocialForge without API key."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import CampaignStatus
from src.orchestrator import SocialForge


def main() -> int:
    cfg = load_config()
    agent = SocialForge(cfg)

    c = agent.demo()
    assert c.id
    assert c.posts
    assert c.schedule
    assert c.status in {CampaignStatus.pending_review, CampaignStatus.approved}
    assert c.export_paths

    mon = agent.monitor()
    assert mon.get("items")

    replies = agent.draft_replies()
    assert replies.get("items")

    ins = agent.insights()
    assert ins.highlights or ins.suggestions

    # Approve campaign HITL if pending
    if c.hitl_id:
        approved = agent.approve(c.hitl_id)
        assert approved
        pub = agent.publish(c.id, backend="local")
        assert pub
        assert any(p.status.value == "published" for p in pub.posts.values())

    st = agent.status()
    assert st["campaigns"] >= 1

    print(
        "SMOKE OK",
        {
            "campaign": c.id,
            "status": c.status.value,
            "platforms": list(c.posts.keys()),
            "slots": len(c.schedule),
            "inbox": len(mon.get("items") or []),
            "insights": ins.id,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

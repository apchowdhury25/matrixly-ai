#!/usr/bin/env python3
"""Smoke test SEOForge pipeline without API key."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import JobStatus, KeywordItem
from src.orchestrator import SEOForge


def main() -> int:
    cfg = load_config()
    agent = SEOForge(cfg)

    # Onboard
    agent.onboard(
        {
            "business_name": "Apex Comfort HVAC",
            "business_type": "Residential HVAC",
            "service_areas": ["Austin, TX", "Round Rock, TX"],
            "website": "https://example-apex-hvac.com",
            "gbp_status": "Active",
            "primary_goal": "near_me_leads",
        }
    )

    chat = agent.chat("Create a 30-day plan for AC repair leads in Austin")
    assert chat.get("reply")
    assert chat.get("session_id")

    plan = agent.create_plan(
        (ROOT / "samples" / "business_brief.txt").read_text(encoding="utf-8"),
        primary_goal="near_me_leads",
        service_areas=["Austin, TX"],
        business_type="Residential HVAC",
    )
    assert plan.id
    assert plan.plan.get("weeks")
    assert plan.research.get("keywords")

    job = agent.demo()
    assert job.id
    assert (job.draft or {}).get("body_markdown")
    assert (job.draft or {}).get("title")
    assert job.status in {JobStatus.pending_review, JobStatus.approved}
    assert job.export_paths
    assert job.roi_snapshot

    local = agent.local_package("HVAC in Austin — need GBP posts and review templates")
    assert local.local.get("gbp_profile_suggestions")

    audit = agent.audit_page(
        "# AC Repair\n\nWe fix AC units in town. Call us.\n",
        url_or_title="AC Repair",
        primary_keyword="AC repair Austin",
    )
    assert audit.audit.get("issues") is not None

    agent.keywords.upsert(
        [
            KeywordItem(keyword="AC repair Austin", intent="local", priority="high", city="Austin, TX", current_rank=18),
            KeywordItem(keyword="AC repair near me", intent="local", priority="high", city="Austin, TX", current_rank=12),
        ]
    )
    assert agent.keywords.summary()["total"] >= 2

    agent.roi.record(hours_saved=3, leads_attributed=1, revenue_usd=450, note="smoke")
    assert agent.roi.summary()["hours_saved"] >= 3

    brand = agent.brand.save_voice("# Voice\nFriendly local experts.\n", tone=["friendly"], avoid=["guarantees"])
    assert brand.get("ok")

    print(
        "SMOKE OK",
        {
            "plan": plan.id,
            "content": job.id,
            "status": job.status.value,
            "local": local.id,
            "audit_score": audit.audit.get("score"),
            "keywords": agent.keywords.summary(),
            "roi": agent.roi.summary(),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

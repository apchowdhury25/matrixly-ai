#!/usr/bin/env python3
"""Smoke test — seed, FAQ chat, escalation path. Exit 0 on success."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import ActionType
from src.orchestrator import SupportForge


def main() -> int:
    cfg = load_config()
    forge = SupportForge(cfg)
    stats = forge.seed_knowledge()
    assert stats["chunks"] > 0, "knowledge index empty"

    pricing = forge.process("What are your pricing plans?", channel="chat")
    assert pricing.answer, "empty pricing answer"
    assert pricing.confidence > 0, "zero confidence on pricing"
    assert pricing.topic.value in {"pricing", "other"}

    hours = forge.process("What are your business hours?", channel="chat")
    assert hours.answer
    assert hours.topic.value in {"hours", "other"}

    bad = forge.process(
        "I will file a lawsuit with my attorney about chargeback fraud!",
        channel="chat",
    )
    assert bad.action == ActionType.escalate or bad.requires_human
    assert bad.ticket_id

    st = forge.status()
    assert st["kb"]["documents"] > 0
    print("SMOKE OK", {
        "chunks": stats["chunks"],
        "pricing_conf": pricing.confidence,
        "hours_action": hours.action.value,
        "escalate_action": bad.action.value,
        "ticket": bad.ticket_id,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

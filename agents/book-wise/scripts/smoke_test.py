#!/usr/bin/env python3
"""Smoke test BookWise availability + book + cancel."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import Intent
from src.orchestrator import BookWise


def main() -> int:
    cfg = load_config()
    agent = BookWise(cfg)

    slots = agent.calendar.propose_slots(service_id="consult")
    assert slots, "expected availability slots"
    print("slots", len(slots), slots[0].label)

    sid = None
    s1 = agent.process(
        "What times are available this week for a consultation?",
        channel="chat",
        session_id=sid,
    )
    sid = s1.session_id
    assert s1.intent in {Intent.availability, Intent.book}
    assert s1.proposals or s1.reply

    s2 = agent.process(
        "Book the first available. My name is Alex Rivera and email is alex@acme.com",
        channel="chat",
        session_id=sid,
    )
    assert s2.booking is not None, s2.reply
    assert s2.booking.customer.email == "alex@acme.com"
    bid = s2.booking.id

    upcoming = agent.bookings.list(upcoming_only=True)
    assert any(b.id == bid for b in upcoming)

    s3 = agent.process(
        f"Please cancel {bid}",
        channel="chat",
        session_id=sid,
        booking_id=bid,
    )
    assert "cancel" in s3.reply.lower() or s3.intent == Intent.cancel

    print("SMOKE OK", {"booking": bid, "slots": len(slots)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

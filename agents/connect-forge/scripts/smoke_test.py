#!/usr/bin/env python3
"""Smoke test ConnectForge without live Twilio credentials."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import MessageStatus
from src.orchestrator import ConnectForge


def main() -> int:
    cfg = load_config()
    # Force safe demo defaults
    cfg.setdefault("twilio", {})["test_mode"] = True
    cfg["twilio"]["verified_numbers"] = ["+17135550123"]
    cfg.setdefault("hitl", {})["auto_approve"] = True  # exercise send path in mock

    agent = ConnectForge(cfg)
    st = agent.status()
    assert st["service"] == "connect-forge"
    assert st["connection"]["status"] in {"mock", "trial", "live", "disconnected"}

    demo = agent.demo()
    assert demo.get("ok")
    assert demo.get("conversation")
    assert demo.get("inbound_flow", {}).get("ok")

    msgs = agent.store.list_messages(limit=20)
    assert len(msgs) >= 2
    inbound = [m for m in msgs if m.direction.value == "inbound"]
    outbound = [m for m in msgs if m.direction.value == "outbound"]
    assert inbound and outbound

    # HITL path
    cfg["hitl"]["auto_approve"] = False
    cfg["hitl"]["require_approval_outbound"] = True
    agent2 = ConnectForge(cfg)
    pending = agent2.send_sms("+17135550123", "HITL smoke message")
    assert pending.get("pending_approval") is True
    hitl_id = pending.get("hitl_id")
    assert hitl_id
    approved = agent2.approve_hitl(hitl_id)
    assert approved.get("ok")

    # Test mode block
    blocked = agent2.send_sms("+19995550111", "should block", skip_hitl=True)
    assert blocked.get("ok") is False

    call = agent2.start_call("+17135550123")
    assert call.get("call")

    print(
        "SMOKE OK",
        {
            "status": st["connection"]["status"],
            "messages": len(msgs),
            "demo_ok": demo.get("ok"),
            "hitl": hitl_id,
            "call": call.get("call", {}).get("id"),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

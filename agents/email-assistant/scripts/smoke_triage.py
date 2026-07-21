#!/usr/bin/env python3
"""Smoke test: triage recent (including read) messages."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import EmailAssistant
from src.config import load_config
from src.triage import triage_report


def main() -> int:
    cfg = load_config()
    cfg.setdefault("triage", {})["unread_only"] = False
    agent = EmailAssistant(cfg)
    profile = agent.connect()
    print(f"Connected: {profile.get('emailAddress')} ({profile.get('messagesTotal')} in inbox)")
    items = agent.triage(apply_labels=False, max_results=15, use_llm=False)
    print(triage_report(items))
    print("--- top ---")
    for i in items[:12]:
        m = i.message
        subj = (m.get("subject") or "")[:70]
        frm = (m.get("from_email") or "")[:40]
        print(f"{i.category:12} {i.score:0.2f} | {frm} | {subj}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

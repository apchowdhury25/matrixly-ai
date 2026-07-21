#!/usr/bin/env python3
"""Hermes cron / standalone: build daily email brief and email it to yourself."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import EmailAssistant  # noqa: E402


def main() -> int:
    deliver = "--no-send" not in sys.argv
    agent = EmailAssistant()
    agent.connect()
    result = agent.daily_summary(deliver=deliver, apply_labels=True, use_llm=True)
    print(result.get("summary") or "")
    if result.get("markdown_path"):
        print(f"\n---\nSaved: {result['markdown_path']}")
    if result.get("sent_message_id"):
        print(f"Delivered to: {result.get('delivered_to')} (id={result['sent_message_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

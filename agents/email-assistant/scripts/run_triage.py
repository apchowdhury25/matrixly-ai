#!/usr/bin/env python3
"""Hermes cron / standalone: triage inbox and print markdown report."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import EmailAssistant  # noqa: E402


def main() -> int:
    agent = EmailAssistant()
    agent.connect()
    print(agent.triage_text(apply_labels=True, use_llm=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Smoke test ETF Analyzer (uses live Yahoo if available, else fallback)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.orchestrator import ETFAnalyzer


def main() -> int:
    cfg = load_config()
    agent = ETFAnalyzer(cfg)

    # Default QQQI
    r1 = agent.analyze("")
    assert r1.ticker == "QQQI"
    assert r1.is_default_sample
    assert r1.markdown
    assert "ETF Portfolio Analyzer" in r1.markdown
    assert r1.snapshot.data_quality in {"live", "partial", "fallback_sample", "delayed"}

    # Explicit ticker
    r2 = agent.analyze("SPY")
    assert r2.ticker == "SPY"
    assert not r2.is_default_sample

    # Chat default
    chat = agent.chat("hello")
    assert chat.session_id
    assert "QQQI" in chat.reply

    # Chat ticker
    chat2 = agent.chat("analyze JEPI", session_id=chat.session_id)
    assert "JEPI" in chat2.reply.upper() or (chat2.report and chat2.report.ticker == "JEPI")

    # Notion local save
    result = agent.notion.save(r1)
    assert result.get("ok") is True or result.get("local_path")

    st = agent.status()
    assert st["reports"] >= 2

    print(
        "SMOKE OK",
        {
            "default": r1.ticker,
            "quality": r1.snapshot.data_quality,
            "spy_quality": r2.snapshot.data_quality,
            "price": r1.snapshot.price,
            "reports": st["reports"],
            "notion": result.get("backend"),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

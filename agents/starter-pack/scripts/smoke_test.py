#!/usr/bin/env python3
"""Smoke test Starter Pack (works with local data fallback if agents offline)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.pack import StarterPack


def main() -> int:
    cfg = load_config()
    pack = StarterPack(cfg)

    ov = pack.overview()
    assert ov.pack
    assert len(ov.agents) == 3
    ids = {a.id for a in ov.agents}
    assert ids == {"supportforge", "bookwise", "invoiceforge"}

    # Toggle off/on
    pack.set_agent_enabled("supportforge", False)
    s = pack.settings.load()
    assert s.agents_enabled.get("supportforge") is False
    pack.set_agent_enabled("supportforge", True)

    pack.update_connections({"knowledge": {"kb_path": "knowledge/"}})
    assert "knowledge" in pack.settings.load().connections

    st = pack.status()
    assert st["service"] == "starter-pack"
    assert "analytics" in st

    print(
        "SMOKE OK",
        {
            "pack": ov.pack,
            "agents": len(ov.agents),
            "online": ov.analytics.get("agents_online"),
            "analytics": ov.analytics,
            "activity": len(ov.activity),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

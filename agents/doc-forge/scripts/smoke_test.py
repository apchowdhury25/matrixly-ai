#!/usr/bin/env python3
"""Smoke test DocForge without API key."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import DocStatus
from src.orchestrator import DocForge


def main() -> int:
    cfg = load_config()
    agent = DocForge(cfg)

    assert agent.templates.list(), "templates missing"

    doc = agent.demo()
    assert doc.id
    assert doc.body_markdown
    assert doc.export_paths
    assert any(str(p).endswith(".pdf") for p in doc.export_paths)
    assert any(str(p).endswith(".html") for p in doc.export_paths)
    assert doc.status in {DocStatus.pending_approval, DocStatus.approved}
    assert doc.pricing_totals.get("total") is not None

    if doc.hitl_id:
        approved = agent.approve(doc.hitl_id)
        assert approved
        assert approved.status == DocStatus.approved
        sent = agent.send(approved.id, recipients=["client@example.com"])
        assert sent
        assert sent.status == DocStatus.sent
        assert sent.send_status == "sent"

    st = agent.status()
    assert st["documents"] >= 1
    assert st["templates"] >= 1

    print(
        "SMOKE OK",
        {
            "document": doc.id,
            "status": doc.status.value,
            "type": doc.doc_type.value,
            "quality": doc.quality_score,
            "exports": len(doc.export_paths),
            "total": (doc.pricing_totals or {}).get("total"),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Smoke test InvoiceForge sample processing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.models import InvoiceStatus
from src.orchestrator import InvoiceForge


def main() -> int:
    cfg = load_config()
    agent = InvoiceForge(cfg)
    results = agent.demo()
    assert len(results) >= 2, "expected 2 sample invoices"

    acme = results[0].invoice
    assert acme.vendor_name and "Acme" in (acme.vendor_name or "")
    assert acme.invoice_number
    assert acme.total is not None and acme.total > 0
    assert acme.status in {
        InvoiceStatus.posted,
        InvoiceStatus.validated,
        InvoiceStatus.pending_hitl,
    }

    exc = results[1].invoice
    assert exc.exceptions or exc.status in {
        InvoiceStatus.exception,
        InvoiceStatus.pending_hitl,
    }

    report = agent.report()
    assert report["summary"]["total_invoices"] >= 2

    print(
        "SMOKE OK",
        {
            "acme_status": acme.status.value,
            "acme_total": acme.total,
            "exc_status": exc.status.value,
            "exceptions": exc.exceptions,
            "posted": report["summary"]["posted"],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

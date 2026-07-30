#!/usr/bin/env python3
"""Smoke test Invoice Processor without requiring an LLM API key."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.deps import InvoiceProcessorDeps
from src.models import InvoiceInput, ReviewAction, SourceType
from src.pipeline import process_invoice


async def _run() -> dict:
    deps = InvoiceProcessorDeps.create()
    samples = ROOT / "samples"

    # 1) Clean match → approve
    match_text = (samples / "invoice_acme_match.txt").read_text(encoding="utf-8")
    r1 = await process_invoice(
        deps,
        InvoiceInput(text=match_text, source_type=SourceType.text, filename="match.txt"),
        use_llm=False,
    )
    assert r1.invoice.invoice_number
    assert r1.invoice.po_number == "PO-10482"
    assert r1.matching.matched_po is not None
    assert r1.review.action == ReviewAction.approve, r1.review
    assert r1.requires_human is False

    # 2) Amount mismatch → needs review
    bad = (samples / "invoice_amount_mismatch.txt").read_text(encoding="utf-8")
    r2 = await process_invoice(
        deps,
        InvoiceInput(text=bad, source_type=SourceType.text),
        use_llm=False,
    )
    assert r2.matching.discrepancies, "expected amount discrepancy"
    assert r2.review.action in {ReviewAction.needs_review, ReviewAction.reject}
    assert r2.requires_human is True

    # 3) No PO → needs review
    nop = (samples / "invoice_no_po.txt").read_text(encoding="utf-8")
    r3 = await process_invoice(
        deps,
        InvoiceInput(text=nop, source_type=SourceType.text),
        use_llm=False,
    )
    assert r3.review.requires_human is True

    return {
        "match": {
            "id": r1.processing_id,
            "action": r1.review.action.value,
            "status": r1.matching.status.value,
        },
        "mismatch": {
            "id": r2.processing_id,
            "action": r2.review.action.value,
            "discrepancies": len(r2.matching.discrepancies),
        },
        "no_po": {
            "id": r3.processing_id,
            "action": r3.review.action.value,
        },
        "pos_seeded": len(deps.po_store.list_all()),
    }


def main() -> int:
    out = asyncio.run(_run())
    print("SMOKE OK", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
End-to-end usage example for Matrixly Invoice Processor.

Demonstrates:
  - Building InvoiceProcessorDeps (DI container)
  - Running the deterministic multi-agent pipeline
  - Interpreting InvoiceProcessingResult for HITL / payment prep

Usage:
  python scripts/run_example.py
  python scripts/run_example.py --llm   # uses XAI_API_KEY if set
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.deps import InvoiceProcessorDeps
from src.models import InvoiceInput, SourceType
from src.pipeline import process_invoice


async def main_async(use_llm: bool | None) -> None:
    # 1) Dependency injection — swap stubs for Gmail / QuickBooks later
    deps = InvoiceProcessorDeps.create()

    print("Model:", deps.model_name)
    print("LLM ready:", deps.model_available())
    print("POs loaded:", len(deps.po_store.list_all()))
    print()

    # 2) Load a sample invoice (PDF path also supported via pdf_path=)
    sample = ROOT / "samples" / "invoice_acme_match.txt"
    payload = InvoiceInput(
        text=sample.read_text(encoding="utf-8"),
        source_type=SourceType.text,
        filename=sample.name,
        metadata={"demo": True},
    )

    # 3) Orchestrated workflow: Extractor → Matcher → Reviewer
    result = await process_invoice(deps, payload, use_llm=use_llm)

    # 4) Consume structured result
    print("=== InvoiceProcessingResult ===")
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))
    print()
    print("Action:", result.review.action.value)
    print("HITL required:", result.requires_human)
    print("Trace:", " → ".join(result.agent_trace))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable Pydantic AI specialists when XAI_API_KEY is set",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Force rule-based path",
    )
    args = parser.parse_args()
    use_llm: bool | None
    if args.no_llm:
        use_llm = False
    elif args.llm:
        use_llm = True
    else:
        use_llm = None  # auto
    asyncio.run(main_async(use_llm))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

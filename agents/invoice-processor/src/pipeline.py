"""Deterministic async pipeline: Extract → Match → Review → Result.

This is the production workhorse. The Pydantic AI orchestrator agent can
wrap the same stages as tools for conversational control, but batch AP
ingestion should call `process_invoice` directly for predictable ordering
and simpler observability.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .agents.extractor import extract_invoice
from .agents.matcher import match_invoice
from .agents.reviewer import review_invoice
from .deps import InvoiceProcessorDeps
from .models import (
    InvoiceInput,
    InvoiceProcessingResult,
    ProcessingStatus,
    SourceType,
    utc_now,
)


async def process_invoice(
    deps: Optional[InvoiceProcessorDeps] = None,
    payload: Optional[InvoiceInput] = None,
    *,
    text: Optional[str] = None,
    pdf_path: Optional[str] = None,
    email_message_id: Optional[str] = None,
    use_llm: Optional[bool] = None,
) -> InvoiceProcessingResult:
    """
    End-to-end invoice processing.

    Parameters
    ----------
    deps : dependency container (created if omitted)
    payload : structured input (or pass text/pdf_path/email_message_id)
    use_llm : force LLM on/off for specialists; None = auto
    """
    deps = deps or InvoiceProcessorDeps.create()
    if payload is None:
        payload = InvoiceInput(
            text=text,
            pdf_path=pdf_path,
            email_message_id=email_message_id,
            source_type=(
                SourceType.pdf
                if pdf_path
                else SourceType.email
                if email_message_id
                else SourceType.text
            ),
        )

    trace: list[str] = []
    started = utc_now()

    try:
        trace.append("extract:start")
        invoice = await extract_invoice(deps, payload, use_llm=use_llm)
        trace.append(
            f"extract:done method={invoice.extraction_method} "
            f"conf={invoice.extraction_confidence:.2f}"
        )

        trace.append("match:start")
        matching = await match_invoice(deps, invoice, use_llm=use_llm)
        trace.append(
            f"match:done status={matching.status.value} "
            f"conf={matching.match_confidence:.2f} "
            f"discrepancies={len(matching.discrepancies)}"
        )

        trace.append("review:start")
        review = await review_invoice(deps, invoice, matching, use_llm=use_llm)
        trace.append(
            f"review:done action={review.action.value} "
            f"hitl={review.requires_human}"
        )

        status = ProcessingStatus.completed
        if review.requires_human or review.action.value == "needs_review":
            status = ProcessingStatus.pending_hitl
        if review.action.value == "reject":
            status = ProcessingStatus.completed  # terminal recommendation

        result = InvoiceProcessingResult(
            status=status,
            invoice=invoice,
            matching=matching,
            review=review,
            requires_human=review.requires_human,
            started_at=started,
            completed_at=utc_now(),
            agent_trace=trace,
            metadata={
                "model": deps.model_name,
                "llm_enabled": deps.model_available() if use_llm is None else bool(use_llm),
            },
        )

        # Persist result for audit / dashboard hooks
        out_dir = Path(deps.data_dir) / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{result.processing_id}.json"
        path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        result.metadata["result_path"] = str(path)

        # Prepare accounting artifact only when approve (or always as draft)
        try:
            prep = await deps.accounting.prepare_payment(result)
            result.metadata["accounting_prep"] = prep
            trace.append("accounting:prep_done")
        except Exception as e:
            trace.append(f"accounting:prep_failed:{e}")
            result.agent_trace = trace

        return result

    except Exception as e:
        # Structured failure envelope
        from .models import InvoiceData, MatchingResult, MatchStatus, ReviewAction, ReviewDecision

        empty_invoice = InvoiceData(
            vendor_name="",
            invoice_number="",
            total=0.0,
            extraction_confidence=0.0,
            warnings=[str(e)],
        )
        return InvoiceProcessingResult(
            status=ProcessingStatus.failed,
            invoice=empty_invoice,
            matching=MatchingResult(
                status=MatchStatus.unmatched,
                match_confidence=0.0,
                summary="Processing failed before match",
            ),
            review=ReviewDecision(
                action=ReviewAction.needs_review,
                reasoning=f"Pipeline error: {e}",
                confidence=0.0,
                requires_human=True,
                hitl_reasons=[str(e)],
                recommended_next_actions=["Retry processing", "Inspect source file"],
            ),
            requires_human=True,
            error=str(e),
            started_at=started,
            completed_at=utc_now(),
            agent_trace=trace + [f"error:{e}"],
        )


def process_invoice_sync(*args: Any, **kwargs: Any) -> InvoiceProcessingResult:
    """Sync wrapper for CLIs that are not async."""
    import asyncio

    return asyncio.run(process_invoice(*args, **kwargs))

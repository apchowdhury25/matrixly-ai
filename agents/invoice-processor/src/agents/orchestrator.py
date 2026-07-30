"""InvoiceOrchestrator — coordinates Extractor → Matcher → Reviewer.

Two execution modes
-------------------
1. **Deterministic pipeline** (`pipeline.process_invoice`) — preferred for
   production batch jobs: fixed order, strong typing, easy to audit.
2. **Agentic orchestrator** (this module) — Pydantic AI agent that calls
   specialist agents as tools. Useful for conversational AP desk UIs and
   ad-hoc “what if” questions.

Design decision: specialists remain independently runnable. The orchestrator
never re-implements extraction/matching logic; it only sequences and packages
InvoiceProcessingResult.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Optional

from ..models import (
    InvoiceData,
    InvoiceInput,
    InvoiceProcessingResult,
    MatchingResult,
    ProcessingStatus,
    ReviewDecision,
    SourceType,
    utc_now,
)
from ._model import llm_enabled, resolve_model, try_import_pydantic_ai
from .extractor import extract_invoice
from .matcher import match_invoice
from .reviewer import review_invoice

if TYPE_CHECKING:
    from ..deps import InvoiceProcessorDeps

ORCHESTRATOR_SYSTEM = """
You are InvoiceOrchestrator for Matrixly Invoice Processor.

Coordinate the AP workflow:
1) extract_invoice_tool → InvoiceData
2) match_invoice_tool → MatchingResult
3) review_invoice_tool → ReviewDecision
4) Return a complete InvoiceProcessingResult

Do not skip stages. Prefer tools over free-form invention.
If a stage fails, set status=failed and explain in error.
Surface requires_human from the reviewer.
""".strip()

_orchestrator_agent: Any = None


def get_orchestrator_agent(model: Optional[str] = None) -> Any:
    global _orchestrator_agent
    imported = try_import_pydantic_ai()
    if imported is None:
        raise RuntimeError("pydantic-ai is not installed. pip install pydantic-ai")

    Agent, RunContext, _ = imported
    if _orchestrator_agent is not None and model is None:
        return _orchestrator_agent

    from ..deps import InvoiceProcessorDeps

    agent = Agent(
        resolve_model(model or "xai:grok-4.5"),
        deps_type=InvoiceProcessorDeps,
        output_type=InvoiceProcessingResult,
        system_prompt=ORCHESTRATOR_SYSTEM,
        name="InvoiceOrchestrator",
    )

    # --- Specialist agents registered as tools ---

    @agent.tool
    async def extract_invoice_tool(
        ctx: RunContext[InvoiceProcessorDeps],
        text: str = "",
        pdf_path: str = "",
        email_message_id: str = "",
        filename: str = "",
    ) -> dict[str, Any]:
        """Run InvoiceExtractorAgent on text, PDF path, or email id."""
        payload = InvoiceInput(
            text=text or None,
            pdf_path=pdf_path or None,
            email_message_id=email_message_id or None,
            filename=filename or None,
            source_type=(
                SourceType.pdf
                if pdf_path
                else SourceType.email
                if email_message_id
                else SourceType.text
            ),
        )
        data = await extract_invoice(ctx.deps, payload)
        return data.model_dump(mode="json")

    @agent.tool
    async def match_invoice_tool(
        ctx: RunContext[InvoiceProcessorDeps], invoice_json: str
    ) -> dict[str, Any]:
        """Run InvoiceMatcherAgent against the PO store."""
        invoice = InvoiceData.model_validate_json(invoice_json)
        result = await match_invoice(ctx.deps, invoice)
        return result.model_dump(mode="json")

    @agent.tool
    async def review_invoice_tool(
        ctx: RunContext[InvoiceProcessorDeps],
        invoice_json: str,
        matching_json: str,
    ) -> dict[str, Any]:
        """Run InvoiceReviewerAgent for final Approve / Needs Review / Reject."""
        invoice = InvoiceData.model_validate_json(invoice_json)
        matching = MatchingResult.model_validate_json(matching_json)
        decision = await review_invoice(ctx.deps, invoice, matching)
        return decision.model_dump(mode="json")

    @agent.tool
    async def prepare_accounting_payload(
        ctx: RunContext[InvoiceProcessorDeps], result_json: str
    ) -> dict[str, Any]:
        """Optional: prepare payment/accounting artifact via connector stub."""
        result = InvoiceProcessingResult.model_validate_json(result_json)
        return await ctx.deps.accounting.prepare_payment(result)

    if model is None:
        _orchestrator_agent = agent
    return agent


async def run_orchestrator(
    deps: "InvoiceProcessorDeps",
    payload: InvoiceInput,
    *,
    use_llm_orchestrator: bool = False,
) -> InvoiceProcessingResult:
    """
    Run the full workflow.

    By default uses the deterministic pipeline (extract→match→review) which
    still uses specialist LLM agents when keys are present. Set
    use_llm_orchestrator=True to let the Pydantic AI orchestrator agent
    drive tool calls conversationally.
    """
    # Default path: explicit pipeline for reliability
    if not use_llm_orchestrator or not llm_enabled(deps):
        from ..pipeline import process_invoice

        return await process_invoice(deps, payload)

    agent = get_orchestrator_agent(deps.model_name)
    user = (
        "Process this invoice end-to-end using extract → match → review tools.\n"
        f"payload={json.dumps(payload.model_dump(), default=str)}"
    )
    try:
        result = await agent.run(user, deps=deps)
        out: InvoiceProcessingResult = result.output
        if out.completed_at is None:
            out.completed_at = utc_now()
        return out
    except Exception as e:
        # Fall back to deterministic pipeline on orchestrator failure
        from ..pipeline import process_invoice

        fallback = await process_invoice(deps, payload)
        fallback.agent_trace.append(f"orchestrator_llm_failed:{e}")
        return fallback

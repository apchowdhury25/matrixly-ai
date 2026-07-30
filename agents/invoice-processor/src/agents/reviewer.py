"""InvoiceReviewerAgent — match + policy → ReviewDecision (HITL-aware).

Makes the final Approve / Needs Review / Reject recommendation with
explicit reasoning and next actions for AP owners.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ..models import InvoiceData, MatchingResult, ReviewDecision
from ..tools.review_rules import decide_review
from ._model import llm_enabled, resolve_model, try_import_pydantic_ai

if TYPE_CHECKING:
    from ..deps import InvoiceProcessorDeps

REVIEWER_SYSTEM = """
You are InvoiceReviewerAgent for Matrixly Invoice Processor.

Decide Approve, Needs Review, or Reject for payment preparation.
Policies:
- Never approve when critical PO/amount/vendor issues remain unresolved.
- Force human-in-the-loop for high-value invoices and low confidence.
- Use the apply_review_policy tool for baseline decisioning; refine reasoning if needed.
- recommended_next_actions must be concrete for an AP owner (not engineers).
- requires_human=true whenever action is needs_review or reject (unless policy auto-approves clean matches).
""".strip()

_reviewer_agent: Any = None


def get_reviewer_agent(model: Optional[str] = None) -> Any:
    global _reviewer_agent
    imported = try_import_pydantic_ai()
    if imported is None:
        raise RuntimeError("pydantic-ai is not installed. pip install pydantic-ai")

    Agent, RunContext, _ = imported
    if _reviewer_agent is not None and model is None:
        return _reviewer_agent

    from ..deps import InvoiceProcessorDeps

    agent = Agent(
        resolve_model(model or "xai:grok-4.5"),
        deps_type=InvoiceProcessorDeps,
        output_type=ReviewDecision,
        system_prompt=REVIEWER_SYSTEM,
        name="InvoiceReviewerAgent",
    )

    @agent.tool
    async def apply_review_policy(
        ctx: RunContext[InvoiceProcessorDeps],
        invoice_json: str,
        matching_json: str,
    ) -> dict[str, Any]:
        """Apply Matrixly AP review policy; returns ReviewDecision dict."""
        invoice = InvoiceData.model_validate_json(invoice_json)
        matching = MatchingResult.model_validate_json(matching_json)
        decision = decide_review(invoice, matching, ctx.deps.rules)
        return decision.model_dump(mode="json")

    @agent.tool
    async def get_thresholds(ctx: RunContext[InvoiceProcessorDeps]) -> dict[str, Any]:
        """Return current amount/confidence thresholds for transparency."""
        r = ctx.deps.rules
        return {
            "amount_review_threshold": r.amount_review_threshold,
            "min_extract_confidence": r.min_extract_confidence,
            "min_match_confidence": r.min_match_confidence,
            "auto_approve_when_clean": r.auto_approve_when_clean,
            "require_hitl_on_high_severity": r.require_hitl_on_high_severity,
        }

    if model is None:
        _reviewer_agent = agent
    return agent


async def review_invoice(
    deps: "InvoiceProcessorDeps",
    invoice: InvoiceData,
    matching: MatchingResult,
    *,
    use_llm: Optional[bool] = None,
) -> ReviewDecision:
    baseline = decide_review(invoice, matching, deps.rules)
    want_llm = llm_enabled(deps) if use_llm is None else use_llm
    if not want_llm:
        return baseline

    try:
        agent = get_reviewer_agent(deps.model_name)
        prompt = (
            "Produce the final review decision. Call apply_review_policy first.\n\n"
            f"Invoice:\n{invoice.model_dump_json()}\n\n"
            f"Matching:\n{matching.model_dump_json()}\n\n"
            f"Policy baseline:\n{baseline.model_dump_json()}"
        )
        result = await agent.run(prompt, deps=deps)
        out: ReviewDecision = result.output
        # Safety: never silently approve if baseline demanded HITL
        if baseline.requires_human and out.action.value == "approve":
            return baseline
        return out
    except Exception:
        return baseline

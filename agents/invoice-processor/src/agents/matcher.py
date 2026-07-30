"""InvoiceMatcherAgent — InvoiceData + PO store → MatchingResult.

Uses tools for PO lookup and deterministic discrepancy rules so matching
stays auditable. LLM can explain / re-rank candidates; core math is rule-based.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ..models import InvoiceData, MatchingResult
from ..tools.matching_rules import match_invoice_to_po
from ._model import llm_enabled, resolve_model, try_import_pydantic_ai

if TYPE_CHECKING:
    from ..deps import InvoiceProcessorDeps

MATCHER_SYSTEM = """
You are InvoiceMatcherAgent for Matrixly Invoice Processor.

Match the structured invoice against purchase orders using the provided tools.
You MUST:
1. Look up the PO by number when present.
2. If missing, search candidate POs by vendor.
3. Run discrepancy rules via the match_against_po tool.
4. Return the MatchingResult from tools — do not invent PO totals.

Be conservative: when unsure, lower match_confidence and leave discrepancies.
""".strip()

_matcher_agent: Any = None


def get_matcher_agent(model: Optional[str] = None) -> Any:
    global _matcher_agent
    imported = try_import_pydantic_ai()
    if imported is None:
        raise RuntimeError("pydantic-ai is not installed. pip install pydantic-ai")

    Agent, RunContext, _ = imported
    if _matcher_agent is not None and model is None:
        return _matcher_agent

    from ..deps import InvoiceProcessorDeps

    agent = Agent(
        resolve_model(model or "xai:grok-4.5"),
        deps_type=InvoiceProcessorDeps,
        output_type=MatchingResult,
        system_prompt=MATCHER_SYSTEM,
        name="InvoiceMatcherAgent",
    )

    @agent.tool
    async def lookup_po(
        ctx: RunContext[InvoiceProcessorDeps], po_number: str
    ) -> dict[str, Any]:
        """Fetch a purchase order by number from the PO store."""
        po = ctx.deps.po_store.get(po_number)
        if not po:
            return {"found": False, "po_number": po_number}
        return {"found": True, "po": po.model_dump()}

    @agent.tool
    async def find_pos_by_vendor(
        ctx: RunContext[InvoiceProcessorDeps], vendor_name: str
    ) -> list[dict[str, Any]]:
        """Fuzzy-find open POs for a vendor name."""
        pos = ctx.deps.po_store.find_by_vendor(vendor_name, limit=5)
        return [p.model_dump() for p in pos]

    @agent.tool
    async def match_against_po(
        ctx: RunContext[InvoiceProcessorDeps],
        invoice_json: str,
        po_number: str,
    ) -> dict[str, Any]:
        """
        Run deterministic discrepancy rules between invoice JSON and a PO number.
        Returns a MatchingResult dict.
        """
        invoice = InvoiceData.model_validate_json(invoice_json)
        po = ctx.deps.po_store.get(po_number)
        result = match_invoice_to_po(
            invoice,
            po,
            ctx.deps.rules,
            candidate_pos=[po_number] if po_number else [],
        )
        return result.model_dump(mode="json")

    if model is None:
        _matcher_agent = agent
    return agent


async def match_invoice(
    deps: "InvoiceProcessorDeps",
    invoice: InvoiceData,
    *,
    use_llm: Optional[bool] = None,
) -> MatchingResult:
    """Match invoice to PO — tools-first deterministic core, optional LLM wrap."""
    # Always compute a deterministic baseline first (production safety)
    po = deps.po_store.get(invoice.po_number or "")
    candidates = [invoice.po_number] if invoice.po_number else []
    if not po and invoice.vendor_name:
        found = deps.po_store.find_by_vendor(invoice.vendor_name, limit=3)
        candidates = [p.po_number for p in found]
        if found and not invoice.po_number:
            po = found[0]

    baseline = match_invoice_to_po(
        invoice, po, deps.rules, candidate_pos=[c for c in candidates if c]
    )

    want_llm = llm_enabled(deps) if use_llm is None else use_llm
    if not want_llm:
        return baseline

    try:
        agent = get_matcher_agent(deps.model_name)
        prompt = (
            "Match this invoice using tools. Prefer tool results over free reasoning.\n\n"
            f"Invoice JSON:\n{invoice.model_dump_json()}\n\n"
            f"Baseline match (rules):\n{baseline.model_dump_json()}"
        )
        result = await agent.run(prompt, deps=deps)
        out: MatchingResult = result.output
        # Prefer rule discrepancies if LLM emptied them
        if not out.discrepancies and baseline.discrepancies:
            out.discrepancies = baseline.discrepancies
        if out.matched_po is None and baseline.matched_po is not None:
            out.matched_po = baseline.matched_po
        return out
    except Exception:
        return baseline

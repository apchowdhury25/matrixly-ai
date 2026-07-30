"""InvoiceExtractorAgent — PDF/email/text → InvoiceData.

Responsibility
--------------
Turn messy invoice sources into a clean InvoiceData model. Uses tools for
PDF text extraction and email payload loading. When no LLM key is present,
falls back to deterministic rule extraction so demos and CI still work.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ..models import InvoiceData, InvoiceInput, SourceType
from ..tools.rule_extract import extract_invoice_rules
from ._model import llm_enabled, resolve_model, try_import_pydantic_ai

if TYPE_CHECKING:
    from ..deps import InvoiceProcessorDeps

EXTRACTOR_SYSTEM = """
You are InvoiceExtractorAgent for Matrixly Invoice Processor (US SMB AP).

Extract structured invoice data from the provided text (from PDF or email).
Rules:
- Never invent vendor names, amounts, PO numbers, or line items not supported by the text.
- Prefer ISO dates (YYYY-MM-DD) when possible.
- Populate line_items when line-level detail is present.
- Set extraction_confidence between 0 and 1 based on completeness and clarity.
- Put uncertainty notes in warnings.
- source_type and source_ref will be set by the system if missing.

Return only fields on InvoiceData. Be precise with totals and currency.
""".strip()

_extractor_agent: Any = None


def get_extractor_agent(model: Optional[str] = None) -> Any:
    """Lazily construct the Pydantic AI extractor agent."""
    global _extractor_agent
    imported = try_import_pydantic_ai()
    if imported is None:
        raise RuntimeError("pydantic-ai is not installed. pip install pydantic-ai")

    Agent, RunContext, _ = imported
    if _extractor_agent is not None and model is None:
        return _extractor_agent

    from ..deps import InvoiceProcessorDeps

    agent = Agent(
        resolve_model(model or "xai:grok-4.5"),
        deps_type=InvoiceProcessorDeps,
        output_type=InvoiceData,
        system_prompt=EXTRACTOR_SYSTEM,
        name="InvoiceExtractorAgent",
    )

    @agent.tool
    async def read_pdf_text(ctx: RunContext[InvoiceProcessorDeps], path: str) -> str:
        """Extract plain text from a PDF (or text sample) path."""
        return await ctx.deps.pdf.extract_text(path)

    @agent.tool
    async def read_email_payload(
        ctx: RunContext[InvoiceProcessorDeps], message_id: str
    ) -> str:
        """Load invoice-relevant text from an email message id (Gmail later)."""
        return await ctx.deps.email.extract_invoice_payload(message_id)

    if model is None:
        _extractor_agent = agent
    return agent


async def _load_source_text(
    deps: "InvoiceProcessorDeps", payload: InvoiceInput
) -> tuple[str, SourceType, Optional[str]]:
    if payload.text and payload.text.strip():
        return payload.text.strip(), payload.source_type or SourceType.text, payload.filename

    if payload.pdf_path:
        text = await deps.pdf.extract_text(payload.pdf_path)
        return text, SourceType.pdf, payload.pdf_path

    if payload.email_raw and payload.email_raw.strip():
        return payload.email_raw.strip(), SourceType.email, payload.email_message_id

    if payload.email_message_id:
        text = await deps.email.extract_invoice_payload(payload.email_message_id)
        return text, SourceType.email, payload.email_message_id

    raise ValueError("InvoiceInput requires text, pdf_path, email_raw, or email_message_id")


async def extract_invoice(
    deps: "InvoiceProcessorDeps",
    payload: InvoiceInput,
    *,
    use_llm: Optional[bool] = None,
) -> InvoiceData:
    """
    Run extraction. Prefer LLM structured output when available; always
    capable of rule-based fallback for CI / offline demos.
    """
    text, source_type, source_ref = await _load_source_text(deps, payload)
    want_llm = llm_enabled(deps) if use_llm is None else use_llm

    if want_llm:
        try:
            agent = get_extractor_agent(deps.model_name)
            prompt = (
                f"Source type: {source_type.value}\n"
                f"Source ref: {source_ref or ''}\n"
                f"Filename: {payload.filename or ''}\n\n"
                f"Invoice content:\n{text[:40000]}"
            )
            result = await agent.run(prompt, deps=deps)
            data: InvoiceData = result.output
            data.source_type = source_type
            data.source_ref = source_ref or data.source_ref
            if not data.raw_text_excerpt:
                data.raw_text_excerpt = text[:2000]
            if data.extraction_method in {"unknown", ""}:
                data.extraction_method = "llm"
            return data
        except Exception as e:
            # Fall through to rules — production systems should still process
            rules = extract_invoice_rules(
                text,
                source_type=source_type,
                source_ref=source_ref,
                default_currency=deps.rules.default_currency,
            )
            rules.warnings.append(f"LLM extraction failed, used rules: {e}")
            rules.extraction_method = "hybrid"
            return rules

    return extract_invoice_rules(
        text,
        source_type=source_type,
        source_ref=source_ref,
        default_currency=deps.rules.default_currency,
    )

"""Drafter agent — generate document body from template + brief."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import Document, DocStatus
from ..services.templates import TemplateStore


def run_drafter(
    doc: Document,
    cfg: dict,
    brand: BrandMemory,
    templates: TemplateStore,
) -> tuple[Document, int, int]:
    tin = tout = 0
    doc.status = DocStatus.drafting
    totals = _pricing_totals(doc, cfg)
    doc.pricing_totals = totals
    validity = int((cfg.get("documents") or {}).get("default_validity_days") or 30)
    valid_through = (datetime.now(timezone.utc) + timedelta(days=validity)).date().isoformat()
    doc.valid_through = valid_through

    values = _template_values(doc, cfg, totals, valid_through)
    template_id = doc.template_id or doc.doc_type.value
    skeleton = templates.render(template_id, values)

    if llm.grok_available(cfg):
        try:
            system = prompt_text("drafter") + "\n\n# Brand\n" + brand.context()[:4000]
            user = (
                f"Doc type: {doc.doc_type.value}\n"
                f"Client: {doc.client.model_dump()}\n"
                f"Project: {doc.project.model_dump()}\n"
                f"Line items: {[li.model_dump() for li in doc.line_items]}\n"
                f"Totals: {totals}\n"
                f"Legal block:\n{doc.legal_block}\n\n"
                f"Template skeleton (fill completely):\n{skeleton}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict) and data.get("body_markdown"):
                doc.title = str(data.get("title") or doc.project.title or doc.title)
                doc.body_markdown = str(data["body_markdown"])
                doc.summary = str(data.get("summary") or "")
                doc.sections = [str(s) for s in (data.get("sections") or [])]
                doc.flags.extend([str(f) for f in (data.get("flags") or [])])
                return doc, tin, tout
        except Exception as e:
            doc.metadata["drafter_error"] = str(e)

    doc.title = doc.project.title or f"{doc.doc_type.value.title()} — {doc.client.company}"
    doc.body_markdown = skeleton
    doc.summary = doc.project.summary[:280] if doc.project.summary else doc.title
    doc.sections = _extract_headings(doc.body_markdown)
    return doc, tin, tout


def _pricing_totals(doc: Document, cfg: dict) -> dict[str, Any]:
    pricing = cfg.get("pricing") or {}
    max_disc = float(pricing.get("default_discount_max_pct") or 15)
    tax_rate = float(pricing.get("tax_rate_pct") or 0) / 100.0
    disc = float(doc.discount_pct or 0)
    if disc > max_disc:
        doc.flags.append(f"Discount {disc}% exceeds max {max_disc}% — needs human review")
    subtotal = sum(li.qty * li.unit_price for li in doc.line_items)
    discount_amt = round(subtotal * (disc / 100.0), 2)
    taxable = subtotal - discount_amt
    tax = round(taxable * tax_rate, 2)
    total = round(taxable + tax, 2)
    currency = pricing.get("currency") or doc.currency or "USD"
    doc.currency = currency
    return {
        "subtotal": subtotal,
        "discount_pct": disc,
        "discount": discount_amt,
        "tax": tax,
        "total": total,
        "currency": currency,
        "payment_terms_days": int(pricing.get("payment_terms_days") or 30),
    }


def _pricing_table_md(doc: Document, totals: dict[str, Any]) -> str:
    lines = [
        "| SKU | Item | Qty | Unit | Unit price | Line total |",
        "|-----|------|----:|------|----------:|-----------:|",
    ]
    for li in doc.line_items:
        lt = li.qty * li.unit_price
        lines.append(
            f"| {li.sku or '—'} | {li.name} | {li.qty:g} | {li.unit or '—'} | "
            f"{totals['currency']} {li.unit_price:,.2f} | {totals['currency']} {lt:,.2f} |"
        )
    if not doc.line_items:
        lines.append("| — | Services as described | 1 | project | — | TBD |")
    lines.append("")
    lines.append(f"- **Subtotal:** {totals['currency']} {totals['subtotal']:,.2f}")
    if totals["discount"]:
        lines.append(
            f"- **Discount ({totals['discount_pct']}%):** −{totals['currency']} {totals['discount']:,.2f}"
        )
    if totals["tax"]:
        lines.append(f"- **Tax:** {totals['currency']} {totals['tax']:,.2f}")
    lines.append(f"- **Total:** {totals['currency']} {totals['total']:,.2f}")
    return "\n".join(lines)


def _template_values(
    doc: Document,
    cfg: dict,
    totals: dict[str, Any],
    valid_through: str,
) -> dict[str, str]:
    business = cfg.get("business") or {}
    brand = cfg.get("brand") or {}
    goals = "\n".join(f"- {g}" for g in doc.project.goals) or "- Align on pilot success metrics"
    constraints = "\n".join(f"- {c}" for c in doc.project.constraints) or "- Standard assumptions apply"
    scope = (
        doc.project.summary
        + ("\n\n**Goals**\n" + goals if doc.project.goals else "")
    )
    deliverables = goals if doc.project.goals else "- Implementation plan\n- Configuration & training\n- Weekly pilot review"
    return {
        "title": doc.project.title or f"{doc.doc_type.value.title()} for {doc.client.company}",
        "client_name": doc.client.company or doc.client.name or "Client",
        "business_name": str(business.get("name") or "Provider"),
        "date": datetime.now(timezone.utc).date().isoformat(),
        "valid_through": valid_through,
        "doc_id": doc.id,
        "summary": doc.project.summary or "Professional engagement summary.",
        "project_summary": doc.project.summary or "",
        "scope": scope,
        "deliverables": deliverables,
        "pricing_table": _pricing_table_md(doc, totals),
        "payment_terms_days": str(totals.get("payment_terms_days") or 30),
        "currency": str(totals.get("currency") or "USD"),
        "subtotal": f"{totals['currency']} {totals['subtotal']:,.2f}",
        "discount": f"{totals['currency']} {totals['discount']:,.2f}",
        "tax": f"{totals['currency']} {totals['tax']:,.2f}",
        "total": f"{totals['currency']} {totals['total']:,.2f}",
        "timeline": doc.project.timeline or "To be confirmed at kickoff",
        "assumptions": constraints,
        "legal_block": doc.legal_block or "",
        "footer": str(brand.get("footer_line") or "Confidential"),
    }


def _extract_headings(md: str) -> list[str]:
    out = []
    for line in md.splitlines():
        if line.startswith("## "):
            out.append(line[3:].strip())
    return out

"""Legal language assembler."""

from __future__ import annotations

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import Document


def run_legal(doc: Document, cfg: dict, brand: BrandMemory) -> tuple[Document, int, int]:
    tin = tout = 0
    legal_cfg = cfg.get("legal") or {}
    business = cfg.get("business") or {}

    if llm.grok_available(cfg):
        try:
            system = prompt_text("legal") + "\n\n# Brand context\n" + brand.context()[:3000]
            user = (
                f"Doc type: {doc.doc_type.value}\n"
                f"Governing law: {legal_cfg.get('governing_law')}\n"
                f"Entity: {business.get('legal_entity') or business.get('name')}\n"
                f"Include liability cap: {legal_cfg.get('include_liability_cap')}\n"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict) and data.get("legal_markdown"):
                doc.legal_block = str(data["legal_markdown"])
                if data.get("requires_counsel_review"):
                    doc.flags.append("Legal counsel review recommended")
                return doc, tin, tout
        except Exception as e:
            doc.metadata["legal_error"] = str(e)

    doc.legal_block = _rule_legal(doc, cfg, brand)
    return doc, tin, tout


def _rule_legal(doc: Document, cfg: dict, brand: BrandMemory) -> str:
    legal = cfg.get("legal") or {}
    business = cfg.get("business") or {}
    entity = business.get("legal_entity") or business.get("name") or "Provider"
    law = legal.get("governing_law") or "the applicable laws of the Provider's jurisdiction"
    cap_months = int(legal.get("liability_cap_months") or 12)
    payment = int((cfg.get("pricing") or {}).get("payment_terms_days") or 30)

    custom = ""
    for c in brand.clauses()[-3:]:
        custom += f"\n### {c.get('name')}\n{c.get('body')}\n"

    conf = ""
    if legal.get("confidentiality", True):
        conf = (
            "\n### Confidentiality\n"
            "Each party shall keep confidential the non-public information of the other party "
            "and use it only to perform under this document, except as required by law.\n"
        )

    liability = ""
    if legal.get("include_liability_cap", True):
        liability = (
            f"\n### Limitation of liability\n"
            f"Except for willful misconduct or breach of confidentiality, each party's aggregate liability "
            f"arising out of this document shall not exceed fees paid in the preceding {cap_months} months.\n"
        )

    return f"""## Terms

### Parties & authority
This document is issued by **{entity}**. The recipient confirms they have authority to evaluate and accept these terms.

### Fees & payment
Fees are as stated in the Investment / Fees section. Invoices are due within **{payment}** days of issue unless otherwise agreed in writing.

### Governing law
This document is governed by the laws of **{law}**, without regard to conflict-of-law principles.
{conf}{liability}
### Human-in-the-loop agents
Where AI agents are included, customer-facing or financial actions may require human approval per Provider policy.
{custom}
*This language is a standard template for SMB commercial documents and is not legal advice.*
"""

"""Brand & compliance checker."""

from __future__ import annotations

import re

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import Document, DocStatus


def run_brand_check(doc: Document, cfg: dict, brand: BrandMemory) -> tuple[Document, int, int]:
    tin = tout = 0
    doc.status = DocStatus.brand_review

    if llm.grok_available(cfg):
        try:
            system = prompt_text("brand_check") + "\n\n# Guidelines\n" + brand.context()[:3500]
            user = (
                f"Doc type: {doc.doc_type.value}\n"
                f"Flags so far: {doc.flags}\n"
                f"Totals: {doc.pricing_totals}\n\n"
                f"Draft:\n{doc.body_markdown[:12000]}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                doc.quality_score = float(data.get("quality_score") or 0)
                for issue in data.get("issues") or []:
                    msg = issue.get("message") if isinstance(issue, dict) else str(issue)
                    if msg:
                        doc.flags.append(str(msg))
                edits = data.get("edits") or {}
                if isinstance(edits, dict) and edits.get("body_markdown"):
                    doc.body_markdown = str(edits["body_markdown"])
                    doc.version += 1
                return doc, tin, tout
        except Exception as e:
            doc.metadata["brand_check_error"] = str(e)

    score, issues = _rule_check(doc, cfg)
    doc.quality_score = score
    doc.flags.extend(issues)
    # de-dupe flags
    seen: set[str] = set()
    uniq = []
    for f in doc.flags:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    doc.flags = uniq
    return doc, tin, tout


def _rule_check(doc: Document, cfg: dict) -> tuple[float, list[str]]:
    issues: list[str] = []
    score = 80.0
    body = doc.body_markdown or ""
    if re.search(r"\{\{[a-zA-Z0-9_]+\}\}", body):
        issues.append("Unresolved template placeholders remain")
        score -= 20
    if len(body) < 400:
        issues.append("Draft appears too short for a professional document")
        score -= 10
    if "Terms" not in body and not doc.legal_block:
        issues.append("Missing legal/terms section")
        score -= 15
    pricing = cfg.get("pricing") or {}
    max_disc = float(pricing.get("default_discount_max_pct") or 15)
    if float(doc.discount_pct or 0) > max_disc:
        issues.append(f"Discount exceeds policy max ({max_disc}%)")
        score -= 10
    if doc.doc_type.value in {"proposal", "quote", "contract"} and not doc.line_items:
        issues.append("No line items — pricing may be incomplete")
        score -= 8
    if not doc.client.company and not doc.client.name:
        issues.append("Client name missing")
        score -= 10
    score = max(0.0, min(100.0, score))
    return score, issues

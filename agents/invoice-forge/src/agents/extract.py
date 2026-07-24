"""Extract Agent — OCR/vision + rule-based invoice parsing."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import Invoice, LineItem, PipelineState


def run_extract(state: PipelineState, cfg: dict, invoice: Invoice) -> tuple[PipelineState, Invoice]:
    text = state.text or invoice.raw_text or ""
    image_path = state.image_path
    is_image = bool(
        image_path
        and Path(image_path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    )

    if llm.grok_available(cfg):
        try:
            system = prompt_text("extract") or "Extract invoice JSON from document."
            user = f"Filename: {state.filename or invoice.source_file or 'unknown'}\n\nDocument text:\n{text[:8000]}"
            if is_image:
                content, tin, tout = llm.vision_chat(
                    cfg, system, user, image_path=image_path
                )
                invoice.extraction_method = "vision"
            else:
                content, tin, tout = llm.chat(cfg, system, user)
                invoice.extraction_method = "llm_text"
            state.usage_tokens_in += tin
            state.usage_tokens_out += tout
            data = llm.extract_json(content)
            invoice = _apply_extracted(invoice, data)
            invoice.raw_text = text
            invoice.status = invoice.status  # keep
            from ..models import InvoiceStatus

            invoice.status = InvoiceStatus.extracted
            state.add_audit(
                "extract_llm",
                method=invoice.extraction_method,
                confidence=invoice.confidence,
            )
            state.invoice = invoice
            return state, invoice
        except Exception as e:
            state.add_audit("extract_llm_fallback", error=str(e))

    data = _rule_extract(text)
    invoice = _apply_extracted(invoice, data)
    invoice.raw_text = text
    invoice.extraction_method = "rules"
    from ..models import InvoiceStatus

    invoice.status = InvoiceStatus.extracted
    state.add_audit("extract_rules", confidence=invoice.confidence)
    state.invoice = invoice
    return state, invoice


def _apply_extracted(invoice: Invoice, data: dict[str, Any]) -> Invoice:
    for key in (
        "vendor_name",
        "vendor_email",
        "invoice_number",
        "po_number",
        "invoice_date",
        "due_date",
        "currency",
    ):
        if data.get(key) not in (None, ""):
            setattr(invoice, key, data[key])
    for key in ("subtotal", "tax", "total", "amount_due", "confidence"):
        if data.get(key) is not None:
            try:
                setattr(invoice, key, float(data[key]))
            except (TypeError, ValueError):
                pass
    if data.get("amount_due") is None and invoice.total is not None:
        invoice.amount_due = invoice.total
    items = data.get("line_items") or []
    if items:
        line_items: list[LineItem] = []
        for it in items:
            try:
                line_items.append(
                    LineItem(
                        description=str(it.get("description") or ""),
                        quantity=float(it.get("quantity") or 1),
                        unit_price=float(it.get("unit_price") or 0),
                        amount=float(it.get("amount") or 0),
                    )
                )
            except Exception:
                continue
        if line_items:
            invoice.line_items = line_items
    if data.get("notes"):
        invoice.notes = str(data["notes"])
    if invoice.confidence <= 0:
        invoice.confidence = float(data.get("confidence") or 0.5)
    return invoice


def _rule_extract(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "currency": "USD",
        "line_items": [],
        "confidence": 0.55,
    }
    if not text:
        data["confidence"] = 0.1
        return data

    # Vendor
    m = re.search(r"(?im)^(?:from|vendor|bill from|seller)\s*[:\-]\s*(.+)$", text)
    if m:
        data["vendor_name"] = m.group(1).strip()
    else:
        # First non-empty line after INVOICE header
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            if re.search(r"invoice", ln, re.I) and i + 1 < len(lines):
                nxt = lines[i + 1]
                if not re.search(r"invoice\s*#|number|date|due", nxt, re.I):
                    data["vendor_name"] = nxt.replace("From:", "").strip()
                    break

    m = re.search(r"(?i)\b([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b", text)
    if m:
        data["vendor_email"] = m.group(1)

    m = re.search(
        r"(?i)invoice\s*(?:number|#|no\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]+)",
        text,
    )
    if m:
        data["invoice_number"] = m.group(1).strip()
    else:
        m = re.search(r"(?i)\b(INV[-\s]?\d{3,}[\w-]*)\b", text)
        if m:
            data["invoice_number"] = re.sub(r"\s+", "", m.group(1))

    m = re.search(r"(?i)\bPO\s*(?:number|#|no\.?)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]+)", text)
    if m:
        data["po_number"] = m.group(1).strip()

    m = re.search(
        r"(?i)invoice\s*date\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        text,
    )
    if m:
        data["invoice_date"] = _norm_date(m.group(1))
    m = re.search(
        r"(?i)due\s*date\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        text,
    )
    if m:
        data["due_date"] = _norm_date(m.group(1))

    m = re.search(r"(?i)\bcurrency\s*[:\-]?\s*([A-Z]{3})\b", text)
    if m:
        data["currency"] = m.group(1).upper()

    m = re.search(r"(?i)subtotal\s*[:\-]?\s*\$?\s*([\d,]+\.?\d*)", text)
    if m:
        data["subtotal"] = _money(m.group(1))
    m = re.search(r"(?i)\btax(?:\s*\([^)]*\))?\s*[:\-]?\s*\$?\s*([\d,]+\.?\d*)", text)
    if m:
        data["tax"] = _money(m.group(1))
    m = re.search(
        r"(?i)(?:total\s*due|amount\s*due|grand\s*total|(?<![a-z])total(?![a-z]))\s*[:\-]?\s*\$?\s*([\d,]+\.?\d*)",
        text,
    )
    # Prefer explicit "Total Due" / last matching total line
    totals = re.findall(
        r"(?im)^(?:total\s*due|amount\s*due|grand\s*total|total)\s*[:\-]?\s*\$?\s*([\d,]+\.?\d*)\s*$",
        text,
    )
    if totals:
        data["total"] = _money(totals[-1])
        data["amount_due"] = data["total"]
    elif m:
        data["total"] = _money(m.group(1))
        data["amount_due"] = data["total"]

    # Line items: "desc Qty N @ $X  $Y"
    for lm in re.finditer(
        r"(?im)^\s*(?:\d+\.\s*)?(.+?)\s+Qty\s+([\d.]+)\s+@\s*\$?\s*([\d.]+)\s+\$?\s*([\d.]+)\s*$",
        text,
    ):
        data["line_items"].append(
            {
                "description": lm.group(1).strip(),
                "quantity": float(lm.group(2)),
                "unit_price": float(lm.group(3)),
                "amount": float(lm.group(4)),
            }
        )

    # Confidence from field coverage
    score = 0.2
    for k in ("vendor_name", "invoice_number", "total", "invoice_date", "due_date"):
        if data.get(k):
            score += 0.14
    if data.get("line_items"):
        score += 0.1
    data["confidence"] = min(0.92, score)
    return data


def _money(s: str) -> float:
    return float(s.replace(",", ""))


def _norm_date(s: str) -> str:
    s = s.strip()
    if re.match(r"\d{4}-\d{2}-\d{2}$", s):
        return s
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", s)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if c < 100:
            c += 2000
        # assume MM/DD/YYYY
        return f"{c:04d}-{a:02d}-{b:02d}"
    return s

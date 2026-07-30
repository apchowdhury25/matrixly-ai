"""Rule-based invoice extraction fallback (no LLM required)."""

from __future__ import annotations

import re
from typing import Optional

from ..models import InvoiceData, InvoiceLineItem, SourceType


def extract_invoice_rules(
    text: str,
    *,
    source_type: SourceType = SourceType.text,
    source_ref: Optional[str] = None,
    default_currency: str = "USD",
) -> InvoiceData:
    text = text or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    def find(patterns: list[str]) -> Optional[str]:
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                return m.group(1).strip()
        return None

    vendor = find(
        [
            r"Vendor[:\s]+(.+)",
            r"From[:\s]+(.+)",
            r"Bill\s+From[:\s]+(.+)",
            r"Supplier[:\s]+(.+)",
        ]
    )
    if not vendor and lines:
        # first non-label line often is vendor on simple invoices
        for ln in lines[:5]:
            if not re.search(r"invoice|date|total|po\b", ln, re.I):
                vendor = ln
                break

    invoice_number = find(
        [
            r"Invoice\s*(?:Number|No\.?|#)[:\s]+([A-Za-z0-9\-_/]+)",
            r"INV[:\s#-]+([A-Za-z0-9\-_/]+)",
        ]
    ) or "UNKNOWN"

    po_number = find(
        [
            r"P\.?O\.?\s*(?:Number|No\.?|#)?[:\s]+([A-Za-z0-9\-_/]+)",
            r"Purchase\s+Order[:\s]+([A-Za-z0-9\-_/]+)",
        ]
    )

    invoice_date = find(
        [
            r"Invoice\s*Date[:\s]+([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
            r"Date[:\s]+([0-9]{4}-[0-9]{2}-[0-9]{2})",
        ]
    )
    due_date = find(
        [
            r"Due\s*Date[:\s]+([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        ]
    )

    currency = find([r"Currency[:\s]+([A-Z]{3})"]) or default_currency

    def money(pat: str) -> Optional[float]:
        m = re.search(pat, text, re.I)
        if not m:
            return None
        raw = m.group(1).replace(",", "")
        try:
            return float(raw)
        except ValueError:
            return None

    total = money(r"(?:Invoice\s+)?Total[:\s]+\$?\s*([0-9,]+\.?[0-9]*)")
    subtotal = money(r"Subtotal[:\s]+\$?\s*([0-9,]+\.?[0-9]*)")
    tax = money(r"Tax[:\s]+\$?\s*([0-9,]+\.?[0-9]*)")
    if total is None:
        # last currency-looking number
        nums = re.findall(r"\$\s*([0-9,]+\.[0-9]{2})", text)
        if nums:
            try:
                total = float(nums[-1].replace(",", ""))
            except ValueError:
                total = 0.0
        else:
            total = 0.0

    # Simple line items: "desc | qty | price | amount" or tab-ish patterns
    line_items: list[InvoiceLineItem] = []
    for i, ln in enumerate(lines, start=1):
        m = re.match(
            r"^(?:(\d+)[\).\s]+)?(.+?)\s+[x×]\s*([0-9.]+)\s+@\s*\$?([0-9.]+)\s*=\s*\$?([0-9.]+)$",
            ln,
            re.I,
        )
        if m:
            line_items.append(
                InvoiceLineItem(
                    line_number=int(m.group(1) or len(line_items) + 1),
                    description=m.group(2).strip(),
                    quantity=float(m.group(3)),
                    unit_price=float(m.group(4)),
                    amount=float(m.group(5)),
                )
            )
            continue
        m2 = re.match(
            r"^(.+?)\s{2,}([0-9.]+)\s+\$?([0-9.]+)\s+\$?([0-9.]+)$",
            ln,
        )
        if m2 and not re.search(r"total|subtotal|tax", ln, re.I):
            line_items.append(
                InvoiceLineItem(
                    line_number=len(line_items) + 1,
                    description=m2.group(1).strip(),
                    quantity=float(m2.group(2)),
                    unit_price=float(m2.group(3)),
                    amount=float(m2.group(4)),
                )
            )

    warnings: list[str] = []
    conf = 0.55
    if invoice_number != "UNKNOWN":
        conf += 0.1
    if vendor:
        conf += 0.1
    if po_number:
        conf += 0.1
    if total:
        conf += 0.1
    if line_items:
        conf += 0.05
    conf = min(0.92, conf)
    if not vendor:
        warnings.append("Vendor name not confidently extracted")
    if not po_number:
        warnings.append("PO number not found in text")

    return InvoiceData(
        vendor_name=vendor or "Unknown Vendor",
        invoice_number=invoice_number,
        po_number=po_number,
        invoice_date=invoice_date,
        due_date=due_date,
        currency=currency or default_currency,
        subtotal=subtotal,
        tax=tax,
        total=float(total or 0),
        amount_due=float(total or 0),
        line_items=line_items,
        source_type=source_type,
        source_ref=source_ref,
        raw_text_excerpt=text[:2000],
        extraction_confidence=round(conf, 3),
        extraction_method="rules",
        warnings=warnings,
    )

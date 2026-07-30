"""Deterministic discrepancy rules for InvoiceMatcherAgent.

The matcher agent can call this logic via tools so LLM reasoning stays
grounded in explicit, auditable rules (amount tolerance, vendor fuzzy
match, qty checks). Easy to unit-test without an LLM.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from ..models import (
    Discrepancy,
    DiscrepancyType,
    InvoiceData,
    MatchStatus,
    MatchingResult,
    PurchaseOrder,
    Severity,
)

if TYPE_CHECKING:
    from ..deps import BusinessRules


def vendor_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower().strip(), (b or "").lower().strip()).ratio()


def match_invoice_to_po(
    invoice: InvoiceData,
    po: PurchaseOrder | None,
    rules: "BusinessRules",
    *,
    candidate_pos: list[str] | None = None,
) -> MatchingResult:
    rules_applied: list[str] = []
    discrepancies: list[Discrepancy] = []

    if not invoice.po_number and not po:
        rules_applied.append("missing_po_number")
        discrepancies.append(
            Discrepancy(
                type=DiscrepancyType.missing_po,
                severity=Severity.high,
                field="po_number",
                description="Invoice has no PO number and no PO could be inferred from vendor.",
                invoice_value=None,
                expected_value="Valid open PO",
            )
        )
        return MatchingResult(
            status=MatchStatus.no_po,
            matched_po=None,
            match_confidence=0.2,
            discrepancies=discrepancies,
            summary="No purchase order linked — route to review before payment.",
            candidate_po_numbers=candidate_pos or [],
            rules_applied=rules_applied,
        )

    if invoice.po_number and not po:
        rules_applied.append("po_not_found")
        discrepancies.append(
            Discrepancy(
                type=DiscrepancyType.po_number,
                severity=Severity.critical,
                field="po_number",
                description=f"PO {invoice.po_number} not found in store.",
                invoice_value=invoice.po_number,
                expected_value="Existing open PO",
            )
        )
        return MatchingResult(
            status=MatchStatus.unmatched,
            matched_po=None,
            match_confidence=0.15,
            discrepancies=discrepancies,
            summary=f"PO {invoice.po_number} not found.",
            candidate_po_numbers=candidate_pos or [],
            rules_applied=rules_applied,
        )

    assert po is not None
    confidence = 0.9

    # Vendor
    rules_applied.append("vendor_similarity")
    vscore = vendor_similarity(invoice.vendor_name, po.vendor_name)
    if vscore < rules.vendor_similarity_min:
        confidence -= 0.25
        severity = Severity.high if vscore < 0.5 else Severity.medium
        discrepancies.append(
            Discrepancy(
                type=DiscrepancyType.vendor,
                severity=severity,
                field="vendor_name",
                description=f"Vendor name similarity {vscore:.2f} below threshold {rules.vendor_similarity_min}.",
                invoice_value=invoice.vendor_name,
                expected_value=po.vendor_name,
                delta=round(1.0 - vscore, 3),
            )
        )

    # Currency
    rules_applied.append("currency_check")
    if (invoice.currency or "").upper() != (po.currency or "").upper():
        confidence -= 0.15
        discrepancies.append(
            Discrepancy(
                type=DiscrepancyType.currency,
                severity=Severity.high,
                field="currency",
                description="Invoice currency does not match PO currency.",
                invoice_value=invoice.currency,
                expected_value=po.currency,
            )
        )

    # Amount
    rules_applied.append("amount_tolerance")
    inv_total = float(invoice.total or 0)
    po_total = float(po.remaining_amount if po.remaining_amount is not None else po.total)
    abs_delta = abs(inv_total - po_total)
    pct = (abs_delta / po_total * 100.0) if po_total else 100.0
    tol_abs = rules.amount_tolerance_abs
    tol_pct = rules.amount_tolerance_pct
    within = abs_delta <= tol_abs or pct <= tol_pct
    if not within:
        confidence -= 0.3
        severity = Severity.critical if pct > 10 else Severity.high
        discrepancies.append(
            Discrepancy(
                type=DiscrepancyType.amount,
                severity=severity,
                field="total",
                description=(
                    f"Invoice total ${inv_total:.2f} vs PO remaining/total ${po_total:.2f} "
                    f"(Δ ${abs_delta:.2f}, {pct:.1f}%)."
                ),
                invoice_value=f"{inv_total:.2f}",
                expected_value=f"{po_total:.2f}",
                delta=round(abs_delta, 2),
            )
        )

    # Line quantity spot-check (best-effort by line number / first lines)
    rules_applied.append("line_qty_spot_check")
    po_by_line = {li.line_number: li for li in po.line_items}
    for ili in invoice.line_items[:10]:
        pli = po_by_line.get(ili.line_number)
        if not pli:
            continue
        if abs(float(ili.quantity) - float(pli.quantity)) > rules.qty_tolerance + 1e-9:
            confidence -= 0.1
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.quantity,
                    severity=Severity.medium,
                    field=f"line_items[{ili.line_number}].quantity",
                    description=f"Qty mismatch on line {ili.line_number}: invoice {ili.quantity} vs PO {pli.quantity}.",
                    invoice_value=str(ili.quantity),
                    expected_value=str(pli.quantity),
                    delta=abs(float(ili.quantity) - float(pli.quantity)),
                )
            )
        if abs(float(ili.unit_price) - float(pli.unit_price)) > max(0.01, rules.amount_tolerance_abs):
            confidence -= 0.08
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.unit_price,
                    severity=Severity.medium,
                    field=f"line_items[{ili.line_number}].unit_price",
                    description=(
                        f"Unit price mismatch on line {ili.line_number}: "
                        f"invoice {ili.unit_price} vs PO {pli.unit_price}."
                    ),
                    invoice_value=str(ili.unit_price),
                    expected_value=str(pli.unit_price),
                    delta=abs(float(ili.unit_price) - float(pli.unit_price)),
                )
            )

    confidence = max(0.0, min(1.0, confidence))
    high = any(d.severity in {Severity.high, Severity.critical} for d in discrepancies)
    if not discrepancies:
        status = MatchStatus.matched
        summary = f"Invoice matches PO {po.po_number} within tolerances."
    elif high:
        status = MatchStatus.partial if vscore >= rules.vendor_similarity_min else MatchStatus.unmatched
        summary = f"Material discrepancies vs PO {po.po_number} — review required."
    else:
        status = MatchStatus.partial
        summary = f"Partial match to PO {po.po_number} with minor discrepancies."

    return MatchingResult(
        status=status,
        matched_po=po,
        match_confidence=confidence,
        discrepancies=discrepancies,
        summary=summary,
        candidate_po_numbers=candidate_pos or [po.po_number],
        rules_applied=rules_applied,
    )

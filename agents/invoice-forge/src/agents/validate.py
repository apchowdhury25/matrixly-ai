"""Validate Agent — rules + exception flagging."""

from __future__ import annotations

from ..models import Invoice, InvoiceStatus, PipelineState
from ..services.store import InvoiceStore


def run_validate(
    state: PipelineState,
    cfg: dict,
    invoice: Invoice,
    store: InvoiceStore,
) -> tuple[PipelineState, Invoice]:
    rules = cfg.get("validation") or {}
    exc_cfg = cfg.get("exceptions") or {}
    errors: list[str] = []
    exceptions: list[str] = []

    if rules.get("require_vendor", True) and not invoice.vendor_name:
        errors.append("missing_vendor")
    if rules.get("require_invoice_number", True) and not invoice.invoice_number:
        errors.append("missing_invoice_number")
    if rules.get("require_total", True) and invoice.total is None:
        errors.append("missing_total")
    if rules.get("require_due_date") and not invoice.due_date:
        errors.append("missing_due_date")

    if invoice.total is not None:
        mx = float(rules.get("max_amount") or 500000)
        mn = float(rules.get("min_amount") or 0.01)
        if invoice.total > mx:
            errors.append("total_above_max")
        if invoice.total < mn:
            errors.append("total_below_min")

    thr = float(rules.get("confidence_threshold") or 0.75)
    if invoice.confidence < thr:
        exceptions.append(f"low_confidence:{invoice.confidence:.2f}")

    if rules.get("check_duplicates", True):
        dup = store.find_duplicate(invoice.vendor_name, invoice.invoice_number)
        if dup and dup.id != invoice.id:
            exceptions.append(f"duplicate_of:{dup.id}")

    # Line math check
    if invoice.line_items and invoice.subtotal is not None:
        s = sum(li.amount for li in invoice.line_items)
        if abs(s - invoice.subtotal) > 0.05 * max(1.0, abs(invoice.subtotal)):
            exceptions.append("line_items_subtotal_mismatch")

    high = float(exc_cfg.get("auto_flag_high_amount") or 25000)
    if invoice.total is not None and invoice.total >= high:
        exceptions.append(f"high_amount:{invoice.total}")

    if exc_cfg.get("missing_po_is_exception") and not invoice.po_number:
        exceptions.append("missing_po")

    raw = (invoice.raw_text or "").lower()
    for kw in exc_cfg.get("keywords") or []:
        if kw.lower() in raw:
            exceptions.append(f"keyword:{kw}")

    invoice.validation_errors = errors
    invoice.exceptions = list(dict.fromkeys(exceptions))  # unique preserve order

    hitl_mode = (cfg.get("hitl") or {}).get("mode") or "exceptions_only"
    auto = (cfg.get("hitl") or {}).get("auto_approve")

    if errors:
        invoice.status = InvoiceStatus.exception
        state.requires_human = True
        state.message = f"Validation failed: {', '.join(errors)}"
    elif exceptions and hitl_mode != "off" and not auto:
        invoice.status = InvoiceStatus.pending_hitl
        state.requires_human = True
        state.message = f"Flagged for review: {', '.join(exceptions)}"
    elif hitl_mode == "always" and not auto:
        invoice.status = InvoiceStatus.pending_hitl
        state.requires_human = True
        state.message = "HITL mode always — awaiting approval to post"
    else:
        invoice.status = InvoiceStatus.validated
        state.message = "Invoice validated"

    state.add_audit(
        "validated",
        errors=errors,
        exceptions=exceptions,
        status=invoice.status.value,
    )
    state.invoice = invoice
    return state, invoice

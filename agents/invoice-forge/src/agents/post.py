"""Post Agent — push to accounting backend + schedule AR reminders."""

from __future__ import annotations

from ..integrations.accounting import AccountingPoster
from ..models import Invoice, InvoiceStatus, PipelineState
from ..services.reminders import ReminderService


def run_post(
    state: PipelineState,
    invoice: Invoice,
    poster: AccountingPoster,
    reminders: ReminderService,
) -> tuple[PipelineState, Invoice]:
    if invoice.status not in {InvoiceStatus.validated}:
        state.message = f"Skip post — status is {invoice.status.value}"
        state.add_audit("post_skipped", status=invoice.status.value)
        return state, invoice

    result = poster.post(invoice)
    if result.get("ok"):
        invoice.status = InvoiceStatus.posted
        invoice.posted_to = result.get("backend")
        invoice.external_id = result.get("external_id")
        invoice.export_path = result.get("export_path")
        invoice.ar_status = "open"
        rems = reminders.schedule_for_invoice(invoice)
        invoice.reminders_sent = []  # scheduled, not yet sent
        invoice.metadata["reminders_scheduled"] = [r["id"] for r in rems]
        state.message = (
            f"Posted to {invoice.posted_to}"
            + (f" ({result.get('note')})" if result.get("note") else "")
        )
        state.add_audit(
            "posted",
            backend=invoice.posted_to,
            external_id=invoice.external_id,
            reminders=len(rems),
        )
    else:
        invoice.exceptions.append(f"post_failed:{result.get('reason')}")
        invoice.status = InvoiceStatus.exception
        state.requires_human = True
        state.message = f"Post failed: {result.get('reason')}"
        state.add_audit("post_failed", reason=result.get("reason"))

    state.invoice = invoice
    return state, invoice

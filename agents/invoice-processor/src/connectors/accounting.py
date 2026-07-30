"""Accounting connector abstraction — stub / CSV / future QB & NetSuite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from ..models import InvoiceData, InvoiceProcessingResult


class AccountingConnector(Protocol):
    async def prepare_payment(
        self, result: InvoiceProcessingResult
    ) -> dict[str, Any]: ...

    async def post_bill(self, invoice: InvoiceData) -> dict[str, Any]: ...


class StubAccountingConnector:
    """Writes a payment-prep JSON artifact; no external side effects."""

    def __init__(self, out_dir: str | Path | None = None) -> None:
        self.out_dir = Path(out_dir) if out_dir else None

    async def prepare_payment(self, result: InvoiceProcessingResult) -> dict[str, Any]:
        payload = {
            "status": "prepared",
            "backend": "stub",
            "processing_id": result.processing_id,
            "invoice_number": result.invoice.invoice_number,
            "vendor": result.invoice.vendor_name,
            "amount": result.invoice.total,
            "currency": result.invoice.currency,
            "action": result.review.action.value,
            "requires_human": result.requires_human,
            "note": "Stub connector — swap for QuickBooks/NetSuite implementation.",
        }
        if self.out_dir:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            path = self.out_dir / f"{result.processing_id}_payment_prep.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            payload["path"] = str(path)
        return payload

    async def post_bill(self, invoice: InvoiceData) -> dict[str, Any]:
        return {
            "status": "stub_posted",
            "backend": "stub",
            "invoice_number": invoice.invoice_number,
            "external_id": f"stub-{invoice.invoice_number}",
        }


class QuickBooksConnector:
    """Placeholder for real QBO Bill create — implement with OAuth later."""

    async def prepare_payment(self, result: InvoiceProcessingResult) -> dict[str, Any]:
        return {
            "status": "not_implemented",
            "backend": "quickbooks",
            "hint": "Implement OAuth + Bill endpoint; keep this interface stable.",
        }

    async def post_bill(self, invoice: InvoiceData) -> dict[str, Any]:
        raise NotImplementedError("QuickBooks connector not configured")


class NetSuiteConnector:
    """Placeholder for NetSuite vendor bill — implement with TBA later."""

    async def prepare_payment(self, result: InvoiceProcessingResult) -> dict[str, Any]:
        return {
            "status": "not_implemented",
            "backend": "netsuite",
            "hint": "Implement TBA + vendor bill record; keep this interface stable.",
        }

    async def post_bill(self, invoice: InvoiceData) -> dict[str, Any]:
        raise NotImplementedError("NetSuite connector not configured")

"""Invoice persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Invoice, InvoiceStatus, utc_now


class InvoiceStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.dir = Path(data_dir) / "invoices"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, invoice_id: str) -> Path:
        return self.dir / f"{invoice_id}.json"

    def save(self, invoice: Invoice) -> Invoice:
        invoice.updated_at = utc_now()
        with self._path(invoice.id).open("w", encoding="utf-8") as f:
            json.dump(invoice.model_dump(), f, indent=2, ensure_ascii=False)
        return invoice

    def get(self, invoice_id: str) -> Invoice | None:
        p = self._path(invoice_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return Invoice(**json.load(f))

    def list(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Invoice]:
        items: list[Invoice] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    inv = Invoice(**json.load(f))
            except Exception:
                continue
            if status and inv.status.value != status:
                continue
            items.append(inv)
            if len(items) >= limit:
                break
        return items

    def list_exceptions(self, limit: int = 100) -> list[Invoice]:
        return [
            i
            for i in self.list(limit=200)
            if i.status in {InvoiceStatus.exception, InvoiceStatus.pending_hitl}
            or i.exceptions
        ][:limit]

    def list_open_ar(self, limit: int = 200) -> list[Invoice]:
        return [
            i
            for i in self.list(limit=500)
            if i.ar_status in {"open", "reminded"}
            and i.status in {InvoiceStatus.posted, InvoiceStatus.validated, InvoiceStatus.extracted}
        ][:limit]

    def find_duplicate(self, vendor: str | None, number: str | None) -> Invoice | None:
        if not vendor or not number:
            return None
        v = vendor.lower().strip()
        n = number.lower().strip()
        for inv in self.list(limit=500):
            if (
                (inv.vendor_name or "").lower().strip() == v
                and (inv.invoice_number or "").lower().strip() == n
                and inv.status != InvoiceStatus.void
            ):
                return inv
        return None

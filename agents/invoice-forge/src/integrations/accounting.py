"""Post invoices to CSV (default), QuickBooks Online, or Xero stubs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import httpx

from ..models import Invoice, utc_now


class AccountingPoster:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        acct = cfg.get("accounting") or {}
        self.backend = (acct.get("backend") or "csv").lower()
        self.export_dir = Path(
            acct.get("export_dir") or Path(cfg["paths"]["data"]) / "exports"
        )
        if not self.export_dir.is_absolute():
            self.export_dir = Path(cfg["paths"]["root"]) / self.export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def post(self, invoice: Invoice) -> dict[str, Any]:
        if self.backend == "quickbooks":
            result = self._post_quickbooks(invoice)
            if result.get("ok"):
                return result
            # fall through to CSV with note
            csv_result = self._post_csv(invoice)
            csv_result["note"] = result.get("reason") or "QBO unavailable; wrote CSV"
            csv_result["backend"] = "csv"
            return csv_result
        if self.backend == "xero":
            result = self._post_xero(invoice)
            if result.get("ok"):
                return result
            csv_result = self._post_csv(invoice)
            csv_result["note"] = result.get("reason") or "Xero unavailable; wrote CSV"
            csv_result["backend"] = "csv"
            return csv_result
        return self._post_csv(invoice)

    def _post_csv(self, invoice: Invoice) -> dict[str, Any]:
        path = self.export_dir / "invoices.csv"
        fieldnames = [
            "id",
            "invoice_number",
            "vendor_name",
            "vendor_email",
            "invoice_date",
            "due_date",
            "currency",
            "subtotal",
            "tax",
            "total",
            "po_number",
            "status",
            "posted_at",
        ]
        rows: list[dict[str, Any]] = []
        if path.exists():
            with path.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        # upsert by id
        rows = [r for r in rows if r.get("id") != invoice.id]
        rows.append(
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number or "",
                "vendor_name": invoice.vendor_name or "",
                "vendor_email": invoice.vendor_email or "",
                "invoice_date": invoice.invoice_date or "",
                "due_date": invoice.due_date or "",
                "currency": invoice.currency,
                "subtotal": invoice.subtotal if invoice.subtotal is not None else "",
                "tax": invoice.tax if invoice.tax is not None else "",
                "total": invoice.total if invoice.total is not None else "",
                "po_number": invoice.po_number or "",
                "status": invoice.status.value,
                "posted_at": utc_now(),
            }
        )
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

        # Also JSON export per invoice
        jpath = self.export_dir / f"{invoice.id}.json"
        jpath.write_text(
            json.dumps(invoice.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "backend": "csv",
            "external_id": invoice.id,
            "export_path": str(path),
        }

    def _post_quickbooks(self, invoice: Invoice) -> dict[str, Any]:
        qbo = self.cfg.get("quickbooks") or {}
        token = qbo.get("access_token") or ""
        realm = qbo.get("realm_id") or ""
        if not token or not realm:
            return {"ok": False, "reason": "QuickBooks not configured"}
        # Minimal Bill create stub — soft-fail
        url = f"https://quickbooks.api.intuit.com/v3/company/{realm}/bill"
        payload = {
            "VendorRef": {"name": invoice.vendor_name or "Unknown Vendor"},
            "DocNumber": invoice.invoice_number or invoice.id,
            "TxnDate": invoice.invoice_date,
            "DueDate": invoice.due_date,
            "PrivateNote": f"Posted by Matrixly InvoiceForge {invoice.id}",
            "Line": [
                {
                    "Amount": invoice.total or 0,
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "Description": (invoice.line_items[0].description if invoice.line_items else "Invoice"),
                }
            ],
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if not resp.is_success:
                    return {"ok": False, "reason": f"QBO HTTP {resp.status_code}"}
                data = resp.json()
                bill_id = (data.get("Bill") or {}).get("Id") or invoice.id
                return {
                    "ok": True,
                    "backend": "quickbooks",
                    "external_id": str(bill_id),
                    "export_path": None,
                }
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    def _post_xero(self, invoice: Invoice) -> dict[str, Any]:
        xero = self.cfg.get("xero") or {}
        token = xero.get("access_token") or ""
        tenant = xero.get("tenant_id") or ""
        if not token or not tenant:
            return {"ok": False, "reason": "Xero not configured"}
        payload = {
            "Invoices": [
                {
                    "Type": "ACCPAY",
                    "Contact": {"Name": invoice.vendor_name or "Unknown Vendor"},
                    "InvoiceNumber": invoice.invoice_number or invoice.id,
                    "Date": invoice.invoice_date,
                    "DueDate": invoice.due_date,
                    "LineItems": [
                        {
                            "Description": li.description or "Item",
                            "Quantity": li.quantity,
                            "UnitAmount": li.unit_price,
                            "LineAmount": li.amount,
                        }
                        for li in (invoice.line_items or [])
                    ]
                    or [
                        {
                            "Description": "Invoice total",
                            "Quantity": 1,
                            "UnitAmount": invoice.total or 0,
                            "LineAmount": invoice.total or 0,
                        }
                    ],
                    "Status": "AUTHORISED",
                }
            ]
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.xero.com/api.xro/2.0/Invoices",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Xero-tenant-id": tenant,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if not resp.is_success:
                    return {"ok": False, "reason": f"Xero HTTP {resp.status_code}"}
                data = resp.json()
                invs = data.get("Invoices") or []
                xid = (invs[0].get("InvoiceID") if invs else None) or invoice.id
                return {
                    "ok": True,
                    "backend": "xero",
                    "external_id": str(xid),
                    "export_path": None,
                }
        except Exception as e:
            return {"ok": False, "reason": str(e)}

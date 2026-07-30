"""Purchase Order store — file-backed stub ready for ERP swap."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from ..models import PurchaseOrder, PurchaseOrderLine


class PurchaseOrderStore:
    """
    Simple JSON directory store.

    Production swap: implement the same interface against NetSuite /
    QuickBooks PO APIs without changing matcher tools.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, po_number: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", po_number.strip())
        return self.root / f"{safe}.json"

    def save(self, po: PurchaseOrder) -> None:
        self._path(po.po_number).write_text(
            po.model_dump_json(indent=2), encoding="utf-8"
        )

    def get(self, po_number: str) -> Optional[PurchaseOrder]:
        if not po_number:
            return None
        # exact filename
        p = self._path(po_number)
        if p.exists():
            return PurchaseOrder.model_validate_json(p.read_text(encoding="utf-8"))
        # case-insensitive scan
        target = po_number.strip().lower()
        for f in self.root.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if str(data.get("po_number", "")).strip().lower() == target:
                    return PurchaseOrder.model_validate(data)
            except Exception:
                continue
        return None

    def list_all(self) -> list[PurchaseOrder]:
        items: list[PurchaseOrder] = []
        for f in sorted(self.root.glob("*.json")):
            try:
                items.append(
                    PurchaseOrder.model_validate_json(f.read_text(encoding="utf-8"))
                )
            except Exception:
                continue
        return items

    def find_by_vendor(self, vendor_name: str, limit: int = 5) -> list[PurchaseOrder]:
        if not vendor_name:
            return []
        scored: list[tuple[float, PurchaseOrder]] = []
        for po in self.list_all():
            score = SequenceMatcher(
                None, vendor_name.lower(), (po.vendor_name or "").lower()
            ).ratio()
            if score >= 0.5:
                scored.append((score, po))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def ensure_seed_data(self) -> None:
        """Seed demo POs if store is empty — enables offline smoke tests."""
        if any(self.root.glob("*.json")):
            return
        samples = [
            PurchaseOrder(
                po_number="PO-10482",
                vendor_name="Acme Office Supplies",
                status="open",
                currency="USD",
                order_date="2026-06-01",
                total=1250.00,
                remaining_amount=1250.00,
                line_items=[
                    PurchaseOrderLine(
                        line_number=1,
                        description="A4 Copy Paper Case (10 reams)",
                        quantity=10,
                        unit_price=45.00,
                        amount=450.00,
                        sku="PAPER-A4-10",
                        received_qty=10,
                    ),
                    PurchaseOrderLine(
                        line_number=2,
                        description="Black Toner Cartridge HP 26A",
                        quantity=5,
                        unit_price=160.00,
                        amount=800.00,
                        sku="TONER-26A",
                        received_qty=5,
                    ),
                ],
            ),
            PurchaseOrder(
                po_number="PO-10501",
                vendor_name="BrightField HVAC Parts",
                status="open",
                currency="USD",
                order_date="2026-06-15",
                total=4820.50,
                remaining_amount=4820.50,
                line_items=[
                    PurchaseOrderLine(
                        line_number=1,
                        description="Condenser fan motor 1/4 HP",
                        quantity=4,
                        unit_price=285.00,
                        amount=1140.00,
                        sku="CFM-025",
                        received_qty=4,
                    ),
                    PurchaseOrderLine(
                        line_number=2,
                        description="R-410A refrigerant cylinder",
                        quantity=6,
                        unit_price=613.4167,
                        amount=3680.50,
                        sku="R410A-CYL",
                        received_qty=6,
                    ),
                ],
            ),
            PurchaseOrder(
                po_number="PO-10999",
                vendor_name="Northwind Logistics",
                status="open",
                currency="USD",
                order_date="2026-07-01",
                total=890.00,
                remaining_amount=890.00,
                line_items=[
                    PurchaseOrderLine(
                        line_number=1,
                        description="Same-day courier service block",
                        quantity=1,
                        unit_price=890.00,
                        amount=890.00,
                        sku="COURIER-BLK",
                        received_qty=1,
                    ),
                ],
            ),
        ]
        for po in samples:
            self.save(po)

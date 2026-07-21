"""Exception detection for shipments (late / exception status)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Shipment, ShippingException


def _parse_date(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")[:10]).replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def scan_exceptions(shipments: list[Shipment], cfg: dict[str, Any]) -> list[ShippingException]:
    ex_cfg = cfg.get("exceptions") or {}
    late_days = int(ex_cfg.get("late_after_days") or 3)
    statuses = {s.lower() for s in ex_cfg.get("exception_statuses") or []}
    keywords = [k.lower() for k in ex_cfg.get("exception_keywords") or []]
    now = datetime.now(timezone.utc)
    out: list[ShippingException] = []

    for s in shipments:
        st = (s.status or "").lower().replace(" ", "_")
        detail = str((s.raw or {}).get("statusDetail") or "").lower()
        blob = f"{st} {detail} {s.carrier}"

        if st in statuses or any(k in blob for k in keywords if k):
            out.append(
                ShippingException(
                    shipment=s,
                    code="carrier_exception",
                    severity="high",
                    message=detail or f"Carrier status: {s.status}",
                    suggested_action="Contact carrier; draft customer update; verify address",
                )
            )
            continue

        if st in {"delivered", "cancelled", "canceled", "awaiting_shipment", "awaiting_payment"}:
            continue

        eta = _parse_date(s.estimated_delivery)
        ship = _parse_date(s.ship_date)
        if eta and (now - eta).days >= 1 and st not in {"delivered"}:
            out.append(
                ShippingException(
                    shipment=s,
                    code="past_eta",
                    severity="high",
                    message=f"Past estimated delivery ({s.estimated_delivery})",
                    suggested_action="Pull latest tracking; notify customer with revised ETA",
                )
            )
        elif ship and (now - ship).days >= late_days and st in {"shipped", "in_transit", "in transit"}:
            out.append(
                ShippingException(
                    shipment=s,
                    code="late_in_transit",
                    severity="medium",
                    message=f"In transit { (now - ship).days }d since ship date",
                    suggested_action="Monitor tracking; prepare proactive WISMO reply",
                )
            )

    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda e: (order.get(e.severity, 9), e.shipment.order_number))
    return out


def exceptions_report(exceptions: list[ShippingException]) -> str:
    lines = ["# Shipping Exceptions Report", ""]
    if not exceptions:
        lines.append("No exceptions detected.")
        return "\n".join(lines)
    lines.append(f"**Total:** {len(exceptions)}")
    lines.append("")
    for e in exceptions:
        s = e.shipment
        lines.append(
            f"- **[{e.severity.upper()}]** `{e.code}` {s.order_number} · {s.carrier} · "
            f"{s.tracking_number or 'no tracking'}"
        )
        lines.append(f"  - {e.message}")
        lines.append(f"  - Action: {e.suggested_action}")
        lines.append(f"  - Customer: {s.customer_email or s.customer_name or '—'}")
    return "\n".join(lines)

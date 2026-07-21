"""Shipment domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Shipment:
    order_id: str
    order_number: str
    status: str
    carrier: str = ""
    service: str = ""
    tracking_number: str = ""
    tracking_url: str = ""
    ship_date: str = ""
    estimated_delivery: str = ""
    customer_name: str = ""
    customer_email: str = ""
    ship_to_city: str = ""
    ship_to_state: str = ""
    ship_to_country: str = ""
    items_summary: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ShippingException:
    shipment: Shipment
    code: str
    severity: str  # high | medium | low
    message: str
    suggested_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_number": self.shipment.order_number,
            "tracking_number": self.shipment.tracking_number,
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "customer_email": self.shipment.customer_email,
            "status": self.shipment.status,
        }


@dataclass
class ProposedAction:
    """HITL unit for destructive shipping ops."""

    action: str  # cancel_order | update_address | create_label | void_label | notify_customer
    payload: dict[str, Any]
    id: str = ""
    reason: str = ""
    status: str = "pending"  # pending | approved | rejected | applied
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"shp_{uuid.uuid4().hex[:10]}"
        if not self.created_at:
            self.created_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WismoReply:
    order_number: str
    subject: str
    body: str
    tracking_number: str = ""
    tracking_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

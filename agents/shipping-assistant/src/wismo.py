"""WISMO (Where Is My Order) reply drafts — human sends."""

from __future__ import annotations

from typing import Any

from .models import Shipment, WismoReply


def draft_wismo_reply(shipment: Shipment, cfg: dict[str, Any]) -> WismoReply:
    op = cfg.get("operator") or {}
    company = op.get("company") or "our team"
    name = (shipment.customer_name or "there").split()[0]
    tracking = shipment.tracking_number or "not assigned yet"
    url = shipment.tracking_url
    status = shipment.status or "processing"
    carrier = shipment.carrier or "our carrier partner"

    lines = [
        f"Hi {name},",
        "",
        f"Thanks for reaching out about order **{shipment.order_number}**.",
        "",
        f"Current status: **{status}** via {carrier}.",
    ]
    if shipment.tracking_number:
        lines.append(f"Tracking number: `{tracking}`")
        if url and (cfg.get("wismo") or {}).get("include_tracking_url", True):
            lines.append(f"Track here: {url}")
    else:
        lines.append(
            "A tracking number will appear as soon as the label is created and the package is scanned."
        )
    if shipment.estimated_delivery:
        lines.append(f"Estimated delivery: {shipment.estimated_delivery}")
    if shipment.ship_to_city:
        lines.append(
            f"Ship-to: {shipment.ship_to_city}"
            + (f", {shipment.ship_to_state}" if shipment.ship_to_state else "")
        )
    lines += [
        "",
        "If anything looks off (address, delay, or damage), reply to this email and our team will help right away.",
        "",
        f"Best regards,",
        f"{company} Shipping Desk",
    ]
    body = "\n".join(lines)
    # plain text without md bold for email body
    body = body.replace("**", "")

    subject = f"Update on your order {shipment.order_number}"
    return WismoReply(
        order_number=shipment.order_number,
        subject=subject,
        body=body,
        tracking_number=shipment.tracking_number,
        tracking_url=shipment.tracking_url,
    )


def draft_exception_notify(
    shipment: Shipment,
    message: str,
    cfg: dict[str, Any],
    *,
    audience: str = "internal",
) -> dict[str, str]:
    op = cfg.get("operator") or {}
    if audience == "customer":
        reply = draft_wismo_reply(shipment, cfg)
        extra = f"\n\nNote: {message}" if message else ""
        return {
            "to": shipment.customer_email or "",
            "subject": reply.subject,
            "body": reply.body + extra,
            "kind": "customer_draft",
        }
    return {
        "to": op.get("notify_email") or op.get("email") or "",
        "subject": f"[Ship Exception] {shipment.order_number} · {shipment.status}",
        "body": (
            f"Exception on order {shipment.order_number}\n"
            f"Customer: {shipment.customer_name} <{shipment.customer_email}>\n"
            f"Carrier: {shipment.carrier} · Tracking: {shipment.tracking_number}\n"
            f"Status: {shipment.status}\n"
            f"Detail: {message}\n"
            f"Suggested: review in ShipStation and approve next action in Shipping Assistant.\n"
        ),
        "kind": "internal_draft",
    }

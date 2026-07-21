"""Shipping Assistant agent facade."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_config
from .exceptions import exceptions_report, scan_exceptions
from .models import ProposedAction, Shipment
from .shipstation_client import ShipStationClient
from .wismo import draft_exception_notify, draft_wismo_reply


class ShippingAssistant:
    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg or load_config()
        self.client = ShipStationClient(self.cfg)
        self._pending: dict[str, ProposedAction] = {}
        self._pending_path = Path(self.cfg["_paths"]["data"]) / "pending_actions.json"
        self._load_pending()

    def _load_pending(self) -> None:
        if self._pending_path.exists():
            data = json.loads(self._pending_path.read_text(encoding="utf-8"))
            self._pending = {
                k: ProposedAction(**v) for k, v in data.items() if v.get("status") == "pending"
            }

    def _save_pending(self) -> None:
        blob = {k: v.to_dict() for k, v in self._pending.items()}
        self._pending_path.write_text(json.dumps(blob, indent=2), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        return {
            "mode": "demo" if self.client.is_demo else "live",
            "shipstation_base": self.client.base_url,
            "pending_actions": len(self._pending),
        }

    def list_shipments(self) -> list[Shipment]:
        return self.client.list_shipments()

    def track(self, *, order_number: str = "", tracking: str = "") -> Shipment | None:
        if order_number:
            return self.client.find_by_order_number(order_number)
        if tracking:
            return self.client.find_by_tracking(tracking)
        return None

    def exceptions(self) -> dict[str, Any]:
        ships = self.list_shipments()
        ex = scan_exceptions(ships, self.cfg)
        return {
            "count": len(ex),
            "exceptions": [e.to_dict() for e in ex],
            "report": exceptions_report(ex),
            "mode": "demo" if self.client.is_demo else "live",
        }

    def wismo(self, order_number: str) -> dict[str, Any]:
        s = self.client.find_by_order_number(order_number)
        if not s:
            raise ValueError(f"Order not found: {order_number}")
        reply = draft_wismo_reply(s, self.cfg)
        return {"shipment": s.to_dict(), "draft": reply.to_dict()}

    def notify_drafts_for_exceptions(self) -> list[dict[str, Any]]:
        ships = self.list_shipments()
        ex = scan_exceptions(ships, self.cfg)
        drafts = []
        for e in ex:
            internal = draft_exception_notify(e.shipment, e.message, self.cfg, audience="internal")
            customer = draft_exception_notify(e.shipment, e.message, self.cfg, audience="customer")
            drafts.append(
                {
                    "order_number": e.shipment.order_number,
                    "exception": e.to_dict(),
                    "internal_draft": internal,
                    "customer_draft": customer,
                }
            )
        return drafts

    def propose_action(self, action: str, payload: dict[str, Any], reason: str = "") -> ProposedAction:
        hitl = self.cfg.get("hitl") or {}
        require = set(hitl.get("require_approval_for") or [])
        if action not in require and action not in set(hitl.get("auto_allow") or []):
            # unknown destructive default to approval
            pass
        pa = ProposedAction(action=action, payload=payload, reason=reason or action)
        if action in require:
            self._pending[pa.id] = pa
            self._save_pending()
            return pa
        # auto-allow actions are informational
        pa.status = "applied"
        return pa

    def list_pending(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._pending.values() if p.status == "pending"]

    def approve(self, action_id: str) -> dict[str, Any]:
        pa = self._pending.get(action_id)
        if not pa:
            raise ValueError(f"Pending action not found: {action_id}")
        # MVP: mark applied — live ShipStation mutations wired when keys present
        pa.status = "applied"
        result = {
            "id": pa.id,
            "action": pa.action,
            "status": "applied",
            "note": (
                "Recorded approval. Live ShipStation mutation executes when API credentials "
                "and action handlers are enabled for this op."
            ),
            "payload": pa.payload,
        }
        del self._pending[action_id]
        self._save_pending()
        return result

    def reject(self, action_id: str) -> dict[str, Any]:
        pa = self._pending.get(action_id)
        if not pa:
            raise ValueError(f"Pending action not found: {action_id}")
        pa.status = "rejected"
        del self._pending[action_id]
        self._save_pending()
        return {"id": action_id, "status": "rejected"}

    def shipments_report(self, shipments: list[Shipment] | None = None) -> str:
        ships = shipments if shipments is not None else self.list_shipments()
        lines = [
            "# Shipments",
            "",
            f"**Mode:** {'demo' if self.client.is_demo else 'live ShipStation'}",
            f"**Count:** {len(ships)}",
            "",
        ]
        for s in ships:
            lines.append(
                f"- **{s.order_number}** · {s.status} · {s.carrier or '—'} · "
                f"{s.tracking_number or 'no tracking'} · {s.customer_email or s.customer_name}"
            )
        return "\n".join(lines)

    def export_snapshot(self) -> str:
        ships = [s.to_dict() for s in self.list_shipments()]
        ex = self.exceptions()
        path = Path(self.cfg["_paths"]["output"]) / "shipping-snapshot.json"
        path.write_text(
            json.dumps(
                {"mode": "demo" if self.client.is_demo else "live", "shipments": ships, "exceptions": ex["exceptions"]},
                indent=2,
            ),
            encoding="utf-8",
        )
        return str(path)

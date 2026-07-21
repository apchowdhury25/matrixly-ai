"""ShipStation API client + demo backend."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from .demo_data import sample_shipments
from .models import Shipment


class ShipStationClient:
    def __init__(self, cfg: dict[str, Any]):
        ss = cfg.get("shipstation") or {}
        self.base_url = (ss.get("base_url") or "https://ssapi.shipstation.com").rstrip("/")
        self.api_key = ss.get("api_key") or ""
        self.api_secret = ss.get("api_secret") or ""
        self.mode = (ss.get("mode") or "demo").lower()
        self.page_size = int(ss.get("page_size") or 50)

    @property
    def is_demo(self) -> bool:
        return self.mode != "live" or not (self.api_key and self.api_secret)

    def _headers(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.api_key}:{self.api_secret}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
                params=params or {},
            )
            resp.raise_for_status()
            return resp.json()

    def list_shipments(self, *, page: int = 1) -> list[Shipment]:
        if self.is_demo:
            return sample_shipments()

        # Prefer shipments endpoint; fall back to orders if needed
        try:
            data = self._get(
                "/shipments",
                {"page": page, "pageSize": self.page_size, "includeShipmentItems": True},
            )
            rows = data.get("shipments") or []
            return [self._map_shipment(r) for r in rows]
        except Exception:
            data = self._get(
                "/orders",
                {"page": page, "pageSize": self.page_size, "orderStatus": "shipped"},
            )
            rows = data.get("orders") or []
            return [self._map_order(r) for r in rows]

    def list_orders(self, *, page: int = 1, order_status: str | None = None) -> list[Shipment]:
        if self.is_demo:
            ships = sample_shipments()
            if order_status:
                return [s for s in ships if s.status == order_status]
            return ships
        params: dict[str, Any] = {"page": page, "pageSize": self.page_size}
        if order_status:
            params["orderStatus"] = order_status
        data = self._get("/orders", params)
        return [self._map_order(r) for r in (data.get("orders") or [])]

    def find_by_order_number(self, order_number: str) -> Shipment | None:
        order_number = (order_number or "").strip()
        for s in self.list_shipments():
            if s.order_number.lower() == order_number.lower():
                return s
        if not self.is_demo:
            try:
                data = self._get("/orders", {"orderNumber": order_number})
                orders = data.get("orders") or []
                if orders:
                    return self._map_order(orders[0])
            except Exception:
                pass
        return None

    def find_by_tracking(self, tracking: str) -> Shipment | None:
        tracking = (tracking or "").strip()
        for s in self.list_shipments():
            if s.tracking_number and s.tracking_number.lower() == tracking.lower():
                return s
        return None

    def _map_shipment(self, r: dict[str, Any]) -> Shipment:
        ship_to = r.get("shipTo") or {}
        return Shipment(
            order_id=str(r.get("orderId") or r.get("shipmentId") or ""),
            order_number=str(r.get("orderNumber") or ""),
            status=str(r.get("shipmentStatus") or r.get("voided") and "voided" or "shipped"),
            carrier=str(r.get("carrierCode") or r.get("serviceCode") or ""),
            service=str(r.get("serviceCode") or ""),
            tracking_number=str(r.get("trackingNumber") or ""),
            tracking_url=str(r.get("trackingUrl") or ""),
            ship_date=str(r.get("shipDate") or "")[:10],
            estimated_delivery="",
            customer_name=str(ship_to.get("name") or ""),
            customer_email=str(r.get("customerEmail") or ship_to.get("email") or ""),
            ship_to_city=str(ship_to.get("city") or ""),
            ship_to_state=str(ship_to.get("state") or ""),
            ship_to_country=str(ship_to.get("country") or ""),
            items_summary=_items_summary(r.get("shipmentItems") or r.get("items")),
            raw=r,
        )

    def _map_order(self, r: dict[str, Any]) -> Shipment:
        ship_to = r.get("shipTo") or {}
        return Shipment(
            order_id=str(r.get("orderId") or ""),
            order_number=str(r.get("orderNumber") or ""),
            status=str(r.get("orderStatus") or "unknown"),
            carrier=str(r.get("carrierCode") or ""),
            service=str(r.get("serviceCode") or ""),
            tracking_number=str(r.get("trackingNumber") or ""),
            tracking_url="",
            ship_date=str(r.get("shipDate") or "")[:10],
            estimated_delivery="",
            customer_name=str(ship_to.get("name") or r.get("billTo", {}).get("name") or ""),
            customer_email=str(r.get("customerEmail") or ""),
            ship_to_city=str(ship_to.get("city") or ""),
            ship_to_state=str(ship_to.get("state") or ""),
            ship_to_country=str(ship_to.get("country") or ""),
            items_summary=_items_summary(r.get("items")),
            raw=r,
        )


def _items_summary(items: list | None) -> str:
    if not items:
        return ""
    parts = []
    for it in items[:5]:
        name = it.get("name") or it.get("sku") or "item"
        qty = it.get("quantity") or 1
        parts.append(f"{qty}x {name}")
    return ", ".join(parts)

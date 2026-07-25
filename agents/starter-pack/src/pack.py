"""Starter Pack orchestrator — registry, overview, analytics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters.bookwise import BookWiseAdapter
from .adapters.invoiceforge import InvoiceForgeAdapter
from .adapters.supportforge import SupportForgeAdapter
from .models import ActivityItem, AgentCard, OverviewResponse, PackSettings
from .services.audit import AuditLog
from .services.settings import SettingsStore
from .services.usage import UsageMeter


class StarterPack:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        agents_root = Path(cfg["paths"]["agents_root"])
        self.settings = SettingsStore(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data)
        self.runtime = cfg.get("agent_runtime") or {}
        self.local_fallback = bool(self.runtime.get("local_data_fallback", True))

        defs = cfg.get("agents") or {}
        self.adapters: dict[str, Any] = {}

        for key, cls in (
            ("supportforge", SupportForgeAdapter),
            ("bookwise", BookWiseAdapter),
            ("invoiceforge", InvoiceForgeAdapter),
        ):
            meta = defs.get(key) or {}
            rt = self.runtime.get(key) or {}
            local_rel = meta.get("local_data") or f"../{key.replace('forge', '-forge').replace('bookwise', 'book-wise')}"
            # normalize local paths
            local_map = {
                "supportforge": agents_root / "support-forge" / "data",
                "bookwise": agents_root / "book-wise" / "data",
                "invoiceforge": agents_root / "invoice-forge" / "data",
            }
            local_data = local_map.get(key)
            self.adapters[key] = cls(
                url=rt.get("url") or f"http://127.0.0.1:{meta.get('default_port', 8000)}",
                api_key=rt.get("api_key") or "change-me-admin-key",
                meta=meta,
                local_data=local_data,
                local_fallback=self.local_fallback,
            )

    def overview(self) -> OverviewResponse:
        settings = self.settings.load()
        cards: list[AgentCard] = []
        activity: list[ActivityItem] = []
        analytics = {
            "tickets_handled": 0,
            "appointments_booked": 0,
            "invoices_processed": 0,
            "pending_hitl": 0,
            "agents_online": 0,
            "agents_enabled": 0,
        }
        defs = self.cfg.get("agents") or {}

        for key, adapter in self.adapters.items():
            meta = defs.get(key) or {}
            enabled = bool(settings.agents_enabled.get(key, True))
            rt_enabled = bool((self.runtime.get(key) or {}).get("enabled", True))
            enabled = enabled and rt_enabled

            health = adapter.health() if enabled else {"ok": False, "_online": False, "disabled": True}
            # Live process only; local_fallback still supplies metrics/activity
            online = bool(enabled and health.get("_online") is True)

            metrics = adapter.metrics()
            if enabled and health.get("_online"):
                st = adapter.admin_status()
                # merge useful status fields
                if st:
                    metrics = {**metrics, **{k: v for k, v in st.items() if not str(k).startswith("_")}}

            if enabled:
                analytics["agents_enabled"] += 1
            if online:
                analytics["agents_online"] += 1

            analytics["tickets_handled"] += int(metrics.get("tickets_handled") or metrics.get("tickets") or 0)
            analytics["appointments_booked"] += int(
                metrics.get("appointments_booked") or metrics.get("upcoming") or metrics.get("bookings") or 0
            )
            analytics["invoices_processed"] += int(
                metrics.get("invoices_processed") or metrics.get("invoices") or 0
            )
            pend = len(adapter.hitl_pending()) if enabled else 0
            analytics["pending_hitl"] += pend
            metrics["pending_hitl"] = pend

            url = adapter.url
            cards.append(
                AgentCard(
                    id=key,
                    name=meta.get("name") or adapter.name,
                    description=meta.get("description") or "",
                    tile=meta.get("tile") or "",
                    category=meta.get("category") or "",
                    enabled=enabled,
                    online=online,
                    url=url,
                    health=health,
                    metrics=metrics,
                    error=health.get("error") if not online and enabled else None,
                    widget_url=f"{url}{meta.get('widget_path') or ''}",
                    panel_url=f"{url}{meta.get('panel_path') or ''}",
                )
            )

            if enabled:
                activity.extend(adapter.to_activity(adapter.audit(limit=15), limit=15))

        # sort activity by ts desc
        activity.sort(key=lambda a: a.ts or "", reverse=True)
        activity = activity[:40]

        pack = self.cfg.get("pack") or {}
        return OverviewResponse(
            pack=str(pack.get("name") or "Matrixly Starter Pack"),
            version=str(pack.get("version") or "1.0.0"),
            business=self.cfg.get("business") or {},
            agents=cards,
            analytics=analytics,
            activity=activity,
            pending_hitl=int(analytics["pending_hitl"]),
        )

    def set_agent_enabled(self, agent_id: str, enabled: bool) -> PackSettings:
        s = self.settings.update(agents_enabled={agent_id: enabled})
        self.audit.write("agent_toggle", agent_id=agent_id, enabled=enabled)
        self.usage.record("agent_toggle", agent_id=agent_id, enabled=enabled)
        return s

    def update_connections(self, connections: dict[str, Any]) -> PackSettings:
        # Never store secrets in plain form without note — redacted keys still allowed as config labels
        safe = dict(connections)
        s = self.settings.update(connections=safe)
        self.audit.write("connections_updated", keys=list(safe.keys()))
        return s

    def status(self) -> dict[str, Any]:
        ov = self.overview()
        return {
            "service": "starter-pack",
            "version": ov.version,
            "agents_online": ov.analytics.get("agents_online"),
            "agents_enabled": ov.analytics.get("agents_enabled"),
            "pending_hitl": ov.pending_hitl,
            "analytics": ov.analytics,
            "pack_usage": self.usage.summary(),
        }

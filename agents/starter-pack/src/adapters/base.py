"""Base agent adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ..models import ActivityItem, utc_now


class AgentAdapter:
    def __init__(
        self,
        *,
        agent_id: str,
        name: str,
        url: str,
        api_key: str,
        meta: dict[str, Any],
        local_data: Path | None = None,
        local_fallback: bool = True,
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.meta = meta
        self.local_data = local_data
        self.local_fallback = local_fallback

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    def health(self) -> dict[str, Any]:
        path = self.meta.get("health_path") or "/v1/health"
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{self.url}{path}")
                if r.status_code < 400:
                    data = r.json()
                    data["_online"] = True
                    data["_source"] = "http"
                    return data
        except Exception as e:
            offline = {"ok": False, "_online": False, "error": str(e), "_source": "http"}
            if self.local_fallback:
                offline.update(self._local_health())
                offline["_source"] = "local_fallback"
            return offline
        return {"ok": False, "_online": False, "error": f"status {r.status_code}"}

    def admin_status(self) -> dict[str, Any]:
        path = self.meta.get("admin_status_path") or "/v1/admin/status"
        try:
            with httpx.Client(timeout=4.0) as client:
                r = client.get(f"{self.url}{path}", headers=self._headers())
                if r.status_code < 400:
                    data = r.json()
                    data["_online"] = True
                    return data
        except Exception:
            pass
        if self.local_fallback:
            return self._local_status()
        return {}

    def audit(self, limit: int = 30) -> list[dict[str, Any]]:
        path = self.meta.get("audit_path") or "/v1/admin/audit"
        try:
            with httpx.Client(timeout=4.0) as client:
                r = client.get(
                    f"{self.url}{path}",
                    headers=self._headers(),
                    params={"limit": limit},
                )
                if r.status_code < 400:
                    data = r.json()
                    items = data.get("items") if isinstance(data, dict) else data
                    return list(items or [])
        except Exception:
            pass
        if self.local_fallback:
            return self._local_audit(limit)
        return []

    def usage(self) -> dict[str, Any]:
        path = self.meta.get("usage_path") or "/v1/admin/usage"
        try:
            with httpx.Client(timeout=4.0) as client:
                r = client.get(f"{self.url}{path}", headers=self._headers())
                if r.status_code < 400:
                    return r.json()
        except Exception:
            pass
        if self.local_fallback:
            return self._local_usage()
        return {}

    def hitl_pending(self) -> list[dict[str, Any]]:
        path = self.meta.get("hitl_path") or "/v1/admin/hitl"
        try:
            with httpx.Client(timeout=4.0) as client:
                r = client.get(f"{self.url}{path}", headers=self._headers())
                if r.status_code < 400:
                    data = r.json()
                    items = data.get("items") if isinstance(data, dict) else data
                    return list(items or [])
        except Exception:
            pass
        if self.local_fallback:
            return self._local_hitl()
        return []

    def metrics(self) -> dict[str, Any]:
        """Agent-specific metrics for analytics."""
        return self._local_metrics()

    def to_activity(self, audit_rows: list[dict[str, Any]], limit: int = 20) -> list[ActivityItem]:
        out: list[ActivityItem] = []
        for row in audit_rows[:limit]:
            event = str(row.get("event") or row.get("action") or "event")
            ts = str(row.get("ts") or row.get("created_at") or "")
            detail = {k: v for k, v in row.items() if k not in {"event", "ts", "action"}}
            out.append(
                ActivityItem(
                    agent_id=self.agent_id,
                    agent_name=self.name,
                    event=event,
                    detail=detail,
                    ts=ts or utc_now(),
                )
            )
        return out

    # --- local data fallbacks ---

    def _local_health(self) -> dict[str, Any]:
        if not self.local_data or not self.local_data.exists():
            return {"ok": False, "local": False}
        return {
            "ok": True,
            "local": True,
            "service": self.agent_id,
            "note": "Agent process offline; using local data fallback",
        }

    def _local_status(self) -> dict[str, Any]:
        m = self._local_metrics()
        return {"local": True, **m}

    def _local_audit(self, limit: int) -> list[dict[str, Any]]:
        if not self.local_data:
            return []
        path = self.local_data / "audit" / "events.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(out))

    def _local_usage(self) -> dict[str, Any]:
        if not self.local_data:
            return {}
        path = self.local_data / "usage" / "usage.jsonl"
        if not path.exists():
            return {"events": 0}
        n = 0
        for _ in path.read_text(encoding="utf-8").splitlines():
            n += 1
        return {"events": n, "source": "local"}

    def _local_hitl(self) -> list[dict[str, Any]]:
        if not self.local_data:
            return []
        hitl_dir = self.local_data / "hitl"
        if not hitl_dir.exists():
            return []
        out = []
        for p in sorted(hitl_dir.glob("*.json"), reverse=True)[:50]:
            try:
                row = json.loads(p.read_text(encoding="utf-8"))
                if row.get("status", "pending") == "pending":
                    out.append(row)
            except Exception:
                continue
        return out

    def _count_json(self, sub: str) -> int:
        if not self.local_data:
            return 0
        d = self.local_data / sub
        if not d.exists():
            return 0
        return len(list(d.glob("*.json")))

    def _local_metrics(self) -> dict[str, Any]:
        return {
            "activity_count": len(self._local_audit(100)),
            "pending_hitl": len(self._local_hitl()),
        }

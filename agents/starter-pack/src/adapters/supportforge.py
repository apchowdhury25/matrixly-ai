"""SupportForge adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import AgentAdapter


class SupportForgeAdapter(AgentAdapter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(agent_id="supportforge", name="SupportForge", **kwargs)

    def _local_metrics(self) -> dict[str, Any]:
        base = super()._local_metrics()
        tickets = self._count_json("tickets")
        sessions = self._count_json("sessions")
        base.update(
            {
                "tickets_handled": tickets,
                "sessions": sessions,
                "kb_docs": self._kb_docs(),
                "week_label": "tickets",
            }
        )
        return base

    def _kb_docs(self) -> int:
        if not self.local_data:
            return 0
        idx = self.local_data / "vector" / "index.json"
        if not idx.exists():
            # knowledge folder sibling
            kb = self.local_data.parent / "knowledge"
            if kb.exists():
                return len(list(kb.glob("*.md")))
            return 0
        try:
            import json

            data = json.loads(idx.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return int(data.get("documents") or data.get("count") or len(data.get("chunks") or []))
            if isinstance(data, list):
                return len(data)
        except Exception:
            pass
        return 0

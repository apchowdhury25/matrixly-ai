"""InvoiceForge adapter."""

from __future__ import annotations

from typing import Any

from .base import AgentAdapter


class InvoiceForgeAdapter(AgentAdapter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(agent_id="invoiceforge", name="InvoiceForge", **kwargs)

    def _local_metrics(self) -> dict[str, Any]:
        base = super()._local_metrics()
        invoices = self._count_json("invoices")
        base.update(
            {
                "invoices_processed": invoices,
                "exceptions": base.get("pending_hitl", 0),
                "week_label": "invoices",
            }
        )
        return base

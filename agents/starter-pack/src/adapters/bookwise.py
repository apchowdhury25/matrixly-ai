"""BookWise adapter."""

from __future__ import annotations

from typing import Any

from .base import AgentAdapter


class BookWiseAdapter(AgentAdapter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(agent_id="bookwise", name="BookWise", **kwargs)

    def _local_metrics(self) -> dict[str, Any]:
        base = super()._local_metrics()
        bookings = self._count_json("bookings")
        reminders = self._count_json("reminders")
        base.update(
            {
                "appointments_booked": bookings,
                "reminders": reminders,
                "week_label": "bookings",
            }
        )
        return base

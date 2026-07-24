"""Availability Agent — propose optimal slots."""

from __future__ import annotations

from ..integrations.calendar import CalendarService
from ..models import BookingState


def run_availability(state: BookingState, calendar: CalendarService) -> BookingState:
    proposals = calendar.propose_slots(
        service_id=state.service_id or "consult",
        preferred_date=state.preferred_date,
        preferred_time=state.preferred_time,
    )
    state.proposals = proposals
    state.add_audit(
        "availability",
        count=len(proposals),
        service_id=state.service_id,
        preferred_date=state.preferred_date,
    )
    return state

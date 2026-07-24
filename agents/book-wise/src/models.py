"""Pydantic models for BookWise."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "") -> str:
    u = uuid4().hex[:12]
    return f"{prefix}{u}" if prefix else u


class Channel(str, Enum):
    chat = "chat"
    email = "email"
    form = "form"
    api = "api"


class Intent(str, Enum):
    book = "book"
    reschedule = "reschedule"
    cancel = "cancel"
    availability = "availability"
    intake = "intake"
    status = "status"
    other = "other"


class BookingStatus(str, Enum):
    proposed = "proposed"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"
    pending_hitl = "pending_hitl"


class Customer(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    external_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    ts: str = Field(default_factory=utc_now)


class SlotProposal(BaseModel):
    start_iso: str
    end_iso: str
    label: str
    service_id: str = "consult"
    score: float = 1.0


class Booking(BaseModel):
    id: str
    status: BookingStatus = BookingStatus.confirmed
    service_id: str = "consult"
    service_name: str = "Consultation"
    start_iso: str
    end_iso: str
    timezone: str = "America/Chicago"
    customer: Customer = Field(default_factory=Customer)
    notes: str = ""
    intake: dict[str, Any] = Field(default_factory=dict)
    channel: str = "chat"
    session_id: Optional[str] = None
    calendar_event_id: Optional[str] = None
    confirmation_sent: bool = False
    reminders_scheduled: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSessionRequest(BaseModel):
    customer: Optional[Customer] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSessionResponse(BaseModel):
    session_id: str
    welcome: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    customer: Optional[Customer] = None
    channel: Channel = Channel.chat
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Optional structured picks from widget buttons
    selected_slot: Optional[str] = None  # start_iso
    service_id: Optional[str] = None
    booking_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    reply: str
    intent: Intent
    proposals: list[SlotProposal] = Field(default_factory=list)
    booking: Optional[Booking] = None
    requires_human: bool = False
    hitl_id: Optional[str] = None
    intake_missing: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


class FormWebhook(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_time: Optional[str] = None
    service_id: Optional[str] = None
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class BookRequest(BaseModel):
    start_iso: str
    service_id: str = "consult"
    customer: Customer
    notes: str = ""
    channel: Channel = Channel.api
    session_id: Optional[str] = None
    intake: dict[str, Any] = Field(default_factory=dict)


class RescheduleRequest(BaseModel):
    booking_id: str
    new_start_iso: str


class CancelRequest(BaseModel):
    booking_id: str
    reason: str = ""


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    booking_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None


class BookingState(BaseModel):
    """Orchestrator state."""

    message_id: str = Field(default_factory=lambda: new_id("msg_"))
    session_id: str = ""
    channel: Channel = Channel.chat
    customer: Customer = Field(default_factory=Customer)
    text: str = ""
    history: list[ChatMessage] = Field(default_factory=list)

    intent: Intent = Intent.other
    service_id: str = "consult"
    preferred_date: Optional[str] = None
    preferred_time: Optional[str] = None
    timezone: str = "America/Chicago"

    proposals: list[SlotProposal] = Field(default_factory=list)
    selected_slot: Optional[str] = None
    booking: Optional[Booking] = None
    booking_id: Optional[str] = None

    reply: str = ""
    requires_human: bool = False
    hitl_id: Optional[str] = None
    intake_missing: list[str] = Field(default_factory=list)
    edge_case: Optional[str] = None

    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_audit(self, event: str, **detail: Any) -> None:
        self.audit_events.append({"event": event, "ts": utc_now(), **detail})

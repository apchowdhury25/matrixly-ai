"""Pydantic models for ConnectForge."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid4().hex[:12]}"


class MessageDirection(str, Enum):
    inbound = "inbound"
    outbound = "outbound"


class MessageStatus(str, Enum):
    received = "received"
    queued = "queued"
    pending_approval = "pending_approval"
    sent = "sent"
    failed = "failed"
    delivered = "delivered"
    mocked = "mocked"


class ConnectionStatus(str, Enum):
    disconnected = "disconnected"
    trial = "trial"
    live = "live"
    mock = "mock"


class SmsMessage(BaseModel):
    id: str
    direction: MessageDirection
    from_number: str = ""
    to_number: str = ""
    body: str = ""
    status: MessageStatus = MessageStatus.queued
    twilio_sid: Optional[str] = None
    conversation_sid: Optional[str] = None
    error: Optional[str] = None
    trial_note: Optional[str] = None
    language: str = "en"
    hitl_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationThread(BaseModel):
    id: str
    conversation_sid: Optional[str] = None
    participant_number: str = ""
    messages: list[str] = Field(default_factory=list)  # message ids
    last_body: str = ""
    updated_at: str = Field(default_factory=utc_now)
    created_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CallRecord(BaseModel):
    id: str
    to_number: str
    from_number: str = ""
    status: str = "initiated"
    twilio_sid: Optional[str] = None
    error: Optional[str] = None
    note: str = ""
    created_at: str = Field(default_factory=utc_now)


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"  # pending | approved | rejected
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None


class SendSmsRequest(BaseModel):
    to: str
    body: str
    force_send: bool = False  # admin override after HITL approve path
    language: str = "en"
    conversation_sid: Optional[str] = None


class StartConversationRequest(BaseModel):
    to: str
    body: str = "Hi! Thanks for contacting us. How can we help today?"
    language: str = "en"


class VoiceCallRequest(BaseModel):
    to: str
    say: Optional[str] = None


class HitlDecision(BaseModel):
    action: str  # approve | reject
    decided_by: str = "owner"
    note: str = ""


class WebhookSmsForm(BaseModel):
    """Twilio form fields (partial)."""

    From: str = ""
    To: str = ""
    Body: str = ""
    MessageSid: str = ""
    AccountSid: str = ""

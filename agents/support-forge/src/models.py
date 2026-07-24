"""Pydantic models for SupportForge."""

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


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    angry = "angry"


class Topic(str, Enum):
    pricing = "pricing"
    hours = "hours"
    order = "order"
    policy = "policy"
    troubleshoot = "troubleshoot"
    other = "other"


class ActionType(str, Enum):
    auto_reply = "auto_reply"
    draft_for_approval = "draft_for_approval"
    escalate = "escalate"


class KbHit(BaseModel):
    chunk: str
    source: str
    score: float
    title: str = ""


class Customer(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    external_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # user | assistant | system
    content: str
    ts: str = Field(default_factory=utc_now)


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


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    reply: str
    action: ActionType
    confidence: float
    urgency: Urgency
    sentiment: Sentiment
    topic: Topic
    ticket_id: Optional[str] = None
    citations: list[KbHit] = Field(default_factory=list)
    requires_human: bool = False
    hitl_id: Optional[str] = None
    usage: dict[str, Any] = Field(default_factory=dict)


class FormWebhook(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    subject: Optional[str] = None
    message: str
    page_url: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmailWebhook(BaseModel):
    from_email: str
    from_name: Optional[str] = None
    subject: str = ""
    body: str
    message_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestMessage(BaseModel):
    channel: Channel = Channel.api
    text: str
    customer: Optional[Customer] = None
    subject: Optional[str] = None
    session_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TicketMessage(BaseModel):
    role: str
    content: str
    ts: str = Field(default_factory=utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)


class Ticket(BaseModel):
    id: str
    status: str = "open"  # open | pending | solved | closed | escalated
    priority: str = "normal"  # low | normal | high | urgent
    channel: str = "chat"
    subject: str = ""
    customer: Customer = Field(default_factory=Customer)
    messages: list[TicketMessage] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    assignee: Optional[str] = None
    confidence: Optional[float] = None
    topic: Optional[str] = None
    urgency: Optional[str] = None
    sentiment: Optional[str] = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HitlAction(BaseModel):
    id: str
    kind: str  # send_email | close_ticket | crm_update | publish_reply
    status: str = "pending"  # pending | approved | rejected
    payload: dict[str, Any] = Field(default_factory=dict)
    ticket_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None


class SupportState(BaseModel):
    """Orchestrator pipeline state (LangGraph-style)."""

    message_id: str = Field(default_factory=lambda: new_id("msg_"))
    session_id: str = ""
    channel: Channel = Channel.chat
    customer: Customer = Field(default_factory=Customer)
    text: str = ""
    subject: str = ""
    history: list[ChatMessage] = Field(default_factory=list)

    urgency: Urgency = Urgency.medium
    sentiment: Sentiment = Sentiment.neutral
    topic: Topic = Topic.other
    pii_flags: list[str] = Field(default_factory=list)
    escalate_reason: Optional[str] = None

    kb_hits: list[KbHit] = Field(default_factory=list)
    retrieval_confidence: float = 0.0

    answer: str = ""
    confidence: float = 0.0
    action: ActionType = ActionType.draft_for_approval

    ticket_id: Optional[str] = None
    hitl_id: Optional[str] = None
    requires_human: bool = False

    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_audit(self, event: str, **detail: Any) -> None:
        self.audit_events.append(
            {"event": event, "ts": utc_now(), **detail}
        )


class KbUpload(BaseModel):
    title: str = "uploaded"
    content: str
    source: str = "upload"

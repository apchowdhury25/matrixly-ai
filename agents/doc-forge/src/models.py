"""Pydantic models for DocForge."""

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


class DocType(str, Enum):
    proposal = "proposal"
    quote = "quote"
    contract = "contract"
    report = "report"


class DocStatus(str, Enum):
    received = "received"
    drafting = "drafting"
    brand_review = "brand_review"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    exported = "exported"
    sent = "sent"


class LineItem(BaseModel):
    sku: str = ""
    name: str = ""
    qty: float = 1
    unit_price: float = 0
    unit: str = ""


class ClientInfo(BaseModel):
    name: str = ""
    contact: str = ""
    email: str = ""
    company: str = ""
    industry: str = ""


class ProjectInfo(BaseModel):
    title: str = ""
    summary: str = ""
    goals: list[str] = Field(default_factory=list)
    timeline: str = ""
    constraints: list[str] = Field(default_factory=list)


class DocVersion(BaseModel):
    version: int
    status: str
    body_markdown: str = ""
    summary: str = ""
    created_at: str = Field(default_factory=utc_now)
    created_by: str = "system"
    note: str = ""
    export_paths: list[str] = Field(default_factory=list)


class Document(BaseModel):
    id: str
    doc_type: DocType = DocType.proposal
    status: DocStatus = DocStatus.received
    title: str = ""
    client: ClientInfo = Field(default_factory=ClientInfo)
    project: ProjectInfo = Field(default_factory=ProjectInfo)
    line_items: list[LineItem] = Field(default_factory=list)
    discount_pct: float = 0
    currency: str = "USD"
    body_markdown: str = ""
    summary: str = ""
    sections: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    quality_score: float = 0
    legal_block: str = ""
    pricing_totals: dict[str, Any] = Field(default_factory=dict)
    template_id: str = ""
    version: int = 1
    versions: list[DocVersion] = Field(default_factory=list)
    hitl_id: Optional[str] = None
    export_paths: list[str] = Field(default_factory=list)
    send_status: str = "not_sent"  # not_sent | queued | sent | failed
    sent_at: Optional[str] = None
    sent_to: list[str] = Field(default_factory=list)
    valid_through: str = ""

    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0

    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftRequest(BaseModel):
    doc_type: str = "proposal"
    client: dict[str, Any] = Field(default_factory=dict)
    project: dict[str, Any] = Field(default_factory=dict)
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    discount_pct: float = 0
    notes: str = ""
    template_id: str = ""
    source: str = "manual"  # manual | sample | crm
    crm_account: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SendRequest(BaseModel):
    document_id: str
    recipients: list[str] = Field(default_factory=list)
    note: str = ""


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    document_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None

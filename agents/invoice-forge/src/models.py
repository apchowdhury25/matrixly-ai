"""Pydantic models for InvoiceForge."""

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


class SourceChannel(str, Enum):
    upload = "upload"
    email = "email"
    api = "api"
    watch = "watch"


class InvoiceStatus(str, Enum):
    received = "received"
    extracted = "extracted"
    validated = "validated"
    exception = "exception"
    posted = "posted"
    paid = "paid"
    void = "void"
    pending_hitl = "pending_hitl"


class LineItem(BaseModel):
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    amount: float = 0.0


class Invoice(BaseModel):
    id: str
    status: InvoiceStatus = InvoiceStatus.received
    source: SourceChannel = SourceChannel.upload
    source_file: Optional[str] = None
    source_email: Optional[str] = None

    vendor_name: Optional[str] = None
    vendor_email: Optional[str] = None
    invoice_number: Optional[str] = None
    po_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    amount_due: Optional[float] = None
    line_items: list[LineItem] = Field(default_factory=list)

    confidence: float = 0.0
    extraction_method: str = "rules"  # rules | vision | llm_text
    raw_text: str = ""
    exceptions: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)

    posted_to: Optional[str] = None  # csv | quickbooks | xero
    external_id: Optional[str] = None
    export_path: Optional[str] = None

    ar_status: str = "open"  # open | reminded | paid | written_off
    reminders_sent: list[str] = Field(default_factory=list)

    hitl_id: Optional[str] = None
    notes: str = ""
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessResult(BaseModel):
    invoice: Invoice
    message: str = ""
    requires_human: bool = False
    usage: dict[str, Any] = Field(default_factory=dict)


class UploadMeta(BaseModel):
    filename: str = "invoice.txt"
    source: SourceChannel = SourceChannel.upload
    source_email: Optional[str] = None
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmailIngest(BaseModel):
    from_email: str
    from_name: Optional[str] = None
    subject: str = ""
    body: str = ""
    attachment_text: Optional[str] = None
    attachment_filename: Optional[str] = None


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    invoice_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None


class PipelineState(BaseModel):
    invoice_id: str = ""
    channel: SourceChannel = SourceChannel.upload
    text: str = ""
    image_path: Optional[str] = None
    filename: str = ""
    source_email: Optional[str] = None

    invoice: Optional[Invoice] = None
    requires_human: bool = False
    hitl_id: Optional[str] = None
    message: str = ""

    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_audit(self, event: str, **detail: Any) -> None:
        self.audit_events.append({"event": event, "ts": utc_now(), **detail})


class ReportSummary(BaseModel):
    total_invoices: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    exceptions: int = 0
    posted: int = 0
    open_ar_total: float = 0.0
    aging: dict[str, float] = Field(default_factory=dict)
    currency: str = "USD"

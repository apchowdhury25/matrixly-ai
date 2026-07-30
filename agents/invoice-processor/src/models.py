"""Core domain models for the Matrixly Invoice Processor.

Every agent emits structured Pydantic outputs — no free-form “trust me”
JSON blobs between stages. This keeps the multi-agent boundary explicit
and makes HITL UIs trivial to build later.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "inv_") -> str:
    return f"{prefix}{uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SourceType(str, Enum):
    pdf = "pdf"
    email = "email"
    text = "text"
    upload = "upload"
    api = "api"


class MatchStatus(str, Enum):
    matched = "matched"
    partial = "partial"
    no_po = "no_po"
    unmatched = "unmatched"


class DiscrepancyType(str, Enum):
    amount = "amount"
    quantity = "quantity"
    unit_price = "unit_price"
    vendor = "vendor"
    po_number = "po_number"
    line_item = "line_item"
    currency = "currency"
    tax = "tax"
    date = "date"
    missing_po = "missing_po"
    duplicate = "duplicate"
    other = "other"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ReviewAction(str, Enum):
    approve = "approve"
    needs_review = "needs_review"
    reject = "reject"


class ProcessingStatus(str, Enum):
    received = "received"
    extracting = "extracting"
    matching = "matching"
    reviewing = "reviewing"
    completed = "completed"
    failed = "failed"
    pending_hitl = "pending_hitl"


# ---------------------------------------------------------------------------
# Invoice domain
# ---------------------------------------------------------------------------


class InvoiceLineItem(BaseModel):
    """Single invoice line — maps cleanly to PO lines for 3-way match later."""

    line_number: int = 1
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    amount: float = 0.0
    sku: Optional[str] = None
    unit_of_measure: Optional[str] = None
    tax_amount: Optional[float] = None
    po_line_number: Optional[int] = None

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount(cls, v: Any, info: Any) -> Any:
        if v is None or v == "":
            return 0.0
        return v


class InvoiceData(BaseModel):
    """Structured invoice extracted from PDF or email."""

    invoice_id: str = Field(default_factory=lambda: new_id("inv_"))
    vendor_name: str = ""
    vendor_email: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    invoice_number: str = ""
    po_number: Optional[str] = None
    invoice_date: Optional[str] = None  # ISO date preferred
    due_date: Optional[str] = None
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    shipping: Optional[float] = None
    total: float = 0.0
    amount_due: Optional[float] = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    source_type: SourceType = SourceType.text
    source_ref: Optional[str] = None  # path, message-id, etc.
    raw_text_excerpt: str = ""
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_method: str = "unknown"  # llm | rules | hybrid
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PurchaseOrderLine(BaseModel):
    line_number: int = 1
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    amount: float = 0.0
    sku: Optional[str] = None
    received_qty: float = 0.0


class PurchaseOrder(BaseModel):
    """Purchase order record used for matching (in-memory or future ERP)."""

    po_number: str
    vendor_name: str = ""
    vendor_id: Optional[str] = None
    status: str = "open"  # open | closed | cancelled | partially_received
    currency: str = "USD"
    order_date: Optional[str] = None
    total: float = 0.0
    remaining_amount: Optional[float] = None
    line_items: list[PurchaseOrderLine] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Discrepancy(BaseModel):
    """A single mismatch between invoice and PO / business rules."""

    type: DiscrepancyType
    severity: Severity
    field: str
    description: str
    invoice_value: Optional[str] = None
    expected_value: Optional[str] = None
    delta: Optional[float] = None


class MatchingResult(BaseModel):
    """Output of InvoiceMatcherAgent."""

    status: MatchStatus
    matched_po: Optional[PurchaseOrder] = None
    match_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    summary: str = ""
    candidate_po_numbers: list[str] = Field(default_factory=list)
    rules_applied: list[str] = Field(default_factory=list)


class ReviewDecision(BaseModel):
    """Output of InvoiceReviewerAgent — final recommendation + HITL flags."""

    action: ReviewAction
    reasoning: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_human: bool = False
    hitl_reasons: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class InvoiceProcessingResult(BaseModel):
    """Final combined output returned by the orchestrator / pipeline."""

    processing_id: str = Field(default_factory=lambda: new_id("proc_"))
    status: ProcessingStatus = ProcessingStatus.completed
    invoice: InvoiceData
    matching: MatchingResult
    review: ReviewDecision
    requires_human: bool = False
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    agent_trace: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        # Keep top-level HITL flag aligned with reviewer
        if self.review and self.review.requires_human:
            object.__setattr__(self, "requires_human", True)
            if self.status == ProcessingStatus.completed and self.review.action == ReviewAction.needs_review:
                object.__setattr__(self, "status", ProcessingStatus.pending_hitl)


class InvoiceInput(BaseModel):
    """Inbound request envelope for the pipeline / orchestrator."""

    source_type: SourceType = SourceType.text
    text: Optional[str] = None
    pdf_path: Optional[str] = None
    email_message_id: Optional[str] = None
    email_raw: Optional[str] = None
    filename: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUsageSummary(BaseModel):
    stage: str
    model: Optional[str] = None
    notes: str = ""

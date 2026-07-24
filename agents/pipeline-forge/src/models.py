"""Pydantic models for PipelineForge."""

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


class RunStatus(str, Enum):
    received = "received"
    scoring = "scoring"
    prioritizing = "prioritizing"
    risk_review = "risk_review"
    crm_mapped = "crm_mapped"
    pending_review = "pending_review"
    applied = "applied"
    rejected = "rejected"


class Opportunity(BaseModel):
    id: str
    name: str = ""
    account: str = ""
    amount: float = 0.0
    currency: str = "USD"
    stage: str = "lead"
    owner: str = ""
    contact_title: str = ""
    industry: str = ""
    employees: str = ""
    source: str = ""
    last_activity_days: int = 0
    signals: list[str] = Field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoreCard(BaseModel):
    opportunity_id: str
    score: float = 0.0
    fit: float = 0.0
    engagement: float = 0.0
    behavior: float = 0.0
    urgency: float = 0.0
    tier: str = "cold"  # hot | warm | cold
    rationale: str = ""
    at_risk: bool = False


class PriorityItem(BaseModel):
    rank: int
    opportunity_id: str
    rep: str = ""
    why: str = ""
    next_action: str = ""
    due: str = "today"
    score: float = 0.0
    name: str = ""


class RiskFlag(BaseModel):
    opportunity_id: str
    risk_level: str = "medium"
    reasons: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    suggested_stage: Optional[str] = None
    name: str = ""


class CrmUpdate(BaseModel):
    opportunity_id: str
    action: str = "add_note"  # update_stage | create_task | add_note
    stage: Optional[str] = None
    task_subject: Optional[str] = None
    note: Optional[str] = None
    confidence: float = 0.5
    applied: bool = False
    result: dict[str, Any] = Field(default_factory=dict)


class PipelineRun(BaseModel):
    id: str
    status: RunStatus = RunStatus.received
    cadence: str = "daily"
    opportunities: list[Opportunity] = Field(default_factory=list)
    scores: list[ScoreCard] = Field(default_factory=list)
    priority_list: list[PriorityItem] = Field(default_factory=list)
    risks: list[RiskFlag] = Field(default_factory=list)
    crm_updates: list[CrmUpdate] = Field(default_factory=list)
    insights: dict[str, Any] = Field(default_factory=dict)
    list_title: str = ""
    notes: str = ""
    hitl_id: Optional[str] = None
    export_paths: list[str] = Field(default_factory=list)

    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0

    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    opportunities: list[dict[str, Any]] = Field(default_factory=list)
    # empty → load samples/pipeline.json or CRM
    cadence: str = "daily"
    source: str = "payload"  # payload | sample | crm
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApplyCrmRequest(BaseModel):
    run_id: str
    update_indexes: list[int] = Field(default_factory=list)  # empty = all


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    run_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None

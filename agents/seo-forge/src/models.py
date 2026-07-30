"""Pydantic models for SEOForge."""

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


class JobStatus(str, Enum):
    received = "received"
    researching = "researching"
    planning = "planning"
    writing = "writing"
    auditing = "auditing"
    pending_review = "pending_review"
    approved = "approved"
    scheduled = "scheduled"
    published = "published"
    rejected = "rejected"


class SeoJob(BaseModel):
    id: str
    status: JobStatus = JobStatus.received
    kind: str = "content"  # content | plan | audit | local | chat
    title: str = ""
    source_text: str = ""
    goal: str = ""
    business_type: str = ""
    service_areas: list[str] = Field(default_factory=list)
    content_type: str = "blog"

    research: dict[str, Any] = Field(default_factory=dict)
    plan: dict[str, Any] = Field(default_factory=dict)
    draft: dict[str, Any] = Field(default_factory=dict)
    local: dict[str, Any] = Field(default_factory=dict)
    audit: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, Any] = Field(default_factory=dict)
    roi_snapshot: dict[str, Any] = Field(default_factory=dict)

    quality_score: float = 0.0
    confidence: float = 0.0
    hitl_id: Optional[str] = None
    export_paths: list[str] = Field(default_factory=list)
    scheduled_at: Optional[str] = None
    published_to: list[str] = Field(default_factory=list)

    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0

    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str  # user | assistant | system
    content: str
    ts: str = Field(default_factory=utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    profile: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    profile: dict[str, Any] = Field(default_factory=dict)


class OnboardRequest(BaseModel):
    business_type: str = ""
    service_areas: list[str] = Field(default_factory=list)
    website: str = ""
    gbp_status: str = ""
    primary_goal: str = "organic_leads"
    business_name: str = ""
    notes: str = ""


class PlanRequest(BaseModel):
    business_input: str
    primary_goal: str = "organic_leads"
    service_areas: list[str] = Field(default_factory=list)
    business_type: str = ""


class GenerateRequest(BaseModel):
    brief: str
    content_type: str = "blog"
    primary_keyword: str = ""
    service_areas: list[str] = Field(default_factory=list)
    goal: str = ""
    title: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditRequest(BaseModel):
    page_text: str
    url_or_title: str = ""
    primary_keyword: str = ""


class LocalSeoRequest(BaseModel):
    business_input: str
    service_areas: list[str] = Field(default_factory=list)
    gbp_notes: str = ""


class KeywordItem(BaseModel):
    keyword: str
    intent: str = "local"
    priority: str = "medium"
    current_rank: Optional[int] = None
    previous_rank: Optional[int] = None
    city: str = ""
    notes: str = ""
    status: str = "tracking"  # tracking | won | paused


class KeywordUpsert(BaseModel):
    keywords: list[KeywordItem]


class BrandVoiceUpdate(BaseModel):
    voice_markdown: str
    tone: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class RoiEvent(BaseModel):
    hours_saved: float = 0.0
    leads_attributed: int = 0
    revenue_usd: float = 0.0
    note: str = ""
    job_id: Optional[str] = None


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    job_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None


class PublishRequest(BaseModel):
    job_id: str
    targets: list[str] = Field(default_factory=lambda: ["local"])


class ScheduleRequest(BaseModel):
    job_id: str
    run_at: str
    channel: str = "blog"

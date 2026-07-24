"""Pydantic models for ContentForge."""

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
    writing = "writing"
    editing = "editing"
    repurposing = "repurposing"
    pending_review = "pending_review"
    approved = "approved"
    scheduled = "scheduled"
    published = "published"
    rejected = "rejected"


class ContentJob(BaseModel):
    id: str
    status: JobStatus = JobStatus.received
    source_title: str = ""
    source_text: str = ""
    goal: str = ""
    audience: str = ""

    research: dict[str, Any] = Field(default_factory=dict)
    draft: dict[str, Any] = Field(default_factory=dict)
    edited: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, Any] = Field(default_factory=dict)

    quality_score: float = 0.0
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


class GenerateRequest(BaseModel):
    source_text: str
    source_title: str = ""
    goal: str = "Educate SMBs and drive agent marketplace signups"
    audience: str = ""
    formats: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdeaRequest(BaseModel):
    business_input: str
    count: int = 5
    channel: str = "mixed"


class ScheduleRequest(BaseModel):
    job_id: str
    channel: str = "blog"
    run_at: str  # ISO
    content_key: str = "blog"  # blog | linkedin | newsletter


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
    # targets: local | buffer | hootsuite | wordpress

"""Pydantic models for SocialForge."""

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


class PostStatus(str, Enum):
    draft = "draft"
    scheduled = "scheduled"
    pending_review = "pending_review"
    approved = "approved"
    published = "published"
    rejected = "rejected"
    failed = "failed"


class CampaignStatus(str, Enum):
    received = "received"
    composing = "composing"
    scheduling = "scheduling"
    pending_review = "pending_review"
    approved = "approved"
    partially_published = "partially_published"
    published = "published"
    rejected = "rejected"


class PlatformPost(BaseModel):
    platform: str
    text: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""
    thread: list[str] = Field(default_factory=list)
    media_suggestions: list[str] = Field(default_factory=list)
    status: PostStatus = PostStatus.draft
    scheduled_at: Optional[str] = None
    published_at: Optional[str] = None
    publish_result: dict[str, Any] = Field(default_factory=dict)
    schedule_reason: str = ""


class Campaign(BaseModel):
    id: str
    status: CampaignStatus = CampaignStatus.received
    idea: str = ""
    theme: str = ""
    platforms: list[str] = Field(default_factory=list)
    posts: dict[str, PlatformPost] = Field(default_factory=dict)
    schedule: list[dict[str, Any]] = Field(default_factory=list)
    media_suggestions: list[str] = Field(default_factory=list)
    notes: str = ""
    hitl_id: Optional[str] = None
    export_paths: list[str] = Field(default_factory=list)

    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0

    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InboxItem(BaseModel):
    id: str
    platform: str = "x"
    kind: str = "comment"  # mention | comment | dm | review
    author: str = ""
    text: str = ""
    sentiment: str = "neutral"
    priority: str = "normal"
    needs_reply: bool = True
    topic: str = ""
    draft_reply: str = ""
    reply_tone: str = ""
    escalate: bool = False
    status: str = "open"  # open | draft_ready | pending_review | replied | dismissed
    hitl_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InsightsReport(BaseModel):
    id: str
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    metrics_snapshot: dict[str, Any] = Field(default_factory=dict)
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    next_week_themes: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class ComposeRequest(BaseModel):
    idea: str
    platforms: list[str] = Field(default_factory=list)
    theme: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScheduleRequest(BaseModel):
    campaign_id: str
    platform: str
    run_at: str  # ISO


class PublishRequest(BaseModel):
    campaign_id: str
    platforms: list[str] = Field(default_factory=list)
    backend: str = ""  # override: local | buffer | meta | linkedin


class MonitorRequest(BaseModel):
    raw_items: list[dict[str, Any]] = Field(default_factory=list)
    # if empty, use demo inbox seed


class ReplyRequest(BaseModel):
    inbox_ids: list[str] = Field(default_factory=list)


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    campaign_id: Optional[str] = None
    inbox_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None

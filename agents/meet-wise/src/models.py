"""Pydantic models for MeetWise."""

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


class MeetingStatus(str, Enum):
    received = "received"
    summarized = "summarized"
    actions_extracted = "actions_extracted"
    crm_mapped = "crm_mapped"
    recap_drafted = "recap_drafted"
    pending_review = "pending_review"
    applied = "applied"
    rejected = "rejected"


class Platform(str, Enum):
    upload = "upload"
    zoom = "zoom"
    teams = "teams"
    google = "google"
    other = "other"


class ActionItem(BaseModel):
    description: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: str = "normal"
    source_quote: str = ""
    flagged: bool = False


class Meeting(BaseModel):
    id: str
    status: MeetingStatus = MeetingStatus.received
    platform: Platform = Platform.upload
    title: str = ""
    meeting_date: Optional[str] = None
    participants: list[str] = Field(default_factory=list)
    transcript: str = ""
    source_file: Optional[str] = None

    summary: str = ""
    decisions: list[str] = Field(default_factory=list)
    discussion_points: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_meeting: Optional[str] = None

    action_items: list[ActionItem] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)

    crm_payload: dict[str, Any] = Field(default_factory=dict)
    recap_subject: str = ""
    recap_body: str = ""

    hitl_id: Optional[str] = None
    export_paths: list[str] = Field(default_factory=list)
    crm_applied: bool = False
    email_sent: bool = False

    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0

    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessRequest(BaseModel):
    transcript: str
    title: str = ""
    platform: Platform = Platform.upload
    meeting_date: Optional[str] = None
    participants: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    meeting_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None

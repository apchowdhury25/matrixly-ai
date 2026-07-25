"""Pydantic models for Starter Pack."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid4().hex[:12]}"


class AgentCard(BaseModel):
    id: str
    name: str
    description: str = ""
    tile: str = ""
    category: str = ""
    enabled: bool = True
    online: bool = False
    url: str = ""
    health: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    widget_url: str = ""
    panel_url: str = ""


class ActivityItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("act_"))
    agent_id: str
    agent_name: str = ""
    event: str
    detail: dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(default_factory=utc_now)


class PackSettings(BaseModel):
    agents_enabled: dict[str, bool] = Field(
        default_factory=lambda: {
            "supportforge": True,
            "bookwise": True,
            "invoiceforge": True,
        }
    )
    connections: dict[str, Any] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=utc_now)


class SettingsUpdate(BaseModel):
    agents_enabled: dict[str, bool] | None = None
    connections: dict[str, Any] | None = None


class OverviewResponse(BaseModel):
    pack: str
    version: str
    business: dict[str, Any] = Field(default_factory=dict)
    agents: list[AgentCard] = Field(default_factory=list)
    analytics: dict[str, Any] = Field(default_factory=dict)
    activity: list[ActivityItem] = Field(default_factory=list)
    pending_hitl: int = 0
    generated_at: str = Field(default_factory=utc_now)

"""CRM domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class Contact:
    email: str
    id: str = ""
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    title: str = ""
    phone: str = ""
    company_id: str = ""
    company_name: str = ""
    owner: str = ""
    source: str = ""
    tags: list[str] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        self.email = (self.email or "").strip().lower()
        if not self.id:
            self.id = _id("con")
        if not self.full_name:
            self.full_name = f"{self.first_name} {self.last_name}".strip()
        if not self.created_at:
            self.created_at = _now()
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Contact:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class Company:
    name: str
    id: str = ""
    domain: str = ""
    industry: str = ""
    owner: str = ""
    employee_count: int | None = None
    website: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = _id("co")
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Company:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class Deal:
    name: str
    id: str = ""
    stage: str = "Qualification"
    amount: float | None = None
    contact_email: str = ""
    company_name: str = ""
    owner: str = ""
    next_step: str = ""
    close_date: str = ""
    last_activity_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = _id("deal")
        self.updated_at = _now()
        if not self.last_activity_at:
            self.last_activity_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Deal:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class Activity:
    type: str  # email | call | meeting | note | task
    subject: str
    id: str = ""
    body: str = ""
    contact_email: str = ""
    deal_id: str = ""
    owner: str = ""
    occurred_at: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = _id("act")
        if not self.occurred_at:
            self.occurred_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Activity:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class ProposedWrite:
    """HITL unit — proposed CRM mutation."""

    action: str  # upsert_contact | log_activity | upsert_deal | patch_fields
    payload: dict[str, Any]
    id: str = ""
    reason: str = ""
    confidence: float = 0.0
    status: str = "pending"  # pending | approved | rejected | applied
    diffs: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = _id("wrt")
        if not self.created_at:
            self.created_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProposedWrite:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class HygieneIssue:
    entity_type: str
    entity_id: str
    severity: str  # high | medium | low
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

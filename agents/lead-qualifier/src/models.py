"""Lead data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Lead:
    email: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    company: str = ""
    title: str = ""
    phone: str = ""
    website: str = ""
    industry: str = ""
    employee_count: int | None = None
    city: str = ""
    state: str = ""
    country: str = ""
    source: str = ""
    notes: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.email = (self.email or "").strip().lower()
        if not self.full_name:
            self.full_name = f"{self.first_name} {self.last_name}".strip()
        if self.full_name and not (self.first_name or self.last_name):
            parts = self.full_name.split(None, 1)
            self.first_name = parts[0] if parts else ""
            self.last_name = parts[1] if len(parts) > 1 else ""

    @property
    def domain(self) -> str:
        if "@" not in self.email:
            return ""
        return self.email.split("@", 1)[1].lower()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["domain"] = self.domain
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lead:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        raw = {k: v for k, v in data.items() if k not in known}
        lead = cls(**kwargs)
        lead.raw = {**raw, **(lead.raw or {})}
        return lead


@dataclass
class Enrichment:
    company: str = ""
    industry: str = ""
    website: str = ""
    linkedin_guess: str = ""
    employee_band: str = ""
    location_guess: str = ""
    is_free_email: bool = False
    domain: str = ""
    signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    provider: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreResult:
    score: float
    tier: str  # hot | warm | cold | disqualified
    fit: float
    intent: float
    seniority: float
    data_quality: float
    reasons: list[str] = field(default_factory=list)
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutreachTouch:
    day: int
    channel: str
    subject: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualifiedLead:
    lead: Lead
    enrichment: Enrichment
    score: ScoreResult
    sequence: list[OutreachTouch] = field(default_factory=list)
    salesforce_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lead": self.lead.to_dict(),
            "enrichment": self.enrichment.to_dict(),
            "score": self.score.to_dict(),
            "sequence": [t.to_dict() for t in self.sequence],
            "salesforce_payload": self.salesforce_payload,
        }

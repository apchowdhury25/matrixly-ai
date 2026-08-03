"""Pydantic models for SEO-Bespoke."""

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


# ── Quiz & profile ──────────────────────────────────────────────────────────


class SeoMaturity(str, Enum):
    none = "none"  # no SEO yet
    basic = "basic"  # website + occasional posts
    intermediate = "intermediate"  # tracking some keywords, GBP active
    advanced = "advanced"  # content calendar, tools, agency or in-house


class PrimaryGoal(str, Enum):
    near_me_leads = "near_me_leads"
    organic_leads = "organic_leads"
    ecommerce = "ecommerce"
    brand_authority = "brand_authority"
    local_dominance = "local_dominance"
    content_engine = "content_engine"


class DomainAnswers(BaseModel):
    """Collector N2 — website / domain."""

    domain: str = ""
    website_url: str = ""
    has_blog: bool = False
    has_gbp: bool = False  # Google Business Profile
    cms: str = ""  # wordpress | shopify | squarespace | wix | custom | unknown
    notes: str = ""


class IndustryAnswers(BaseModel):
    """Collector N3 — industry / niche."""

    industry: str = ""
    niche: str = ""
    sub_niches: list[str] = Field(default_factory=list)
    competitors_mentioned: list[str] = Field(default_factory=list)
    notes: str = ""


class BusinessAnswers(BaseModel):
    """Collector N4 — business description & unique value."""

    business_name: str = ""
    description: str = ""
    unique_value: str = ""
    products_services: list[str] = Field(default_factory=list)
    years_in_business: Optional[int] = None
    differentiators: list[str] = Field(default_factory=list)
    notes: str = ""


class CustomersAnswers(BaseModel):
    """Collector N5 — target customers / personas."""

    primary_persona: str = ""
    secondary_personas: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    buying_triggers: list[str] = Field(default_factory=list)
    decision_makers: str = ""
    notes: str = ""


class LocationAnswers(BaseModel):
    """Collector N6 — primary location(s) + service area."""

    primary_city: str = ""
    primary_region: str = ""  # state / metro
    country: str = "US"
    service_areas: list[str] = Field(default_factory=list)
    service_radius_miles: Optional[int] = None
    serves_nationally: bool = False
    notes: str = ""


class GoalsAnswers(BaseModel):
    """Collector N7 — SEO maturity & goals."""

    maturity: SeoMaturity = SeoMaturity.basic
    primary_goal: PrimaryGoal = PrimaryGoal.organic_leads
    secondary_goals: list[str] = Field(default_factory=list)
    monthly_content_capacity: str = "2-4 pieces"  # owner-friendly
    budget_band: str = "starter"  # starter | growth | scale
    success_metric: str = "more qualified inquiries"
    timeline_days: int = 90
    notes: str = ""


class QuizAnswers(BaseModel):
    """Full multi-step quiz payload (all collectors)."""

    domain: DomainAnswers = Field(default_factory=DomainAnswers)
    industry: IndustryAnswers = Field(default_factory=IndustryAnswers)
    business: BusinessAnswers = Field(default_factory=BusinessAnswers)
    customers: CustomersAnswers = Field(default_factory=CustomersAnswers)
    location: LocationAnswers = Field(default_factory=LocationAnswers)
    goals: GoalsAnswers = Field(default_factory=GoalsAnswers)
    owner_email: str = ""
    owner_name: str = ""
    raw_notes: str = ""


class BusinessSeoProfile(BaseModel):
    """Clean, professional Business SEO Profile Summary."""

    id: str
    version: int = 1
    business_name: str
    tagline: str = ""
    website: str = ""
    domain: str = ""
    industry: str = ""
    niche: str = ""
    description: str = ""
    unique_value: str = ""
    products_services: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    personas: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    primary_location: str = ""
    service_areas: list[str] = Field(default_factory=list)
    seo_maturity: str = "basic"
    primary_goal: str = "organic_leads"
    secondary_goals: list[str] = Field(default_factory=list)
    success_metric: str = ""
    timeline_days: int = 90
    recommended_focus: list[str] = Field(default_factory=list)
    seed_keywords: list[dict[str, str]] = Field(default_factory=list)
    brand_voice_notes: str = ""
    safety_rules: list[str] = Field(default_factory=list)
    summary_markdown: str = ""
    quiz_snapshot: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Graph run ───────────────────────────────────────────────────────────────


class NodeStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class GraphNodeResult(BaseModel):
    node_id: str
    name: str
    status: NodeStatus = NodeStatus.pending
    inputs_keys: list[str] = Field(default_factory=list)
    output: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: int = 0
    isolation: str = "pure_function"


class RunStatus(str, Enum):
    received = "received"
    quiz_collecting = "quiz_collecting"
    synthesizing = "synthesizing"
    verifying_profile = "verifying_profile"
    architecting = "architecting"
    generating_code = "generating_code"
    assembling = "assembling"
    safety_check = "safety_check"
    packaging = "packaging"
    smoke_testing = "smoke_testing"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    failed = "failed"
    completed = "completed"


class GraphRun(BaseModel):
    """One full parallel-graph execution: quiz → profile → custom agent package."""

    id: str
    status: RunStatus = RunStatus.received
    quiz: QuizAnswers = Field(default_factory=QuizAnswers)
    profile: Optional[BusinessSeoProfile] = None
    architecture: dict[str, Any] = Field(default_factory=dict)
    generated_modules: dict[str, Any] = Field(default_factory=dict)
    package: dict[str, Any] = Field(default_factory=dict)
    node_results: list[GraphNodeResult] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, Any] = Field(default_factory=dict)
    smoke: dict[str, Any] = Field(default_factory=dict)
    hitl_id: Optional[str] = None
    package_path: Optional[str] = None
    profile_path: Optional[str] = None
    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0
    graph_edges: list[dict[str, str]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Keywords / ROI / HITL ───────────────────────────────────────────────────


class KeywordItem(BaseModel):
    keyword: str
    intent: str = "local"
    priority: str = "medium"
    current_rank: Optional[int] = None
    previous_rank: Optional[int] = None
    city: str = ""
    notes: str = ""
    status: str = "tracking"
    profile_id: str = ""


class KeywordUpsert(BaseModel):
    keywords: list[KeywordItem]


class RoiEvent(BaseModel):
    hours_saved: float = 0.0
    leads_attributed: int = 0
    revenue_usd: float = 0.0
    note: str = ""
    run_id: Optional[str] = None
    profile_id: Optional[str] = None


class HitlAction(BaseModel):
    id: str
    kind: str
    status: str = "pending"  # pending | approved | rejected
    payload: dict[str, Any] = Field(default_factory=dict)
    run_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None


class HitlDecision(BaseModel):
    action: str  # approve | reject
    decided_by: str = "owner"
    note: str = ""


# ── API request bodies ──────────────────────────────────────────────────────


class QuizStartRequest(BaseModel):
    owner_name: str = ""
    owner_email: str = ""


class QuizStepRequest(BaseModel):
    run_id: str
    step: str  # domain | industry | business | customers | location | goals
    answers: dict[str, Any] = Field(default_factory=dict)


class QuizSubmitRequest(BaseModel):
    """Submit full quiz at once (API / CLI)."""

    answers: QuizAnswers
    regenerate: bool = False  # re-run generation for existing profile context
    profile_id: Optional[str] = None


class GeneratePackageRequest(BaseModel):
    run_id: Optional[str] = None
    profile_id: Optional[str] = None
    answers: Optional[QuizAnswers] = None


class BrandVoiceUpdate(BaseModel):
    voice_markdown: str
    tone: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    profile_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    ts: str = Field(default_factory=utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    profile_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)

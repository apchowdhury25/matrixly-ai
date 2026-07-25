"""Models for ETF Portfolio Analyzer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid4().hex[:12]}"


class MarketSnapshot(BaseModel):
    ticker: str
    name: str = ""
    currency: str = "USD"
    price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    market_cap: Optional[float] = None
    total_assets: Optional[float] = None
    expense_ratio: Optional[float] = None
    nav: Optional[float] = None
    yield_ttm: Optional[float] = None
    dividend_rate: Optional[float] = None
    dividend_yield: Optional[float] = None
    trailing_annual_dividend_rate: Optional[float] = None
    category: str = ""
    data_quality: str = "live"  # live | partial | fallback_sample | delayed
    notes: list[str] = Field(default_factory=list)
    source: str = "yahoo"
    fetched_at: str = Field(default_factory=utc_now)
    raw: dict[str, Any] = Field(default_factory=dict)


class YieldSection(BaseModel):
    ttm_yield_pct: Optional[float] = None
    latest_distribution: Optional[float] = None
    frequency: str = "unknown"
    annualized_projected_yield_pct: Optional[float] = None
    context: list[str] = Field(default_factory=list)


class NavSection(BaseModel):
    nav: Optional[float] = None
    price: Optional[float] = None
    premium_discount_pct: Optional[float] = None
    notes: list[str] = Field(default_factory=list)


class TaxSection(BaseModel):
    distribution_character: list[str] = Field(default_factory=list)
    tax_efficiency: str = ""
    account_fit: str = ""
    caveats: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    id: str
    ticker: str
    is_default_sample: bool = False
    as_of: str = Field(default_factory=today_str)
    snapshot: MarketSnapshot
    yield_section: YieldSection = Field(default_factory=YieldSection)
    nav_section: NavSection = Field(default_factory=NavSection)
    tax_section: TaxSection = Field(default_factory=TaxSection)
    takeaway: str = ""
    markdown: str = ""
    notion_page_id: Optional[str] = None
    notion_url: Optional[str] = None
    usage_tokens_in: int = 0
    usage_tokens_out: int = 0
    estimated_cost_usd: float = 0.0
    created_at: str = Field(default_factory=utc_now)


class AnalyzeRequest(BaseModel):
    ticker: str = ""
    save_to_notion: bool = False


class ChatRequest(BaseModel):
    message: str = ""
    session_id: str = ""
    save_to_notion: bool = False


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    report: Optional[AnalysisReport] = None

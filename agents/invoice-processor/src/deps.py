"""Dependency injection container for all agents.

Shared resources (PO store, PDF tools, email client, accounting connector,
business rules) live here so specialists stay pure and testable.

Swap stub connectors for real Gmail / QuickBooks / NetSuite later by
replacing the factory methods — agents do not change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

from .connectors.accounting import AccountingConnector, StubAccountingConnector
from .connectors.email_client import EmailClient, StubEmailClient
from .tools.pdf import PdfExtractor
from .tools.po_store import PurchaseOrderStore

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _load_yaml_config() -> dict[str, Any]:
    path = ROOT / "config.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class BusinessRules:
    """Review / match thresholds loaded from config + env."""

    default_currency: str = "USD"
    vendor_similarity_min: float = 0.72
    po_number_exact: bool = True
    amount_tolerance_pct: float = 2.0
    amount_tolerance_abs: float = 1.0
    qty_tolerance: float = 0.0
    amount_review_threshold: float = 10_000.0
    min_extract_confidence: float = 0.75
    min_match_confidence: float = 0.70
    auto_approve_when_clean: bool = True
    require_hitl_on_high_severity: bool = True
    hitl_auto_approve: bool = False


@dataclass
class InvoiceProcessorDeps:
    """Injected into every agent via RunContext[InvoiceProcessorDeps]."""

    po_store: PurchaseOrderStore
    pdf: PdfExtractor
    email: EmailClient
    accounting: AccountingConnector
    rules: BusinessRules = field(default_factory=BusinessRules)
    model_name: str = "xai:grok-4.5"
    data_dir: Path = field(default_factory=lambda: DATA)
    raw_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        po_store: Optional[PurchaseOrderStore] = None,
        pdf: Optional[PdfExtractor] = None,
        email: Optional[EmailClient] = None,
        accounting: Optional[AccountingConnector] = None,
        model_name: Optional[str] = None,
    ) -> "InvoiceProcessorDeps":
        load_dotenv(ROOT / ".env")
        cfg = _load_yaml_config()
        matching = cfg.get("matching") or {}
        review = cfg.get("review") or {}
        business = cfg.get("business") or {}
        model_cfg = cfg.get("model") or {}

        rules = BusinessRules(
            default_currency=os.getenv("CURRENCY_DEFAULT")
            or business.get("default_currency")
            or "USD",
            vendor_similarity_min=float(matching.get("vendor_similarity_min", 0.72)),
            po_number_exact=bool(matching.get("po_number_exact", True)),
            amount_tolerance_pct=float(matching.get("amount_tolerance_pct", 2.0)),
            amount_tolerance_abs=float(matching.get("amount_tolerance_abs", 1.0)),
            qty_tolerance=float(matching.get("qty_tolerance", 0.0)),
            amount_review_threshold=float(
                os.getenv("AMOUNT_REVIEW_THRESHOLD")
                or review.get("amount_review_threshold", 10_000)
            ),
            min_extract_confidence=float(review.get("min_extract_confidence", 0.75)),
            min_match_confidence=float(review.get("min_match_confidence", 0.70)),
            auto_approve_when_clean=bool(review.get("auto_approve_when_clean", True)),
            require_hitl_on_high_severity=bool(
                review.get("require_hitl_on_high_severity", True)
            ),
            hitl_auto_approve=os.getenv("HITL_AUTO_APPROVE", "false").lower()
            in {"1", "true", "yes"},
        )

        preferred = (
            model_name
            or os.getenv("INVOICE_PROCESSOR_MODEL")
            or model_cfg.get("preferred")
            or "xai:grok-4.5"
        )

        store = po_store or PurchaseOrderStore(DATA / "pos")
        store.ensure_seed_data()

        return cls(
            po_store=store,
            pdf=pdf or PdfExtractor(),
            email=email or StubEmailClient(),
            accounting=accounting or StubAccountingConnector(),
            rules=rules,
            model_name=preferred,
            data_dir=DATA,
            raw_config=cfg,
        )

    def model_available(self) -> bool:
        """True when an API key is present for the configured provider."""
        if os.getenv("XAI_API_KEY") or os.getenv("OPENAI_API_KEY"):
            return True
        # Native xAI key alias used by some pydantic-ai builds
        if os.getenv("GROK_API_KEY"):
            return True
        return False

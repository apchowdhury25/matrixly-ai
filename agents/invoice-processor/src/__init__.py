"""Matrixly Invoice Processor — Pydantic AI multi-agent AP system.

Architecture
------------
Three specialist agents + one orchestrator:

1. InvoiceExtractorAgent  — PDF/email → InvoiceData
2. InvoiceMatcherAgent    — InvoiceData + PO store → MatchingResult
3. InvoiceReviewerAgent   — match + rules → ReviewDecision (HITL-aware)
4. InvoiceOrchestrator    — coordinates specialists as tools / pipeline

Design goals: strong typing, async-first, dependency injection,
structured outputs, and connectors that can swap stubs for Gmail /
QuickBooks / NetSuite later without rewriting agent logic.
"""

from .models import (
    Discrepancy,
    InvoiceData,
    InvoiceLineItem,
    InvoiceProcessingResult,
    MatchingResult,
    PurchaseOrder,
    ReviewDecision,
)
from .pipeline import process_invoice

__version__ = "1.0.0"
__all__ = [
    "Discrepancy",
    "InvoiceData",
    "InvoiceLineItem",
    "InvoiceProcessingResult",
    "MatchingResult",
    "PurchaseOrder",
    "ReviewDecision",
    "process_invoice",
    "__version__",
]

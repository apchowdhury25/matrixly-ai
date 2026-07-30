"""Deterministic review policy for InvoiceReviewerAgent tools / fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    InvoiceData,
    MatchingResult,
    MatchStatus,
    ReviewAction,
    ReviewDecision,
    Severity,
)

if TYPE_CHECKING:
    from ..deps import BusinessRules


def decide_review(
    invoice: InvoiceData,
    matching: MatchingResult,
    rules: "BusinessRules",
) -> ReviewDecision:
    hitl: list[str] = []
    risks: list[str] = []
    next_actions: list[str] = []
    conf = min(invoice.extraction_confidence, matching.match_confidence or 0.5)

    high_sev = [
        d
        for d in matching.discrepancies
        if d.severity in {Severity.high, Severity.critical}
    ]
    critical = [d for d in matching.discrepancies if d.severity == Severity.critical]

    if invoice.extraction_confidence < rules.min_extract_confidence:
        hitl.append(
            f"Extraction confidence {invoice.extraction_confidence:.2f} "
            f"below {rules.min_extract_confidence:.2f}"
        )
    if matching.match_confidence < rules.min_match_confidence:
        hitl.append(
            f"Match confidence {matching.match_confidence:.2f} "
            f"below {rules.min_match_confidence:.2f}"
        )
    if matching.status in {MatchStatus.no_po, MatchStatus.unmatched}:
        hitl.append(f"Match status is {matching.status.value}")
        risks.append("Cannot safely pay without valid PO linkage")
    if high_sev and rules.require_hitl_on_high_severity:
        hitl.append(f"{len(high_sev)} high/critical discrepancy(ies)")
    if float(invoice.total or 0) >= rules.amount_review_threshold:
        hitl.append(
            f"Invoice total ${invoice.total:.2f} ≥ review threshold "
            f"${rules.amount_review_threshold:.2f}"
        )
        risks.append("High-value invoice")

    if critical:
        action = ReviewAction.reject if any(
            d.type.value in {"duplicate"} for d in critical
        ) else ReviewAction.needs_review
        # Prefer needs_review over hard reject unless explicit fraud/duplicate
        if not any(d.type.value == "duplicate" for d in critical):
            action = ReviewAction.needs_review
        reasoning = (
            "Critical discrepancies or missing PO prevent automatic approval. "
            + matching.summary
        )
        next_actions = [
            "Open HITL queue and verify PO with procurement",
            "Contact vendor if amount/qty error confirmed",
            "Do not schedule payment until resolved",
        ]
        requires_human = True
    elif hitl:
        action = ReviewAction.needs_review
        reasoning = (
            "Invoice requires human review: " + "; ".join(hitl) + ". " + matching.summary
        )
        next_actions = [
            "Review discrepancies in AP dashboard",
            "Approve only if PO owner confirms exception",
            "After approve, post to accounting connector",
        ]
        requires_human = not rules.hitl_auto_approve
    elif (
        matching.status == MatchStatus.matched
        and rules.auto_approve_when_clean
        and not hitl
    ):
        action = ReviewAction.approve
        reasoning = (
            "Clean match within tolerances, confidence above thresholds, "
            f"total ${invoice.total:.2f} under review threshold. " + matching.summary
        )
        next_actions = [
            "Post to accounting (QuickBooks/NetSuite/CSV)",
            "Schedule payment per terms",
            "Archive invoice + audit trail",
        ]
        requires_human = bool(rules.hitl_auto_approve is False and False)
        # Clean path: no human required unless policy forces
        requires_human = False
        conf = max(conf, 0.85)
    else:
        action = ReviewAction.needs_review
        reasoning = matching.summary or "Partial match — recommend human confirmation."
        next_actions = ["Review partial match details", "Approve or request credit memo"]
        requires_human = True

    return ReviewDecision(
        action=action,
        reasoning=reasoning,
        confidence=round(max(0.0, min(1.0, conf)), 3),
        requires_human=requires_human,
        hitl_reasons=hitl,
        recommended_next_actions=next_actions,
        risk_flags=risks,
    )

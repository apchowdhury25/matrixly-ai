"""Urgency scoring for inbox triage."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import EmailMessage


@dataclass
class UrgencyResult:
    score: float
    is_urgent: bool
    reasons: list[str]
    category: str  # urgent | needs_reply | fyi | newsletter | automated | waiting


def _domain(email: str) -> str:
    if "@" not in email:
        return ""
    return email.split("@", 1)[1].lower()


def score_message(msg: EmailMessage, cfg: dict[str, Any]) -> UrgencyResult:
    urg = cfg.get("urgency") or {}
    account = cfg.get("account") or {}
    own_domains = {d.lower() for d in account.get("domains") or []}
    keywords = [k.lower() for k in urg.get("keywords") or []]
    vip_domains = {d.lower() for d in urg.get("vip_domains") or []}
    vip_addresses = {a.lower() for a in urg.get("vip_addresses") or []}
    threshold = float(urg.get("urgent_threshold") or 0.65)

    score = 0.0
    reasons: list[str] = []
    text = f"{msg.subject}\n{msg.snippet}\n{msg.body}".lower()
    subj = (msg.subject or "").lower()

    # Automated / newsletter heuristics
    automated_markers = (
        "no-reply",
        "noreply",
        "do-not-reply",
        "donotreply",
        "notifications@",
        "mailer-daemon",
        "newsletter",
        "unsubscribe",
    )
    from_l = msg.from_email.lower()
    if any(m in from_l or m in text[:500] for m in automated_markers):
        if "unsubscribe" in text or "newsletter" in from_l or "newsletter" in subj:
            return UrgencyResult(0.05, False, ["Looks like newsletter/marketing"], "newsletter")
        return UrgencyResult(0.1, False, ["Looks automated/no-reply"], "automated")

    # Never treat own mailbox as VIP
    own = ((cfg.get("account") or {}).get("primary_email") or "").lower()
    if from_l and from_l == own:
        reasons.append("Self-sent / same mailbox")
    else:
        # VIP
        if from_l in vip_addresses:
            score += 0.45
            reasons.append("VIP sender address")
        if _domain(from_l) in vip_domains:
            score += 0.3
            reasons.append("VIP domain")

    # Keyword hits (subject hits weigh more)
    hits = [k for k in keywords if k in text]
    subj_hits = [k for k in keywords if k in subj]
    if hits:
        score += min(0.7, 0.14 * len(hits) + 0.1 * len(subj_hits))
        reasons.append(f"Urgency keywords: {', '.join(hits[:5])}")

    # Direct request patterns
    if re.search(
        r"\b(can you|could you|please|need you to|we need|i need|waiting on|follow[- ]?up|action required|respond by)\b",
        text,
    ):
        score += 0.15
        reasons.append("Contains direct request language")

    # Question mark in subject often needs reply
    if "?" in msg.subject:
        score += 0.1
        reasons.append("Question in subject")

    # External vs internal
    sender_domain = _domain(from_l)
    if sender_domain and sender_domain not in own_domains:
        score += 0.08
        reasons.append("External sender")
    else:
        score += 0.05
        reasons.append("Internal domain")

    # Thread already labeled Important by Gmail
    if "IMPORTANT" in (msg.label_ids or []):
        score += 0.2
        reasons.append("Gmail IMPORTANT")

    score = max(0.0, min(1.0, score))
    is_urgent = score >= threshold or len(subj_hits) >= 2

    if is_urgent:
        category = "urgent"
    elif any(
        p in text
        for p in (
            "can you",
            "could you",
            "please reply",
            "please confirm",
            "let me know",
            "looking forward",
            "awaiting",
            "waiting for",
            "we need",
            "i need",
        )
    ) or "?" in msg.subject:
        category = "needs_reply"
    else:
        category = "fyi"

    if not reasons:
        reasons.append("Default scoring")

    return UrgencyResult(score=round(score, 3), is_urgent=is_urgent, reasons=reasons, category=category)

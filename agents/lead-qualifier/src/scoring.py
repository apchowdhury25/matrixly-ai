"""Inbound lead scoring (fit · intent · seniority · data quality)."""

from __future__ import annotations

import re
from typing import Any

from .models import Enrichment, Lead, ScoreResult


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def json_safe(obj: Any) -> str:
    try:
        import json

        return json.dumps(obj, default=str)
    except Exception:  # noqa: BLE001
        return str(obj)


def score_lead(lead: Lead, enrichment: Enrichment, cfg: dict[str, Any]) -> ScoreResult:
    icp = cfg.get("icp") or {}
    scoring = cfg.get("scoring") or {}
    weights = scoring.get("weights") or {}
    thresholds = scoring.get("thresholds") or {}
    free_domains = {d.lower() for d in scoring.get("free_email_domains") or []}

    reasons: list[str] = []
    fit = 0.35
    intent = 0.25
    seniority = 0.25
    data_quality = 0.3

    domain = lead.domain or enrichment.domain
    is_free = domain in free_domains or enrichment.is_free_email
    enrichment.is_free_email = is_free

    # --- Fit ---
    industry_blob = _norm(f"{lead.industry} {enrichment.industry} {lead.notes} {lead.company}")
    industries = [_norm(i) for i in icp.get("target_industries") or []]
    industry_hits = [i for i in industries if i and i in industry_blob]
    if industry_hits:
        fit += min(0.45, 0.15 * len(industry_hits))
        reasons.append(f"Industry match: {', '.join(industry_hits[:3])}")
    elif industry_blob:
        fit += 0.05
        reasons.append("Industry present but not primary ICP")

    geo_blob = _norm(f"{lead.city} {lead.state} {lead.country} {enrichment.location_guess}")
    geos = [_norm(g) for g in icp.get("geographies") or []]
    if any(g in geo_blob for g in geos if g):
        fit += 0.15
        reasons.append("Geography aligns with ICP")

    employees = lead.employee_count
    bands = icp.get("employee_bands") or {}
    ideal = bands.get("ideal") or [5, 200]
    acceptable = bands.get("acceptable") or [1, 500]
    if employees is not None:
        if ideal[0] <= employees <= ideal[1]:
            fit += 0.2
            reasons.append(f"Employee count in ideal band ({employees})")
        elif acceptable[0] <= employees <= acceptable[1]:
            fit += 0.1
            reasons.append(f"Employee count acceptable ({employees})")
        else:
            fit -= 0.1
            reasons.append(f"Employee count outside ICP ({employees})")

    if is_free:
        fit -= 0.15
        reasons.append("Free-mail domain — weaker company signal")
    else:
        fit += 0.12
        reasons.append(f"Business domain: {domain}")

    # --- Intent ---
    notes = _norm(f"{lead.notes} {lead.source} {json_safe(lead.raw)}")
    intent_keywords = [
        "demo",
        "pricing",
        "pilot",
        "quote",
        "budget",
        "timeline",
        "asap",
        "interested",
        "buy",
        "implement",
        "evaluate",
        "rfp",
        "partnership",
        "urgent",
        "this week",
        "this month",
    ]
    hits = [k for k in intent_keywords if k in notes]
    if hits:
        intent += min(0.55, 0.1 * len(hits))
        reasons.append(f"Intent signals: {', '.join(hits[:5])}")
    if lead.source and "inbound" in _norm(lead.source):
        intent += 0.1
        reasons.append("Inbound source")
    if lead.source and any(x in _norm(lead.source) for x in ("referral", "partner")):
        intent += 0.15
        reasons.append("Referral/partner source")

    # --- Seniority ---
    title = _norm(lead.title)
    roles = [_norm(r) for r in icp.get("target_roles") or []]
    role_hits = [r for r in roles if r and r in title]
    if role_hits:
        seniority += min(0.55, 0.18 * len(role_hits))
        reasons.append(f"Role fit: {lead.title}")
    elif title:
        if any(x in title for x in ("intern", "student", "assistant")):
            seniority -= 0.2
            reasons.append("Junior title")
        else:
            seniority += 0.05
            reasons.append(f"Title present: {lead.title}")
    else:
        reasons.append("No title provided")

    # --- Data quality ---
    fields = [
        lead.email,
        lead.full_name or lead.first_name,
        lead.company or enrichment.company,
        lead.title,
        lead.phone,
        lead.website or enrichment.website,
    ]
    filled = sum(1 for f in fields if f)
    data_quality = filled / max(1, len(fields))
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", lead.email or ""):
        data_quality = min(1.0, data_quality + 0.1)
    else:
        data_quality *= 0.3
        reasons.append("Invalid or missing email")
    reasons.append(f"Data completeness {filled}/{len(fields)}")

    # Clamp components
    fit = max(0.0, min(1.0, fit))
    intent = max(0.0, min(1.0, intent))
    seniority = max(0.0, min(1.0, seniority))
    data_quality = max(0.0, min(1.0, data_quality))

    w_fit = float(weights.get("fit", 0.35))
    w_intent = float(weights.get("intent", 0.30))
    w_sen = float(weights.get("seniority", 0.20))
    w_dq = float(weights.get("data_quality", 0.15))
    total_w = w_fit + w_intent + w_sen + w_dq or 1.0
    score = (
        fit * w_fit + intent * w_intent + seniority * w_sen + data_quality * w_dq
    ) / total_w
    score = round(max(0.0, min(1.0, score)), 3)

    hot = float(thresholds.get("hot", 0.75))
    warm = float(thresholds.get("warm", 0.50))
    cold = float(thresholds.get("cold", 0.30))

    # Hard DQ
    disqualifiers = icp.get("disqualifiers") or []
    blob = _norm(f"{lead.notes} {lead.title} {lead.company}")
    if any(_norm(d) in blob for d in disqualifiers if d):
        return ScoreResult(
            score=0.05,
            tier="disqualified",
            fit=fit,
            intent=intent,
            seniority=seniority,
            data_quality=data_quality,
            reasons=reasons + ["Matched disqualifier"],
            recommended_action="Do not pursue — archive or nurture list",
        )

    if not lead.email:
        tier = "disqualified"
        action = "Request valid email before outreach"
    elif score >= hot:
        tier = "hot"
        action = "Route to AE same day · start sequence touch 1 immediately"
    elif score >= warm:
        tier = "warm"
        action = "SDR follow-up within 24h · run 4-touch sequence"
    elif score >= cold:
        tier = "cold"
        action = "Light nurture · add to monthly drip"
    else:
        tier = "disqualified"
        action = "Park — insufficient fit/intent"

    return ScoreResult(
        score=score,
        tier=tier,
        fit=round(fit, 3),
        intent=round(intent, 3),
        seniority=round(seniority, 3),
        data_quality=round(data_quality, 3),
        reasons=reasons,
        recommended_action=action,
    )

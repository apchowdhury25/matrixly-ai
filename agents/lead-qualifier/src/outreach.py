"""Personalized outreach sequence generation."""

from __future__ import annotations

from typing import Any

from .llm import chat, extract_json, grok_available
from .models import Enrichment, Lead, OutreachTouch, ScoreResult


def _first_name(lead: Lead) -> str:
    if lead.first_name:
        return lead.first_name
    if lead.full_name:
        return lead.full_name.split()[0]
    return "there"


def sequence_template(
    lead: Lead,
    enrichment: Enrichment,
    score: ScoreResult,
    cfg: dict[str, Any],
) -> list[OutreachTouch]:
    outreach = cfg.get("outreach") or {}
    op = cfg.get("operator") or {}
    days = list(outreach.get("sequence_days") or [0, 2, 5, 9])
    cta = outreach.get("cta") or "book a short call"
    company = enrichment.company or lead.company or "your team"
    name = _first_name(lead)
    seller = op.get("company") or "Matrixly.AI"
    industry = enrichment.industry or lead.industry or "your industry"

    frames = [
        (
            f"Quick idea for {company}",
            (
                f"Hi {name},\n\n"
                f"Noticed {company} in {industry} and thought a lightweight AI agent pilot "
                f"might save your team hours on sales/ops follow-up.\n\n"
                f"{seller} deploys ready agents (lead qualify, email triage, CRM hygiene) "
                f"without a big IT project.\n\n"
                f"Open to {cta}?\n\n"
                f"Best,\nAnwar"
            ),
        ),
        (
            f"Re: idea for {company}",
            (
                f"Hi {name},\n\n"
                f"Bumping this in case it got buried — SMBs in {industry} usually start with "
                f"an Email Assistant or Lead Qualifier and see time back in week one.\n\n"
                f"Worth a {cta}?\n\n"
                f"Anwar"
            ),
        ),
        (
            f"Houston SMB agents — {company}",
            (
                f"Hi {name},\n\n"
                f"One concrete path: we score inbound leads, enrich contacts, and draft "
                f"outreach sequences — then hand warm leads to your team or Salesforce.\n\n"
                f"If useful, happy to {cta}.\n\n"
                f"Anwar · {seller}"
            ),
        ),
        (
            f"Should I close the loop, {name}?",
            (
                f"Hi {name},\n\n"
                f"I'll close the loop on my side unless a pilot still makes sense for {company}. "
                f"If timing is better later, just reply \"later\" and I'll pause.\n\n"
                f"Either way, appreciate your time.\n\n"
                f"Anwar"
            ),
        ),
    ]

    # Hot leads get slightly more direct CTA on touch 1
    if score.tier == "hot":
        frames[0] = (
            f"{name}, quick pilot for {company}?",
            (
                f"Hi {name},\n\n"
                f"You look like a strong fit for a same-week pilot of our Lead Qualifier + Email Assistant "
                f"({score.recommended_action}).\n\n"
                f"Can we {cta} this week?\n\n"
                f"Anwar · {seller}"
            ),
        )

    touches: list[OutreachTouch] = []
    for i, day in enumerate(days[: len(frames)]):
        subj, body = frames[i]
        touches.append(OutreachTouch(day=int(day), channel="email", subject=subj, body=body))
    return touches


def sequence_with_llm(
    lead: Lead,
    enrichment: Enrichment,
    score: ScoreResult,
    cfg: dict[str, Any],
) -> list[OutreachTouch]:
    if not grok_available(cfg):
        return sequence_template(lead, enrichment, score, cfg)

    outreach = cfg.get("outreach") or {}
    op = cfg.get("operator") or {}
    days = list(outreach.get("sequence_days") or [0, 2, 5, 9])
    system = (
        "You are a B2B SDR coach for Matrixly.AI (AI agent marketplace for Houston SMBs). "
        "Write a personalized multi-touch email sequence. "
        "Return ONLY JSON array of objects: "
        '[{"day":0,"channel":"email","subject":"...","body":"..."}]. '
        f"Use days {days}. Max ~{outreach.get('max_words_per_email', 140)} words per body. "
        "No hype, no fake claims, no invented case studies. "
        f"CTA: {outreach.get('cta')}. Tone: {outreach.get('tone')}."
    )
    user = (
        f"Lead: {lead.to_dict()}\n"
        f"Enrichment: {enrichment.to_dict()}\n"
        f"Score: {score.to_dict()}\n"
        f"Seller: {op}"
    )
    try:
        raw = chat(cfg, system, user, temperature=0.4)
        data = extract_json(raw)
        if not isinstance(data, list) or not data:
            return sequence_template(lead, enrichment, score, cfg)
        touches: list[OutreachTouch] = []
        for i, item in enumerate(data[:4]):
            if not isinstance(item, dict):
                continue
            touches.append(
                OutreachTouch(
                    day=int(item.get("day", days[i] if i < len(days) else i * 2)),
                    channel=str(item.get("channel") or "email"),
                    subject=str(item.get("subject") or f"Follow-up {i+1}"),
                    body=str(item.get("body") or "").strip(),
                )
            )
        return touches or sequence_template(lead, enrichment, score, cfg)
    except Exception:  # noqa: BLE001
        return sequence_template(lead, enrichment, score, cfg)


def build_sequence(
    lead: Lead,
    enrichment: Enrichment,
    score: ScoreResult,
    cfg: dict[str, Any],
    *,
    use_llm: bool = True,
) -> list[OutreachTouch]:
    if score.tier == "disqualified":
        return []
    if use_llm:
        return sequence_with_llm(lead, enrichment, score, cfg)
    return sequence_template(lead, enrichment, score, cfg)

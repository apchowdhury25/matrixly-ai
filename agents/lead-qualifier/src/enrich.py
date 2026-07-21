"""Contact enrichment (heuristic + optional Grok)."""

from __future__ import annotations

from typing import Any

from .llm import chat, extract_json, grok_available
from .models import Enrichment, Lead


def _is_free_email(domain: str, cfg: dict) -> bool:
    free = {
        d.lower()
        for d in (cfg.get("scoring") or {}).get("free_email_domains") or []
    }
    return domain.lower() in free


def enrich_heuristic(lead: Lead, cfg: dict[str, Any]) -> Enrichment:
    domain = lead.domain
    free = _is_free_email(domain, cfg) if domain else True
    company = lead.company
    website = lead.website
    signals: list[str] = []

    if not company and domain and not free:
        # acme-logistics.com → Acme Logistics
        base = domain.split(".")[0]
        company = " ".join(p.capitalize() for p in re_split(base))
        signals.append("Company inferred from email domain")

    if not website and domain and not free:
        website = f"https://{domain}"
        signals.append("Website inferred from domain")

    linkedin = ""
    if lead.full_name:
        slug = lead.full_name.lower().replace(" ", "-")
        linkedin = f"https://www.linkedin.com/search/results/people/?keywords={lead.full_name.replace(' ', '%20')}"
        signals.append("LinkedIn search link generated")

    industry = lead.industry
    if not industry and company:
        # light keyword industry guess from company name / notes
        blob = f"{company} {lead.notes} {lead.title}".lower()
        mapping = {
            "logistics": "logistics",
            "freight": "logistics",
            "shipping": "logistics",
            "import": "import-export",
            "export": "import-export",
            "hvac": "hvac",
            "plumbing": "home services",
            "construction": "construction",
            "remodel": "construction",
            "wholesale": "wholesale",
            "manufactur": "manufacturing",
            "software": "saas",
            "saas": "saas",
        }
        for k, ind in mapping.items():
            if k in blob:
                industry = ind
                signals.append(f"Industry guessed from text: {ind}")
                break

    location = ", ".join(x for x in [lead.city, lead.state, lead.country] if x)
    conf = 0.4
    if company and domain and not free:
        conf = 0.65
    if lead.industry and lead.company:
        conf = 0.75

    return Enrichment(
        company=company or "",
        industry=industry or "",
        website=website or "",
        linkedin_guess=linkedin,
        employee_band=_employee_band(lead.employee_count),
        location_guess=location,
        is_free_email=free,
        domain=domain,
        signals=signals,
        confidence=conf,
        provider="heuristic",
    )


def re_split(base: str) -> list[str]:
    import re

    parts = re.split(r"[-_]+", base)
    return [p for p in parts if p]


def _employee_band(n: int | None) -> str:
    if n is None:
        return ""
    if n < 5:
        return "1-4"
    if n < 25:
        return "5-24"
    if n < 100:
        return "25-99"
    if n < 500:
        return "100-499"
    return "500+"


def enrich_with_llm(lead: Lead, base: Enrichment, cfg: dict[str, Any]) -> Enrichment:
    if not grok_available(cfg):
        return base
    op = cfg.get("operator") or {}
    system = (
        "You enrich B2B sales leads for Matrixly.AI (AI agent marketplace for SMBs). "
        "Return ONLY JSON with keys: company, industry, website, employee_band, "
        "location_guess, signals (array of short strings), confidence (0-1). "
        "Do not invent specific revenue or named executives. Be conservative."
    )
    user = (
        f"Lead: {lead.to_dict()}\n"
        f"Heuristic enrichment: {base.to_dict()}\n"
        f"Seller: {op.get('company')} · market: {op.get('market')}"
    )
    try:
        raw = chat(cfg, system, user, temperature=0.2)
        data = extract_json(raw)
        if not isinstance(data, dict):
            return base
        return Enrichment(
            company=data.get("company") or base.company,
            industry=data.get("industry") or base.industry,
            website=data.get("website") or base.website,
            linkedin_guess=base.linkedin_guess,
            employee_band=data.get("employee_band") or base.employee_band,
            location_guess=data.get("location_guess") or base.location_guess,
            is_free_email=base.is_free_email,
            domain=base.domain,
            signals=list(base.signals)
            + list(data.get("signals") or [])
            + ["Grok enrichment applied"],
            confidence=float(data.get("confidence") or base.confidence),
            provider="heuristic+grok",
        )
    except Exception as exc:  # noqa: BLE001
        base.signals.append(f"LLM enrich skipped: {exc}")
        return base


def enrich_lead(lead: Lead, cfg: dict[str, Any], *, use_llm: bool = True) -> Enrichment:
    base = enrich_heuristic(lead, cfg)
    # Apply enrichment back onto lead gaps
    if not lead.company and base.company:
        lead.company = base.company
    if not lead.website and base.website:
        lead.website = base.website
    if not lead.industry and base.industry:
        lead.industry = base.industry

    if use_llm and (cfg.get("enrichment") or {}).get("use_llm", True):
        return enrich_with_llm(lead, base, cfg)
    return base

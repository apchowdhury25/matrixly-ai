"""Brand-voice SEO content writer."""

from __future__ import annotations

import re
from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import JobStatus, SeoJob


def run_writer(job: SeoJob, cfg: dict) -> tuple[SeoJob, int, int]:
    tin = tout = 0
    brand = BrandMemory(cfg)
    voice = brand.get_voice()
    profile = brand.get_profile()

    if llm.grok_available(cfg):
        try:
            system = prompt_text("writer") + f"\n\n# Brand voice\n{voice[:3000]}"
            user = (
                f"Content type: {job.content_type}\n"
                f"Goal: {job.goal}\n"
                f"Business: {profile}\n"
                f"Service areas: {job.service_areas}\n"
                f"Research: {job.research}\n"
                f"Brief:\n{job.source_text[:8000]}\n"
                f"Title hint: {job.title}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.45)
            data = llm.extract_json(content)
            job.draft = data if isinstance(data, dict) else {"body_markdown": str(data)}
            job.status = JobStatus.writing
            job.confidence = float(job.draft.get("confidence") or 0.75)
            job.quality_score = min(0.95, 0.7 + job.confidence * 0.25)
            return job, tin, tout
        except Exception as e:
            job.metadata["writer_error"] = str(e)

    job.draft = _rule_draft(job, profile)
    job.status = JobStatus.writing
    job.quality_score = 0.78
    job.confidence = 0.7
    return job, tin, tout


def _rule_draft(job: SeoJob, profile: dict[str, Any]) -> dict[str, Any]:
    areas = job.service_areas or profile.get("service_areas") or ["your city"]
    city = areas[0]
    btype = job.business_type or profile.get("business_type") or "local business"
    name = profile.get("business_name") or "Your Business"
    kws = (job.research or {}).get("keywords") or []
    primary = job.metadata.get("primary_keyword") if job.metadata else None
    if not primary and kws and isinstance(kws[0], dict):
        primary = kws[0].get("keyword")
    primary = primary or f"{btype} {city}"
    ctype = job.content_type or "blog"
    title = job.title or f"{primary.title()}: Trusted Local Help"
    if len(title) > 60:
        title = title[:57] + "…"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    meta = f"Looking for {primary}? {name} serves {city}. Get clear answers and book with confidence."
    if len(meta) > 160:
        meta = meta[:157] + "…"

    outline = [
        f"Why {city} customers choose a local {btype}",
        "What to expect when you reach out",
        "Service areas we cover",
        "FAQs",
        "Ready to get started?",
    ]
    body = f"""{meta}

## {outline[0]}

When you search for **{primary}**, you want a team that shows up, communicates clearly, and stands behind the work. {name} helps {city} homeowners and businesses with practical solutions — no hype, no invented guarantees.

## {outline[1]}

1. Tell us what you need (form, call, or message).
2. We confirm fit and next steps.
3. You approve the plan before work proceeds.

## {outline[2]}

We proudly serve: {", ".join(areas)}.

## {outline[3]}

### How fast can you respond?
Response times vary by season and demand. We aim to reply the same business day when possible.

### Do you serve my neighborhood?
If you are in {city} or nearby service areas listed above, reach out and we will confirm.

## {outline[4]}

Contact {name} today to discuss your needs. This draft is **publish-ready only after your approval** in the Matrixly approval queue.
"""
    return {
        "content_type": ctype,
        "title": title,
        "meta_description": meta,
        "slug": slug,
        "primary_keyword": primary,
        "secondary_keywords": [f"{btype} near me", f"{btype} {city}".lower()],
        "outline": outline,
        "body_markdown": body,
        "internal_link_suggestions": [
            "Link to contact / book page",
            "Link to related service page",
            "Link to about / credentials page (only real claims)",
        ],
        "schema_suggestions": ["LocalBusiness", "Service", "FAQPage"],
        "social_variants": {
            "linkedin": f"New resource for {city}: how to choose the right {btype} without the hype. → [link]",
            "x": f"{city}: need a {btype}? Start with questions that matter. New guide: [link]",
            "instagram": f"Local tips for {city} · {primary} · Link in bio after approval",
        },
        "gbp_post": f"Serving {city} with reliable {btype} support. Questions? Message us — happy to help. (Draft — approve before posting)",
        "publishing_checklist": [
            "Owner approved brand claims",
            "Title & meta under length limits",
            "Internal links added on live site",
            "Images have descriptive alt text",
            "Scheduled or published only after HITL approve",
        ],
        "estimated_impact": "Supports local rankings for service+city queries within 30–90 days",
        "owner_effort": "~15–25 minutes to review and approve",
        "next_action": "Approve in content queue, then publish to WordPress draft or GBP",
        "confidence": 0.7,
    }

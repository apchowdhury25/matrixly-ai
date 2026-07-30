"""Local SEO / Google Business Profile specialist."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import SeoJob


def run_local_seo(job: SeoJob, cfg: dict) -> tuple[SeoJob, int, int]:
    tin = tout = 0
    brand = BrandMemory(cfg)
    voice = brand.get_voice()
    profile = brand.get_profile()

    if llm.grok_available(cfg):
        try:
            system = prompt_text("local_seo") + f"\n\n# Brand voice\n{voice[:2000]}"
            user = (
                f"Profile: {profile}\n"
                f"Service areas: {job.service_areas}\n"
                f"GBP notes: {job.metadata.get('gbp_notes', '')}\n"
                f"Brief:\n{job.source_text[:6000]}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.35)
            data = llm.extract_json(content)
            job.local = data if isinstance(data, dict) else {"notes": str(data)}
            job.confidence = float(job.local.get("confidence") or 0.75)
            return job, tin, tout
        except Exception as e:
            job.metadata["local_error"] = str(e)

    job.local = _rule_local(job, profile)
    job.confidence = 0.7
    return job, tin, tout


def _rule_local(job: SeoJob, profile: dict[str, Any]) -> dict[str, Any]:
    areas = job.service_areas or profile.get("service_areas") or ["your city"]
    city = areas[0]
    btype = job.business_type or profile.get("business_type") or "local business"
    name = profile.get("business_name") or "Your Business"
    return {
        "gbp_profile_suggestions": {
            "categories": [f"Primary category matching {btype}"],
            "services": [f"Core {btype} offerings (list only real services)"],
            "description": (
                f"{name} provides {btype} services for customers in {', '.join(areas)}. "
                "Friendly, clear communication — no invented guarantees. Contact us for availability."
            ),
            "posts": [
                f"This week in {city}: how to prepare before you call a {btype}.",
                f"Service area spotlight: proud to help neighbors in {city}.",
            ],
            "qa": [
                {
                    "q": f"Do you serve {city}?",
                    "a": f"Yes — we serve {', '.join(areas)}. Message us to confirm your location.",
                },
                {
                    "q": "How do I get a quote?",
                    "a": "Share a short description of what you need and the best way to reach you. We will follow up with next steps.",
                },
            ],
            "photo_caption_ideas": [
                f"Team ready to help {city} customers",
                "Before/after project (only real photos you own)",
            ],
        },
        "location_page_outline": [
            f"H1: {btype.title()} in {city}",
            "Neighborhoods / service area map note",
            "Services offered",
            "What to expect",
            "Reviews policy (never invent reviews)",
            "Contact CTA",
        ],
        "citation_checklist": [
            "NAP (name, address, phone) consistent everywhere",
            "Website URL matches live site",
            "Categories aligned with actual services",
            "Hours accurate including holidays",
        ],
        "review_response_templates": [
            {
                "tone": "positive",
                "template": f"Thank you for the kind words! We're glad we could help. — {name}",
            },
            {
                "tone": "neutral",
                "template": "Thanks for sharing your experience. If there's more we can clarify, please message us directly.",
            },
            {
                "tone": "negative",
                "template": "We're sorry this didn't meet your expectations. Please contact us so we can make it right — we take feedback seriously.",
            },
        ],
        "near_me_cluster": [
            f"{btype} near me",
            f"{btype} {city}",
            f"emergency {btype} {city}".strip(),
            f"best {btype} {city}",
        ],
        "owner_effort_minutes": 35,
        "estimated_impact": "Stronger local pack visibility when NAP + GBP activity stay consistent",
        "confidence": 0.7,
    }

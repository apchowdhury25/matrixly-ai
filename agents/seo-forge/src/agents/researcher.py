"""SEO research — keywords, gaps, near-me opportunities."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import JobStatus, SeoJob


def run_researcher(job: SeoJob, cfg: dict) -> tuple[SeoJob, int, int]:
    tin = tout = 0
    brand = BrandMemory(cfg)
    voice = brand.get_voice()
    profile = brand.get_profile()
    text = job.source_text[: int((cfg.get("seo") or {}).get("max_source_chars") or 40000)]

    if llm.grok_available(cfg):
        try:
            system = prompt_text("researcher") + f"\n\n# Brand voice\n{voice[:2500]}"
            user = (
                f"Business type: {job.business_type or profile.get('business_type')}\n"
                f"Service areas: {job.service_areas or profile.get('service_areas')}\n"
                f"Goal: {job.goal}\n\nBrief:\n{text}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.3)
            data = llm.extract_json(content)
            job.research = data if isinstance(data, dict) else {"summary": str(data)}
            job.status = JobStatus.researching
            job.confidence = float(job.research.get("confidence") or 0.75)
            return job, tin, tout
        except Exception as e:
            job.metadata["research_error"] = str(e)

    job.research = _rule_research(job, profile)
    job.status = JobStatus.researching
    job.confidence = 0.7
    return job, tin, tout


def _rule_research(job: SeoJob, profile: dict[str, Any]) -> dict[str, Any]:
    text = job.source_text or ""
    areas = job.service_areas or profile.get("service_areas") or ["your city"]
    city = areas[0] if areas else "your city"
    btype = job.business_type or profile.get("business_type") or "local service business"
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    stop = {
        "that", "this", "with", "from", "your", "have", "will", "they", "about",
        "into", "when", "what", "which", "their", "than", "also", "more", "most",
        "just", "like", "only", "other", "some", "such", "after", "before",
        "because", "being", "while", "where", "would", "could", "should", "there",
        "using", "used", "make", "made", "business", "service", "services",
    }
    counts = Counter(w for w in words if w not in stop)
    base_kw = [w for w, _ in counts.most_common(5)]
    keywords = []
    seeds = base_kw or [btype.split()[0].lower() if btype else "service"]
    for s in seeds[:4]:
        keywords.append(
            {
                "keyword": f"{s} {city}",
                "intent": "local",
                "priority": "high",
                "rationale": f"Local commercial intent for {city}",
            }
        )
        keywords.append(
            {
                "keyword": f"{s} near me",
                "intent": "local",
                "priority": "high",
                "rationale": "Near-me mobile search",
            }
        )
    keywords.append(
        {
            "keyword": f"best {btype} in {city}".lower(),
            "intent": "commercial",
            "priority": "medium",
            "rationale": "Comparison intent",
        }
    )
    return {
        "summary": f"Prioritize local + near-me keywords for {btype} in {', '.join(areas)}.",
        "business_type": btype,
        "service_areas": areas,
        "primary_intents": ["local commercial", "near me", "service pages"],
        "keywords": keywords[:8],
        "content_gaps": [
            f"Dedicated service page for top offering in {city}",
            "FAQ answering pricing process without inventing numbers",
            "Seasonal blog tied to local demand",
        ],
        "near_me_opportunities": [
            f"{city} landing page cluster",
            "Google Business Profile weekly posts",
            "Review response templates",
        ],
        "competitor_notes": [
            "Map top 3 local competitors' service page structure (manual review).",
        ],
        "risks": ["Do not invent review counts or guarantees"],
        "confidence": 0.7,
    }

"""30-day SEO strategy planner."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import JobStatus, SeoJob


def run_strategist(job: SeoJob, cfg: dict) -> tuple[SeoJob, int, int]:
    tin = tout = 0
    brand = BrandMemory(cfg)
    voice = brand.get_voice()
    profile = brand.get_profile()

    if llm.grok_available(cfg):
        try:
            system = prompt_text("strategist") + f"\n\n# Brand voice\n{voice[:2000]}"
            user = (
                f"Profile: {profile}\n"
                f"Goal: {job.goal}\n"
                f"Business type: {job.business_type}\n"
                f"Service areas: {job.service_areas}\n"
                f"Research: {job.research}\n"
                f"Brief:\n{job.source_text[:6000]}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.35)
            data = llm.extract_json(content)
            job.plan = data if isinstance(data, dict) else {"theme": str(data)}
            job.status = JobStatus.planning
            job.confidence = float(job.plan.get("confidence") or job.confidence or 0.75)
            return job, tin, tout
        except Exception as e:
            job.metadata["strategist_error"] = str(e)

    job.plan = _rule_plan(job, profile)
    job.status = JobStatus.planning
    return job, tin, tout


def _rule_plan(job: SeoJob, profile: dict[str, Any]) -> dict[str, Any]:
    areas = job.service_areas or profile.get("service_areas") or ["your city"]
    city = areas[0]
    btype = job.business_type or profile.get("business_type") or "local business"
    goal = job.goal or profile.get("primary_goal") or "organic_leads"
    kws = (job.research or {}).get("keywords") or []
    top = (kws[0].get("keyword") if kws and isinstance(kws[0], dict) else f"{btype} {city}")
    return {
        "theme": f"30-day local SEO sprint for {btype} in {city}",
        "primary_goal": goal,
        "weeks": [
            {
                "week": 1,
                "focus": "Foundation & brand voice",
                "actions": [
                    {
                        "title": "Confirm brand voice + approved claims",
                        "type": "content",
                        "effort": "low",
                        "impact": "high",
                        "owner_effort_minutes": 20,
                    },
                    {
                        "title": f"Audit homepage & top service page for {top}",
                        "type": "technical",
                        "effort": "medium",
                        "impact": "high",
                        "owner_effort_minutes": 30,
                    },
                    {
                        "title": "Claim/optimize Google Business Profile basics",
                        "type": "local",
                        "effort": "medium",
                        "impact": "high",
                        "owner_effort_minutes": 45,
                    },
                ],
            },
            {
                "week": 2,
                "focus": "High-intent pages",
                "actions": [
                    {
                        "title": f"Publish service page targeting “{top}”",
                        "type": "content",
                        "effort": "medium",
                        "impact": "high",
                        "owner_effort_minutes": 25,
                    },
                    {
                        "title": f"Create {city} location landing page",
                        "type": "local",
                        "effort": "medium",
                        "impact": "high",
                        "owner_effort_minutes": 20,
                    },
                ],
            },
            {
                "week": 3,
                "focus": "Content velocity + GBP",
                "actions": [
                    {
                        "title": "Publish FAQ blog answering top local questions",
                        "type": "content",
                        "effort": "medium",
                        "impact": "medium",
                        "owner_effort_minutes": 15,
                    },
                    {
                        "title": "2 Google Business Profile posts + photo captions",
                        "type": "local",
                        "effort": "low",
                        "impact": "medium",
                        "owner_effort_minutes": 20,
                    },
                    {
                        "title": "Review response templates live",
                        "type": "local",
                        "effort": "low",
                        "impact": "medium",
                        "owner_effort_minutes": 10,
                    },
                ],
            },
            {
                "week": 4,
                "focus": "Measure & refresh",
                "actions": [
                    {
                        "title": "Track rankings for priority keywords",
                        "type": "measure",
                        "effort": "low",
                        "impact": "high",
                        "owner_effort_minutes": 15,
                    },
                    {
                        "title": "Refresh weakest page based on audit",
                        "type": "content",
                        "effort": "medium",
                        "impact": "medium",
                        "owner_effort_minutes": 20,
                    },
                    {
                        "title": "ROI snapshot into Matrixly dashboard",
                        "type": "measure",
                        "effort": "low",
                        "impact": "high",
                        "owner_effort_minutes": 10,
                    },
                ],
            },
        ],
        "kpi_targets": {
            "organic_leads": "2–5 attributed inquiries / month by day 90 (varies by market)",
            "ranking_movement": "Movement on 3–5 service+city keywords within 30–90 days",
            "hours_saved": "4–8 hours/month vs agency or DIY SEO",
        },
        "next_approval_ask": "Approve Week 1 actions so SEOForge can draft the first service page and GBP package.",
        "confidence": 0.72,
    }

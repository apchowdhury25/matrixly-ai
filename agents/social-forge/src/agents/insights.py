"""Insights agent — performance snapshot + content ideas."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import Campaign, InsightsReport, new_id


def run_insights(
    campaigns: list[Campaign],
    cfg: dict,
    demo_metrics: dict[str, Any] | None = None,
) -> tuple[InsightsReport, int, int]:
    tin = tout = 0
    metrics = demo_metrics or {
        "impressions": 12840,
        "engagements": 942,
        "replies": 37,
        "best_platform": "linkedin",
    }
    themes = [c.theme for c in campaigns[:10] if c.theme]

    if llm.grok_available(cfg):
        try:
            system = prompt_text("insights")
            user = (
                f"Recent themes: {themes}\n"
                f"Metrics: {metrics}\n"
                f"Campaign count: {len(campaigns)}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                return _to_report(data), tin, tout
        except Exception:
            pass

    return _to_report(_rule_insights(themes, metrics)), tin, tout


def _to_report(data: dict[str, Any]) -> InsightsReport:
    return InsightsReport(
        id=new_id("ins_"),
        highlights=[str(x) for x in (data.get("highlights") or [])],
        risks=[str(x) for x in (data.get("risks") or [])],
        metrics_snapshot=dict(data.get("metrics_snapshot") or {}),
        suggestions=list(data.get("suggestions") or []),
        next_week_themes=[str(x) for x in (data.get("next_week_themes") or [])],
    )


def _rule_insights(themes: list[str], metrics: dict[str, Any]) -> dict[str, Any]:
    best = metrics.get("best_platform") or "linkedin"
    return {
        "highlights": [
            f"{best.title()} drove the strongest engagement in this window.",
            "HITL-approved posts reduced brand-risk comments.",
            f"Tracked themes: {', '.join(themes[:3]) or 'general SMB AI'}.",
        ],
        "risks": [
            "Posting too many promos without educational value may lower reply rate.",
            "Unanswered high-priority DMs hurt conversion.",
        ],
        "metrics_snapshot": metrics,
        "suggestions": [
            {
                "title": "Customer win micro-story",
                "platform": "linkedin",
                "angle": "Before/after of booking or support automation",
                "why": "Social proof outperforms feature lists for SMBs",
            },
            {
                "title": "3-tip thread on approval workflows",
                "platform": "x",
                "angle": "Why HITL beats fully autonomous posting",
                "why": "Matches audience anxiety about brand safety",
            },
            {
                "title": "Behind-the-scenes calendar",
                "platform": "instagram",
                "angle": "Screenshot of SocialForge calendar UI",
                "why": "Visual product education",
            },
        ],
        "next_week_themes": [
            "Human-in-the-loop social",
            "Agent marketplace for SMBs",
            "Integration tips (Buffer / Meta / LinkedIn)",
        ],
    }

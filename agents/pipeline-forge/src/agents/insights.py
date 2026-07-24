"""Insights agent — pipeline health."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import PipelineRun


def run_insights(run: PipelineRun, cfg: dict) -> tuple[PipelineRun, int, int]:
    tin = tout = 0

    if llm.grok_available(cfg):
        try:
            system = prompt_text("insights")
            user = (
                f"Scores: {[s.model_dump() for s in run.scores]}\n"
                f"Risks: {len(run.risks)}\n"
                f"Priority count: {len(run.priority_list)}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                run.insights = data
                return run, tin, tout
        except Exception as e:
            run.metadata["insights_error"] = str(e)

    run.insights = _rule_insights(run)
    return run, tin, tout


def _rule_insights(run: PipelineRun) -> dict[str, Any]:
    hot = sum(1 for s in run.scores if s.tier == "hot")
    warm = sum(1 for s in run.scores if s.tier == "warm")
    cold = sum(1 for s in run.scores if s.tier == "cold")
    at_risk = sum(1 for s in run.scores if s.at_risk)
    n = max(1, len(run.scores))
    avg = sum(s.score for s in run.scores) / n
    health = round(min(100, max(0, avg * 0.7 + hot * 5 - at_risk * 8)), 1)
    total_amt = sum(o.amount for o in run.opportunities)
    return {
        "health_score": health,
        "highlights": [
            f"{hot} hot opportunities in the active set.",
            f"Average score {avg:.1f} across {len(run.scores)} deals (${total_amt:,.0f} pipeline).",
            f"{len(run.priority_list)} items on the {run.cadence} work list.",
        ],
        "risks": [
            f"{at_risk} deals flagged at-risk.",
            f"{len([r for r in run.risks if r.risk_level == 'high'])} high-risk flags need same-day action.",
        ],
        "coverage": {"hot": hot, "warm": warm, "cold": cold, "at_risk": at_risk},
        "recommendations": [
            "Protect hot deals with next-step tasks before week's end.",
            "Run recovery plays on stale proposals / negotiations.",
            "Review cold high-value accounts for recycle vs. nurture.",
        ],
        "forecast_note": (
            "Near-term outlook depends on converting hot deals and rescuing high-risk late-stage pipeline."
        ),
    }

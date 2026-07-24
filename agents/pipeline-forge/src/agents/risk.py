"""Risk agent — at-risk deals and recovery actions."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import PipelineRun, RiskFlag, RunStatus


def run_risk(run: PipelineRun, cfg: dict) -> tuple[PipelineRun, int, int]:
    tin = tout = 0
    run.status = RunStatus.risk_review

    if llm.grok_available(cfg):
        try:
            system = prompt_text("risk")
            user = (
                f"Scores: {[s.model_dump() for s in run.scores]}\n"
                f"Opps: {[o.model_dump() for o in run.opportunities]}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict) and data.get("risks") is not None:
                run.risks = _parse(data["risks"], run)
                return run, tin, tout
        except Exception as e:
            run.metadata["risk_error"] = str(e)

    run.risks = _rule_risks(run, cfg)
    return run, tin, tout


def _parse(raw: list[Any], run: PipelineRun) -> list[RiskFlag]:
    by_id = {o.id: o for o in run.opportunities}
    out: list[RiskFlag] = []
    for row in raw:
        oid = str(row.get("opportunity_id") or "")
        o = by_id.get(oid)
        out.append(
            RiskFlag(
                opportunity_id=oid,
                risk_level=str(row.get("risk_level") or "medium"),
                reasons=[str(x) for x in (row.get("reasons") or [])],
                suggested_actions=[str(x) for x in (row.get("suggested_actions") or [])],
                suggested_stage=row.get("suggested_stage"),
                name=o.name if o else oid,
            )
        )
    return out


def _rule_risks(run: PipelineRun, cfg: dict) -> list[RiskFlag]:
    scoring = cfg.get("scoring") or {}
    stale = int(scoring.get("stale_days", 14))
    by_id = {o.id: o for o in run.opportunities}
    risks: list[RiskFlag] = []
    for sc in run.scores:
        o = by_id.get(sc.opportunity_id)
        if not o:
            continue
        reasons: list[str] = []
        actions: list[str] = []
        level = "low"
        if sc.at_risk or sc.score < float(scoring.get("warm_min", 50)):
            level = "medium"
        if o.last_activity_days >= stale:
            reasons.append(f"No activity for {o.last_activity_days} days")
            actions.append("Multi-thread: email + LinkedIn + call within 48h")
            level = "high" if o.stage.lower() in {"proposal", "negotiation"} else "medium"
        if "competitor" in (o.notes or "").lower():
            reasons.append("Competitor mentioned in notes")
            actions.append("Send differentiation one-pager + customer proof")
            level = "high" if level != "high" else level
        if o.stage.lower() in {"proposal", "negotiation"} and o.last_activity_days >= 7:
            reasons.append("Late-stage deal cooling")
            actions.append("Executive sponsor check-in; mutual close plan")
            level = "high"
        if sc.tier == "cold" and o.amount >= float(scoring.get("high_value_amount", 10000)):
            reasons.append("High value but cold score")
            actions.append("Re-qualify ICP fit or recycle to nurture")
        if not reasons and not sc.at_risk:
            continue
        if not reasons:
            reasons.append(sc.rationale or "Score below risk threshold")
        if not actions:
            actions.append("Book discovery refresh call this week")
        risks.append(
            RiskFlag(
                opportunity_id=o.id,
                risk_level=level,
                reasons=reasons,
                suggested_actions=actions,
                suggested_stage=None,
                name=o.name,
            )
        )
    risks.sort(key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r.risk_level, 3))
    return risks

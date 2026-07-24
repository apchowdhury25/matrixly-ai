"""Scorer agent — fit / engagement / behavior / urgency."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.playbook import PlaybookMemory
from ..models import Opportunity, PipelineRun, RunStatus, ScoreCard


def run_scorer(
    run: PipelineRun,
    cfg: dict,
    playbook: PlaybookMemory,
) -> tuple[PipelineRun, int, int]:
    tin = tout = 0
    run.status = RunStatus.scoring

    if llm.grok_available(cfg):
        try:
            system = prompt_text("scorer") + "\n\n# Playbook\n" + playbook.context()
            payload = [o.model_dump() for o in run.opportunities]
            user = f"Score opportunities:\n{payload}"
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict) and data.get("scores"):
                run.scores = _parse_scores(data["scores"], cfg)
                _mark_at_risk(run, cfg)
                return run, tin, tout
        except Exception as e:
            run.metadata["scorer_error"] = str(e)

    run.scores = _rule_score(run.opportunities, cfg)
    _mark_at_risk(run, cfg)
    return run, tin, tout


def _parse_scores(raw: list[Any], cfg: dict) -> list[ScoreCard]:
    out: list[ScoreCard] = []
    scoring = cfg.get("scoring") or {}
    hot = float(scoring.get("hot_min", 75))
    warm = float(scoring.get("warm_min", 50))
    for row in raw:
        score = float(row.get("score") or 0)
        tier = str(row.get("tier") or _tier(score, hot, warm))
        out.append(
            ScoreCard(
                opportunity_id=str(row.get("opportunity_id") or ""),
                score=score,
                fit=float(row.get("fit") or 0),
                engagement=float(row.get("engagement") or 0),
                behavior=float(row.get("behavior") or 0),
                urgency=float(row.get("urgency") or 0),
                tier=tier,
                rationale=str(row.get("rationale") or ""),
            )
        )
    return out


def _tier(score: float, hot: float, warm: float) -> str:
    if score >= hot:
        return "hot"
    if score >= warm:
        return "warm"
    return "cold"


def _mark_at_risk(run: PipelineRun, cfg: dict) -> None:
    scoring = cfg.get("scoring") or {}
    max_score = float(scoring.get("at_risk_score_max", 45))
    stale = int(scoring.get("stale_days", 14))
    by_id = {o.id: o for o in run.opportunities}
    for s in run.scores:
        o = by_id.get(s.opportunity_id)
        stale_flag = o is not None and o.last_activity_days >= stale
        late_stage = o is not None and o.stage.lower() in {
            "proposal",
            "negotiation",
        }
        s.at_risk = s.score <= max_score or (stale_flag and late_stage)


def _rule_score(opps: list[Opportunity], cfg: dict) -> list[ScoreCard]:
    scoring = cfg.get("scoring") or {}
    w = scoring.get("weights") or {}
    wf = float(w.get("fit", 0.35))
    we = float(w.get("engagement", 0.30))
    wb = float(w.get("behavior", 0.25))
    wu = float(w.get("urgency", 0.10))
    hot = float(scoring.get("hot_min", 75))
    warm = float(scoring.get("warm_min", 50))
    high_amt = float(scoring.get("high_value_amount", 10000))
    fit_cfg = scoring.get("fit_signals") or {}
    industries = [x.lower() for x in (fit_cfg.get("industries") or [])]
    titles = [x.lower() for x in (fit_cfg.get("titles") or [])]
    bands = [x.lower() for x in (fit_cfg.get("employee_bands") or [])]
    eng_boosts = scoring.get("engagement_boosts") or {}
    penalties = scoring.get("behavior_penalties") or {}
    stale = int(scoring.get("stale_days", 14))

    out: list[ScoreCard] = []
    for o in opps:
        fit = 40.0
        ind = (o.industry or "").lower()
        title = (o.contact_title or "").lower()
        emp = (o.employees or "").lower()
        if any(i in ind for i in industries):
            fit += 25
        if any(t in title for t in titles):
            fit += 20
        if any(b == emp or b in emp for b in bands):
            fit += 10
        if o.amount >= high_amt:
            fit += 10
        fit = min(100.0, fit)

        eng = 20.0
        for sig in o.signals or []:
            eng += float(eng_boosts.get(sig, 0))
        eng = min(100.0, eng)

        beh = 70.0
        days = int(o.last_activity_days or 0)
        if days >= 14:
            beh += float(penalties.get("no_activity_days_14", -18))
        elif days >= 7:
            beh += float(penalties.get("no_activity_days_7", -8))
        notes = (o.notes or "").lower()
        if "competitor" in notes:
            beh += float(penalties.get("competitor_mentioned", -5))
        if "budget unknown" in notes or "budget unknown" in notes:
            beh += float(penalties.get("budget_unknown", -6))
        beh = max(0.0, min(100.0, beh))

        urg = 30.0
        if o.stage.lower() in {"proposal", "negotiation"}:
            urg += 35
        if days <= 3:
            urg += 25
        if o.amount >= high_amt:
            urg += 10
        urg = min(100.0, urg)

        score = round(fit * wf + eng * we + beh * wb + urg * wu, 1)
        tier = _tier(score, hot, warm)
        rationale = (
            f"Fit {fit:.0f}/eng {eng:.0f}/beh {beh:.0f}/urg {urg:.0f}; "
            f"stage={o.stage}, last_touch={days}d"
        )
        at_risk = score <= float(scoring.get("at_risk_score_max", 45)) or (
            days >= stale and o.stage.lower() in {"proposal", "negotiation"}
        )
        out.append(
            ScoreCard(
                opportunity_id=o.id,
                score=score,
                fit=fit,
                engagement=eng,
                behavior=beh,
                urgency=urg,
                tier=tier,
                rationale=rationale,
                at_risk=at_risk,
            )
        )
    out.sort(key=lambda s: s.score, reverse=True)
    return out

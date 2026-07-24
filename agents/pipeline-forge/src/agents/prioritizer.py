"""Prioritizer agent — daily/weekly rep lists."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import Opportunity, PipelineRun, PriorityItem, RunStatus, ScoreCard


def run_prioritizer(run: PipelineRun, cfg: dict) -> tuple[PipelineRun, int, int]:
    tin = tout = 0
    run.status = RunStatus.prioritizing
    limit = int((cfg.get("pipeline") or {}).get("list_size") or 15)

    if llm.grok_available(cfg):
        try:
            system = prompt_text("prioritizer")
            user = (
                f"Cadence: {run.cadence}\n"
                f"Scores: {[s.model_dump() for s in run.scores]}\n"
                f"Opportunities: {[o.model_dump() for o in run.opportunities]}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict) and data.get("items"):
                run.list_title = str(data.get("list_title") or f"{run.cadence.title()} priorities")
                run.notes = str(data.get("notes") or "")
                run.priority_list = _parse_items(data["items"], run, limit)
                return run, tin, tout
        except Exception as e:
            run.metadata["prioritizer_error"] = str(e)

    data = _rule_priority(run, cfg, limit)
    run.list_title = data["list_title"]
    run.notes = data.get("notes") or ""
    run.priority_list = data["items"]
    return run, tin, tout


def _parse_items(raw: list[Any], run: PipelineRun, limit: int) -> list[PriorityItem]:
    by_id = {o.id: o for o in run.opportunities}
    scores = {s.opportunity_id: s for s in run.scores}
    out: list[PriorityItem] = []
    for i, row in enumerate(raw[:limit], start=1):
        oid = str(row.get("opportunity_id") or "")
        o = by_id.get(oid)
        sc = scores.get(oid)
        out.append(
            PriorityItem(
                rank=int(row.get("rank") or i),
                opportunity_id=oid,
                rep=str(row.get("rep") or (o.owner if o else "")),
                why=str(row.get("why") or ""),
                next_action=str(row.get("next_action") or ""),
                due=str(row.get("due") or "today"),
                score=float(sc.score if sc else 0),
                name=o.name if o else oid,
            )
        )
    return out


def _rule_priority(run: PipelineRun, cfg: dict, limit: int) -> dict[str, Any]:
    by_id = {o.id: o for o in run.opportunities}
    ordered = sorted(run.scores, key=lambda s: (s.at_risk, s.score), reverse=True)
    # Prefer high score; surface at-risk late-stage next
    hot_first = sorted(
        run.scores,
        key=lambda s: (
            1 if s.tier == "hot" else 0,
            1 if s.at_risk else 0,
            s.score,
        ),
        reverse=True,
    )
    items: list[PriorityItem] = []
    for i, sc in enumerate(hot_first[:limit], start=1):
        o = by_id.get(sc.opportunity_id)
        if not o:
            continue
        if sc.at_risk:
            action = "Re-engage decision maker with risk-recovery call"
            due = "ASAP"
            why = f"At-risk ({sc.score}): {sc.rationale}"
        elif sc.tier == "hot":
            action = "Push next commercial step (proposal / mutual close plan)"
            due = "today"
            why = f"Hot deal — {sc.rationale}"
        else:
            action = "Send value touch + book next meeting"
            due = "this_week"
            why = sc.rationale
        items.append(
            PriorityItem(
                rank=i,
                opportunity_id=o.id,
                rep=o.owner,
                why=why,
                next_action=action,
                due=due,
                score=sc.score,
                name=o.name,
            )
        )
    return {
        "list_title": f"{run.cadence.title()} sales priorities",
        "items": items,
        "notes": "Rule-based ranking (set XAI_API_KEY for LLM prioritization).",
    }

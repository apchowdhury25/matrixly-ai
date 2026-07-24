"""CRM mapper — stage/task/note suggestions."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import CrmUpdate, PipelineRun, RunStatus


def run_crm_mapper(run: PipelineRun, cfg: dict) -> tuple[PipelineRun, int, int]:
    tin = tout = 0
    run.status = RunStatus.crm_mapped

    if llm.grok_available(cfg):
        try:
            system = prompt_text("crm_mapper")
            user = (
                f"Priority: {[p.model_dump() for p in run.priority_list[:10]]}\n"
                f"Risks: {[r.model_dump() for r in run.risks]}\n"
                f"Scores: {[s.model_dump() for s in run.scores]}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict) and data.get("updates") is not None:
                run.crm_updates = _parse(data["updates"])
                return run, tin, tout
        except Exception as e:
            run.metadata["crm_mapper_error"] = str(e)

    run.crm_updates = _rule_updates(run, cfg)
    return run, tin, tout


def _parse(raw: list[Any]) -> list[CrmUpdate]:
    out: list[CrmUpdate] = []
    for row in raw:
        out.append(
            CrmUpdate(
                opportunity_id=str(row.get("opportunity_id") or ""),
                action=str(row.get("action") or "add_note"),
                stage=row.get("stage"),
                task_subject=row.get("task_subject"),
                note=row.get("note"),
                confidence=float(row.get("confidence") or 0.5),
            )
        )
    return out


def _rule_updates(run: PipelineRun, cfg: dict) -> list[CrmUpdate]:
    by_name = {o.id: o for o in run.opportunities}
    scores = {s.opportunity_id: s for s in run.scores}
    updates: list[CrmUpdate] = []

    for item in run.priority_list[:8]:
        o = by_name.get(item.opportunity_id)
        sc = scores.get(item.opportunity_id)
        if not o:
            continue
        updates.append(
            CrmUpdate(
                opportunity_id=o.id,
                action="create_task",
                task_subject=item.next_action[:120],
                note=f"PipelineForge priority #{item.rank}: {item.why}",
                confidence=0.8 if sc and sc.tier == "hot" else 0.65,
            )
        )

    for risk in run.risks:
        if risk.risk_level != "high":
            continue
        o = by_name.get(risk.opportunity_id)
        if not o:
            continue
        updates.append(
            CrmUpdate(
                opportunity_id=o.id,
                action="add_note",
                note="AT RISK: " + "; ".join(risk.reasons) + " | Actions: " + "; ".join(risk.suggested_actions),
                confidence=0.85,
            )
        )
        if o.stage.lower() == "proposal" and o.last_activity_days >= 14:
            updates.append(
                CrmUpdate(
                    opportunity_id=o.id,
                    action="update_stage",
                    stage="discovery",
                    note="Suggested re-open discovery due to stale proposal",
                    confidence=0.55,
                )
            )

    # de-dupe by (opp, action, stage/task)
    seen: set[str] = set()
    unique: list[CrmUpdate] = []
    for u in updates:
        key = f"{u.opportunity_id}:{u.action}:{u.stage}:{u.task_subject}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(u)
    return unique

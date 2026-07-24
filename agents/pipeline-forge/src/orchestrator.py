"""LangGraph/Crew-style pipeline: Score → Prioritize → Risk → CRM map → Insights + HITL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agents.crm_mapper import run_crm_mapper
from .agents.insights import run_insights
from .agents.prioritizer import run_prioritizer
from .agents.risk import run_risk
from .agents.scorer import run_scorer
from .integrations.crm import CrmClient
from .llm import cost_usd, grok_available
from .memory.playbook import PlaybookMemory
from .models import Opportunity, PipelineRun, RunStatus, new_id
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.store import PipelineStore
from .services.usage import UsageMeter


class PipelineForge:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.store = PipelineStore(data)
        self.hitl = HitlQueue(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.playbook = PlaybookMemory(data, cfg)
        self.crm = CrmClient(data, cfg)
        self.samples = Path(cfg["paths"]["samples"])

    def analyze(
        self,
        opportunities: list[dict[str, Any]] | list[Opportunity] | None = None,
        *,
        cadence: str = "daily",
        source: str = "payload",
        metadata: dict[str, Any] | None = None,
    ) -> PipelineRun:
        opps = self._resolve_opportunities(opportunities, source)
        run = PipelineRun(
            id=new_id("run_"),
            status=RunStatus.received,
            cadence=cadence or (self.cfg.get("pipeline") or {}).get("cadence") or "daily",
            opportunities=opps,
            metadata=metadata or {"source": source},
        )
        self.store.save(run)
        self.audit.write("run_received", run_id=run.id, count=len(opps), source=source)

        tin = tout = 0

        run, a, b = run_scorer(run, self.cfg, self.playbook)
        tin += a
        tout += b
        self.store.save(run)
        self.audit.write("scored", run_id=run.id, scores=len(run.scores))

        run, a, b = run_prioritizer(run, self.cfg)
        tin += a
        tout += b
        self.store.save(run)
        self.audit.write("prioritized", run_id=run.id, items=len(run.priority_list))

        run, a, b = run_risk(run, self.cfg)
        tin += a
        tout += b
        self.store.save(run)
        self.audit.write("risk_flagged", run_id=run.id, risks=len(run.risks))

        run, a, b = run_crm_mapper(run, self.cfg)
        tin += a
        tout += b
        self.store.save(run)
        self.audit.write("crm_mapped", run_id=run.id, updates=len(run.crm_updates))

        run, a, b = run_insights(run, self.cfg)
        tin += a
        tout += b

        run.usage_tokens_in = tin
        run.usage_tokens_out = tout
        run.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)
        self.store.export(run)

        require = (self.cfg.get("pipeline") or {}).get("require_hitl_before_crm_write", True)
        mode = (self.cfg.get("hitl") or {}).get("mode") or "external_only"
        auto = (self.cfg.get("hitl") or {}).get("auto_approve")
        if require and mode != "off" and not auto and run.crm_updates:
            action = self.hitl.enqueue(
                kind="crm_write_review",
                payload={
                    "list_title": run.list_title,
                    "priority_top": [p.model_dump() for p in run.priority_list[:5]],
                    "risks": len(run.risks),
                    "crm_updates": len(run.crm_updates),
                    "health": (run.insights or {}).get("health_score"),
                },
                run_id=run.id,
            )
            run.hitl_id = action.id
            run.status = RunStatus.pending_review
            self.audit.write("hitl_queued", run_id=run.id, hitl_id=action.id)
        else:
            if run.crm_updates and (auto or mode == "off" or not require):
                run.crm_updates = self.crm.apply_updates(run.crm_updates)
                run.status = RunStatus.applied
                self.audit.write("crm_auto_applied", run_id=run.id)
            else:
                run.status = RunStatus.applied
                self.audit.write("run_complete_no_crm", run_id=run.id)

        self.store.save(run)
        self.usage.record(
            action="analyze",
            tokens_in=tin,
            tokens_out=tout,
            run_id=run.id,
        )
        self.audit.write("pipeline_complete", run_id=run.id, status=run.status.value)
        return run

    def demo(self) -> PipelineRun:
        return self.analyze(source="sample", cadence="daily")

    def approve(self, action_id: str, decided_by: str = "admin") -> PipelineRun | None:
        action = self.hitl.decide(action_id, approve=True, decided_by=decided_by)
        if not action or not action.run_id:
            return None
        run = self.store.get(action.run_id)
        if not run:
            return None
        run.crm_updates = self.crm.apply_updates(run.crm_updates)
        run.status = RunStatus.applied
        self.store.save(run)
        self.audit.write("hitl_approved_crm", run_id=run.id, hitl_id=action_id)
        self.usage.record(action="crm_apply", run_id=run.id)
        return run

    def reject(self, action_id: str, decided_by: str = "admin") -> PipelineRun | None:
        action = self.hitl.decide(action_id, approve=False, decided_by=decided_by)
        if not action or not action.run_id:
            return None
        run = self.store.get(action.run_id)
        if not run:
            return None
        run.status = RunStatus.rejected
        self.store.save(run)
        self.audit.write("hitl_rejected", run_id=run.id, hitl_id=action_id)
        return run

    def apply_crm(self, run_id: str, indexes: list[int] | None = None) -> PipelineRun | None:
        run = self.store.get(run_id)
        if not run:
            return None
        if run.status == RunStatus.pending_review:
            self.audit.write("crm_blocked_hitl", run_id=run.id)
            return run
        updates = run.crm_updates
        if indexes:
            updates = [updates[i] for i in indexes if 0 <= i < len(updates)]
        applied = self.crm.apply_updates(updates)
        # merge results back
        by_key = {(u.opportunity_id, u.action, u.task_subject): u for u in applied}
        for i, u in enumerate(run.crm_updates):
            k = (u.opportunity_id, u.action, u.task_subject)
            if k in by_key:
                run.crm_updates[i] = by_key[k]
        run.status = RunStatus.applied
        self.store.save(run)
        self.audit.write("crm_applied", run_id=run.id, count=len(applied))
        return run

    def status(self) -> dict[str, Any]:
        runs = self.store.list(limit=200)
        pending = self.hitl.list_pending()
        latest = runs[0] if runs else None
        return {
            "service": "pipeline-forge",
            "version": "1.0.0",
            "grok": grok_available(self.cfg),
            "runs": len(runs),
            "pending_review": len(pending),
            "crm_backend": (self.cfg.get("crm") or {}).get("backend"),
            "latest_run": latest.id if latest else None,
            "latest_health": (latest.insights or {}).get("health_score") if latest else None,
            "usage": self.usage.summary(days=30),
        }

    def _resolve_opportunities(
        self,
        opportunities: list[dict[str, Any]] | list[Opportunity] | None,
        source: str,
    ) -> list[Opportunity]:
        if opportunities:
            out: list[Opportunity] = []
            for row in opportunities:
                if isinstance(row, Opportunity):
                    out.append(row)
                else:
                    rid = str(row.get("id") or new_id("opp_"))
                    out.append(Opportunity(id=rid, **{k: v for k, v in row.items() if k != "id"}))
            self.crm.seed_local(out)
            return out

        if source == "crm":
            loaded = self.crm.load_opportunities()
            if loaded:
                return loaded

        # sample
        sample = self.samples / "pipeline.json"
        if sample.exists():
            data = json.loads(sample.read_text(encoding="utf-8"))
            opps = [Opportunity(**row) for row in data]
            self.crm.seed_local(opps)
            return opps

        return [
            Opportunity(
                id="opp_demo",
                name="Demo Opportunity",
                account="Demo Co",
                amount=5000,
                stage="discovery",
                owner="Rep",
                last_activity_days=2,
                signals=["email_open"],
            )
        ]

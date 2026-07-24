"""Crew-style multi-agent orchestrator: Researcher → Writer → Editor → Repurposer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agents.editor import run_editor
from .agents.repurposer import run_repurposer
from .agents.researcher import run_researcher
from .agents.writer import run_writer
from .config import brand_voice_text
from .integrations.publish import Publisher
from .llm import cost_usd, grok_available
from .models import ContentJob, JobStatus, new_id
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.store import JobStore
from .services.usage import UsageMeter


class ContentForge:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.store = JobStore(data)
        self.hitl = HitlQueue(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.publisher = Publisher(cfg)
        self.samples = Path(cfg["paths"]["samples"])

    def generate(
        self,
        source_text: str,
        *,
        source_title: str = "",
        goal: str = "",
        audience: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ContentJob:
        job = ContentJob(
            id=new_id("job_"),
            status=JobStatus.received,
            source_text=source_text.strip(),
            source_title=source_title.strip(),
            goal=goal or "Educate SMBs and drive marketplace engagement",
            audience=audience or "SMB founders and operators",
            metadata=metadata or {},
        )
        self.store.save(job)
        self.audit.write("job_received", job_id=job.id)

        tin = tout = 0

        job, a, b = run_researcher(job, self.cfg)
        tin += a
        tout += b
        self.store.save(job)
        self.audit.write("researched", job_id=job.id)

        job, a, b = run_writer(job, self.cfg)
        tin += a
        tout += b
        self.store.save(job)
        self.audit.write("wrote", job_id=job.id)

        job, a, b = run_editor(job, self.cfg)
        tin += a
        tout += b
        self.store.save(job)
        self.audit.write("edited", job_id=job.id, quality=job.quality_score)

        job, a, b = run_repurposer(job, self.cfg)
        tin += a
        tout += b
        job.usage_tokens_in = tin
        job.usage_tokens_out = tout
        job.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)

        paths = self.store.export_job(job)

        # HITL before publish
        require = (self.cfg.get("content") or {}).get("require_hitl_before_publish", True)
        mode = (self.cfg.get("hitl") or {}).get("mode") or "external_only"
        auto = (self.cfg.get("hitl") or {}).get("auto_approve")
        if require and mode != "off" and not auto:
            action = self.hitl.enqueue(
                kind="content_review",
                payload={
                    "title": (job.edited or {}).get("title"),
                    "quality_score": job.quality_score,
                    "assets": list((job.assets or {}).keys()),
                },
                job_id=job.id,
            )
            job.hitl_id = action.id
            job.status = JobStatus.pending_review
            self.audit.write("hitl_queued", job_id=job.id, hitl_id=action.id)
        else:
            job.status = JobStatus.approved
            self.audit.write("auto_approved", job_id=job.id)

        self.store.save(job)
        self.usage.record(
            action="generate",
            tokens_in=tin,
            tokens_out=tout,
            job_id=job.id,
        )
        self.audit.write(
            "pipeline_complete",
            job_id=job.id,
            status=job.status.value,
            exports=len(paths),
        )
        return job

    def suggest_ideas(self, business_input: str, count: int = 5) -> dict[str, Any]:
        from . import llm
        from .config import prompt_text

        brand = brand_voice_text(self.cfg)
        if llm.grok_available(self.cfg):
            try:
                system = (
                    "You suggest content ideas for an SMB brand. Return JSON: "
                    '{"ideas":[{"title":"...","channel":"...","angle":"..."}]}'
                )
                user = f"Brand:\n{brand[:2000]}\n\nBusiness input:\n{business_input}\nCount:{count}"
                content, tin, tout = llm.chat(self.cfg, system, user, temperature=0.6)
                data = llm.extract_json(content)
                self.usage.record(action="ideas", tokens_in=tin, tokens_out=tout)
                return data if isinstance(data, dict) else {"ideas": []}
            except Exception as e:
                return {"ideas": [], "error": str(e)}

        base = [
            {
                "title": "5 ops tasks to hand to an AI agent this week",
                "channel": "blog",
                "angle": business_input[:80],
            },
            {
                "title": "Human-in-the-loop vs full auto: a practical guide",
                "channel": "linkedin",
                "angle": "trust",
            },
            {
                "title": "From dashboard fatigue to agent marketplace",
                "channel": "newsletter",
                "angle": "narrative",
            },
            {
                "title": "Pilot checklist for your first Matrixly agent",
                "channel": "carousel",
                "angle": "howto",
            },
            {
                "title": "Customer story template: time saved after automation",
                "channel": "case study",
                "angle": "social proof",
            },
        ]
        return {"ideas": base[: max(1, min(count, 8))]}

    def approve(self, hitl_id: str, decided_by: str = "admin") -> ContentJob | None:
        action = self.hitl.decide(hitl_id, approve=True, decided_by=decided_by)
        if not action or not action.job_id:
            return None
        job = self.store.get(action.job_id)
        if not job:
            return None
        job.status = JobStatus.approved
        self.store.save(job)
        self.audit.write("approved", job_id=job.id, hitl_id=hitl_id)
        return job

    def reject(self, hitl_id: str, decided_by: str = "admin") -> ContentJob | None:
        action = self.hitl.decide(hitl_id, approve=False, decided_by=decided_by)
        if not action or not action.job_id:
            return None
        job = self.store.get(action.job_id)
        if not job:
            return None
        job.status = JobStatus.rejected
        self.store.save(job)
        self.audit.write("rejected", job_id=job.id, hitl_id=hitl_id)
        return job

    def publish(self, job_id: str, targets: list[str] | None = None) -> dict[str, Any]:
        job = self.store.get(job_id)
        if not job:
            return {"ok": False, "reason": "job not found"}
        if job.status not in {JobStatus.approved, JobStatus.scheduled, JobStatus.published}:
            return {"ok": False, "reason": f"job status {job.status.value} not publishable"}
        result = self.publisher.publish(job, targets=targets)
        if result.get("ok"):
            job.status = JobStatus.published
            job.published_to = [
                r.get("backend") for r in result.get("results") or [] if r.get("ok")
            ]
            self.store.save(job)
            self.audit.write("published", job_id=job.id, targets=job.published_to)
        return result

    def schedule(
        self,
        job_id: str,
        run_at: str,
        channel: str = "blog",
        content_key: str = "blog",
    ) -> dict[str, Any]:
        job = self.store.get(job_id)
        if not job:
            return {"ok": False, "reason": "job not found"}
        if job.status == JobStatus.pending_review:
            return {"ok": False, "reason": "approve HITL first"}
        item = {
            "job_id": job_id,
            "run_at": run_at,
            "channel": channel,
            "content_key": content_key,
            "status": "scheduled",
        }
        path = self.store.schedule(item)
        job.status = JobStatus.scheduled
        job.scheduled_at = run_at
        self.store.save(job)
        self.audit.write("scheduled", job_id=job_id, run_at=run_at, path=str(path))
        return {"ok": True, "schedule": item}

    def demo(self) -> ContentJob:
        sample = self.samples / "source_blog.txt"
        text = sample.read_text(encoding="utf-8") if sample.exists() else "Agentic AI for SMBs."
        return self.generate(
            text,
            source_title="Why SMBs Need Agentic AI",
            goal="Drive Matrixly marketplace exploration",
            audience="SMB founders and ops leads",
        )

    def status(self) -> dict[str, Any]:
        jobs = self.store.list(limit=100)
        return {
            "version": "1.0.0",
            "business": (self.cfg.get("business") or {}).get("name"),
            "grok": grok_available(self.cfg),
            "jobs": len(jobs),
            "pending_review": len([j for j in jobs if j.status == JobStatus.pending_review]),
            "pending_hitl": len(self.hitl.list_pending()),
            "publish_backend": self.publisher.backend,
            "usage": self.usage.summary(days=7),
        }

"""SEOForge multi-agent orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import llm
from .agents.auditor import run_auditor
from .agents.local_seo import run_local_seo
from .agents.researcher import run_researcher
from .agents.strategist import run_strategist
from .agents.writer import run_writer
from .config import prompt_text
from .integrations.publish import Publisher
from .llm import cost_usd, grok_available
from .memory.brand import BrandMemory
from .models import ChatSession, JobStatus, SeoJob, new_id
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.keywords import KeywordStore
from .services.roi import RoiLedger
from .services.sessions import SessionStore
from .services.store import JobStore
from .services.usage import UsageMeter


class SEOForge:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.store = JobStore(data)
        self.hitl = HitlQueue(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.keywords = KeywordStore(data)
        self.roi = RoiLedger(data)
        self.sessions = SessionStore(data)
        self.brand = BrandMemory(cfg)
        self.publisher = Publisher(cfg)
        self.samples = Path(cfg["paths"]["samples"])

    def _roi_snapshot(self, job: SeoJob, hours: float = 1.5) -> dict[str, Any]:
        snap = {
            "hours_saved_this_cycle": hours,
            "expected_ranking_lift": "Incremental movement on target keywords over 30–90 days",
            "expected_lead_lift": "Supports more qualified organic/local inquiries when published",
            "confidence": job.confidence or 0.7,
            "job_id": job.id,
        }
        job.roi_snapshot = snap
        self.roi.record(
            hours_saved=hours,
            leads_attributed=0,
            revenue_usd=0.0,
            note=f"Cycle complete: {job.kind} {job.id}",
            job_id=job.id,
            source="pipeline",
        )
        return snap

    def _maybe_hitl(self, job: SeoJob, kind: str, payload: dict[str, Any]) -> SeoJob:
        require = (self.cfg.get("seo") or {}).get("require_hitl_before_publish", True)
        mode = (self.cfg.get("hitl") or {}).get("mode") or "external_only"
        auto = (self.cfg.get("hitl") or {}).get("auto_approve")
        if require and mode != "off" and not auto and kind in {
            "content",
            "local",
        }:
            action = self.hitl.enqueue(kind=f"seo_{kind}_review", payload=payload, job_id=job.id)
            job.hitl_id = action.id
            job.status = JobStatus.pending_review
            self.audit.write("hitl_queued", job_id=job.id, hitl_id=action.id)
        else:
            job.status = JobStatus.approved
            self.audit.write("auto_approved", job_id=job.id)
        return job

    def create_plan(
        self,
        business_input: str,
        *,
        primary_goal: str = "organic_leads",
        service_areas: list[str] | None = None,
        business_type: str = "",
    ) -> SeoJob:
        profile = self.brand.get_profile()
        job = SeoJob(
            id=new_id("job_"),
            kind="plan",
            status=JobStatus.received,
            source_text=business_input.strip(),
            goal=primary_goal or profile.get("primary_goal") or "organic_leads",
            business_type=business_type or profile.get("business_type") or "",
            service_areas=service_areas or profile.get("service_areas") or [],
            title="30-day SEO plan",
        )
        self.store.save(job)
        tin = tout = 0
        job, a, b = run_researcher(job, self.cfg)
        tin += a
        tout += b
        self.store.save(job)
        job, a, b = run_strategist(job, self.cfg)
        tin += a
        tout += b
        # Seed keyword tracker from research
        kws = (job.research or {}).get("keywords") or []
        from .models import KeywordItem

        items = []
        for k in kws[:12]:
            if isinstance(k, dict) and k.get("keyword"):
                items.append(
                    KeywordItem(
                        keyword=k["keyword"],
                        intent=k.get("intent") or "local",
                        priority=k.get("priority") or "medium",
                        city=(job.service_areas[0] if job.service_areas else ""),
                        notes=k.get("rationale") or "",
                    )
                )
        if items:
            self.keywords.upsert(items)

        job.usage_tokens_in = tin
        job.usage_tokens_out = tout
        job.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)
        job.status = JobStatus.approved
        self._roi_snapshot(job, hours=2.0)
        self.store.export_job(job)
        self.store.save(job)
        self.usage.record(action="plan", tokens_in=tin, tokens_out=tout, job_id=job.id)
        self.audit.write("plan_complete", job_id=job.id)
        return job

    def generate_content(
        self,
        brief: str,
        *,
        content_type: str = "blog",
        primary_keyword: str = "",
        service_areas: list[str] | None = None,
        goal: str = "",
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SeoJob:
        profile = self.brand.get_profile()
        meta = metadata or {}
        if primary_keyword:
            meta["primary_keyword"] = primary_keyword
        job = SeoJob(
            id=new_id("job_"),
            kind="content",
            status=JobStatus.received,
            source_text=brief.strip(),
            content_type=content_type,
            goal=goal or profile.get("primary_goal") or "organic_leads",
            business_type=profile.get("business_type") or "",
            service_areas=service_areas or profile.get("service_areas") or [],
            title=title,
            metadata=meta,
        )
        self.store.save(job)
        tin = tout = 0
        job, a, b = run_researcher(job, self.cfg)
        tin += a
        tout += b
        self.store.save(job)
        job, a, b = run_writer(job, self.cfg)
        tin += a
        tout += b
        job.usage_tokens_in = tin
        job.usage_tokens_out = tout
        job.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)
        draft = job.draft or {}
        job = self._maybe_hitl(
            job,
            "content",
            {
                "title": draft.get("title"),
                "content_type": content_type,
                "primary_keyword": draft.get("primary_keyword") or primary_keyword,
                "confidence": job.confidence,
            },
        )
        self._roi_snapshot(job, hours=1.5)
        self.store.export_job(job)
        self.store.save(job)
        self.usage.record(action="generate", tokens_in=tin, tokens_out=tout, job_id=job.id)
        self.audit.write("content_complete", job_id=job.id, status=job.status.value)
        return job

    def audit_page(
        self,
        page_text: str,
        *,
        url_or_title: str = "",
        primary_keyword: str = "",
    ) -> SeoJob:
        job = SeoJob(
            id=new_id("job_"),
            kind="audit",
            status=JobStatus.received,
            source_text=page_text.strip(),
            title=url_or_title or "Page audit",
            metadata={"primary_keyword": primary_keyword},
        )
        self.store.save(job)
        job, tin, tout = run_auditor(job, self.cfg)
        job.usage_tokens_in = tin
        job.usage_tokens_out = tout
        job.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)
        job.status = JobStatus.approved
        self._roi_snapshot(job, hours=0.75)
        self.store.export_job(job)
        self.store.save(job)
        self.usage.record(action="audit", tokens_in=tin, tokens_out=tout, job_id=job.id)
        return job

    def local_package(
        self,
        business_input: str,
        *,
        service_areas: list[str] | None = None,
        gbp_notes: str = "",
    ) -> SeoJob:
        profile = self.brand.get_profile()
        job = SeoJob(
            id=new_id("job_"),
            kind="local",
            status=JobStatus.received,
            source_text=business_input.strip(),
            business_type=profile.get("business_type") or "",
            service_areas=service_areas or profile.get("service_areas") or [],
            title="Local SEO package",
            metadata={"gbp_notes": gbp_notes},
        )
        self.store.save(job)
        tin = tout = 0
        job, a, b = run_researcher(job, self.cfg)
        tin += a
        tout += b
        job, a, b = run_local_seo(job, self.cfg)
        tin += a
        tout += b
        job.usage_tokens_in = tin
        job.usage_tokens_out = tout
        job.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)
        job = self._maybe_hitl(
            job,
            "local",
            {
                "title": "GBP / local SEO package",
                "areas": job.service_areas,
                "confidence": job.confidence,
            },
        )
        self._roi_snapshot(job, hours=1.25)
        self.store.export_job(job)
        self.store.save(job)
        self.usage.record(action="local", tokens_in=tin, tokens_out=tout, job_id=job.id)
        return job

    def chat(self, message: str, session_id: str | None = None, profile: dict | None = None) -> dict[str, Any]:
        if session_id:
            session = self.sessions.get(session_id)
            if not session:
                session = self.sessions.create(profile or self.brand.get_profile())
        else:
            session = self.sessions.create(profile or self.brand.get_profile())
        if profile:
            session.profile = {**session.profile, **profile}
            self.brand.save_profile(session.profile)
            self.sessions.save(session)

        self.sessions.append(session, "user", message.strip())
        reply, tin, tout, meta = self._chat_reply(session, message.strip())
        self.sessions.append(session, "assistant", reply, meta=meta)
        self.usage.record(action="chat", tokens_in=tin, tokens_out=tout, job_id=session.id)
        self.audit.write("chat", session_id=session.id)
        return {
            "session_id": session.id,
            "reply": reply,
            "meta": meta,
            "profile": session.profile,
            "messages": [m.model_dump() for m in session.messages[-20:]],
        }

    def _chat_reply(self, session: ChatSession, message: str) -> tuple[str, int, int, dict]:
        profile = session.profile or self.brand.get_profile()
        voice = self.brand.get_voice()
        system = prompt_text("system") + f"\n\n# Brand voice\n{voice[:2500]}\n\n# Client profile\n{profile}"

        missing = []
        if not profile.get("business_type"):
            missing.append("business type")
        if not profile.get("service_areas"):
            missing.append("service areas / cities")
        if not profile.get("website") and not profile.get("gbp_status"):
            missing.append("website or Google Business Profile status")
        if not profile.get("primary_goal"):
            missing.append("primary growth goal")

        if missing and len(session.messages) <= 2:
            reply = (
                "Welcome — I'm **SEOForge**, your Matrixly SEO & brand marketing teammate for US SMBs.\n\n"
                "Before I propose a 30-day plan, please confirm:\n"
                f"- Business type\n- Service areas (cities)\n- Website / Google Business Profile status\n"
                f"- Primary growth goal (e.g. more “near me” leads)\n\n"
                f"Still need: **{', '.join(missing)}**.\n\n"
                "You can also fill the Onboard form in the dashboard. "
                "I will not publish anything without your approval in the content queue."
            )
            return reply, 0, llm.estimate_tokens(reply), {"intent": "onboard", "confidence": 0.9}

        if llm.grok_available(self.cfg):
            try:
                history = "\n".join(
                    f"{m.role}: {m.content}" for m in session.messages[-8:]
                )
                user = f"Conversation:\n{history}\n\nLatest user message:\n{message}"
                content, tin, tout = llm.chat(self.cfg, system, user, temperature=0.45)
                return content, tin, tout, {"intent": "chat", "confidence": 0.8, "llm": True}
            except Exception as e:
                return self._rule_chat(message, profile, str(e)), 0, 0, {
                    "intent": "chat_fallback",
                    "error": str(e),
                }

        return self._rule_chat(message, profile), 0, 0, {"intent": "chat_fallback", "confidence": 0.72}

    def _rule_chat(self, message: str, profile: dict, error: str = "") -> str:
        low = message.lower()
        name = profile.get("business_name") or "your business"
        areas = profile.get("service_areas") or []
        city = areas[0] if areas else "your city"
        btype = profile.get("business_type") or "your business type"

        if any(w in low for w in ("plan", "30-day", "strategy", "roadmap")):
            return (
                f"**Proposed 30-day plan for {name}** ({btype} · {city})\n\n"
                "1. **Week 1** — Brand voice lock-in, page audit, GBP basics\n"
                "2. **Week 2** — Service + location pages for high-intent keywords\n"
                "3. **Week 3** — FAQ blog + GBP posts + review responses\n"
                "4. **Week 4** — Rank tracking + refresh + ROI snapshot\n\n"
                "Use **Create 30-day plan** in the dashboard to generate a full package, "
                "or reply **approve week 1** and I'll prepare the first content draft.\n\n"
                "⚠️ Nothing publishes without your approval.\n\n"
                "**ROI snapshot:** ~2 hours saved vs DIY planning · expected lift on 3–5 local keywords in 30–90 days."
            )
        if any(w in low for w in ("keyword", "rank", "ranking")):
            summary = self.keywords.summary()
            return (
                f"Keyword tracker: **{summary.get('total', 0)}** keywords "
                f"({summary.get('high_priority', 0)} high priority, "
                f"{summary.get('improved', 0)} improved).\n\n"
                "Open the **Keywords** tab to add service+city and near-me terms. "
                "I prioritize high-intent local queries that can move in 30–90 days."
            )
        if any(w in low for w in ("gbp", "google business", "local seo", "near me")):
            return (
                "I can build a **Local SEO package**: GBP description, posts, Q&A, "
                "review response templates, citation checklist, and a location-page outline.\n\n"
                "Use the **Local SEO** action in the dashboard or paste your GBP notes here. "
                "Publishing GBP updates still requires your approval."
            )
        if any(w in low for w in ("write", "blog", "service page", "content", "draft")):
            return (
                "I can draft SEO content in your brand voice with title, meta, outline, full draft, "
                "social variants, GBP post, and a publishing checklist.\n\n"
                "Use **Generate content** with a short brief (service + city + offer). "
                "Drafts land in the **Approval queue** before any publish."
            )
        if "roi" in low or "hours" in low:
            s = self.roi.summary()
            return (
                f"**ROI snapshot (SEOForge)**\n"
                f"- Hours saved: **{s.get('hours_saved', 0)}**\n"
                f"- Leads attributed: **{s.get('leads_attributed', 0)}**\n"
                f"- Revenue tied: **${s.get('revenue_usd', 0)}**\n\n"
                "These feed the Matrixly ROI dashboard. Log leads/revenue in the ROI tab when you close jobs."
            )
        err = f"\n\n_(LLM offline fallback{': ' + error if error else ''})_" if error or not grok_available(self.cfg) else ""
        return (
            f"I'm SEOForge — ready to help {name} grow organic and local visibility.\n\n"
            "I can: research keywords, build a 30-day plan, write brand-voice SEO pages, "
            "optimize Google Business Profile signals, audit pages, track keywords, and report ROI.\n\n"
            "Tell me your goal, or try: *“Create a 30-day plan for AC repair in Austin.”*"
            f"{err}"
        )

    def onboard(self, data: dict[str, Any]) -> dict[str, Any]:
        profile = self.brand.save_profile(data)
        self.audit.write("onboard", business=profile.get("business_name"))
        return {"ok": True, "profile": profile}

    def approve(self, hitl_id: str, decided_by: str = "admin") -> SeoJob | None:
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

    def reject(self, hitl_id: str, decided_by: str = "admin") -> SeoJob | None:
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
            return {"ok": False, "reason": f"job status {job.status.value} not publishable — approve HITL first"}
        result = self.publisher.publish(job, targets=targets)
        if result.get("ok"):
            job.status = JobStatus.published
            job.published_to = [
                r.get("backend") for r in result.get("results") or [] if r.get("ok")
            ]
            self.store.save(job)
            self.audit.write("published", job_id=job.id, targets=job.published_to)
        return result

    def schedule(self, job_id: str, run_at: str, channel: str = "blog") -> dict[str, Any]:
        job = self.store.get(job_id)
        if not job:
            return {"ok": False, "reason": "job not found"}
        if job.status == JobStatus.pending_review:
            return {"ok": False, "reason": "approve HITL first"}
        item = {
            "job_id": job_id,
            "run_at": run_at,
            "channel": channel,
            "status": "scheduled",
        }
        path = self.store.schedule(item)
        job.status = JobStatus.scheduled
        job.scheduled_at = run_at
        self.store.save(job)
        self.audit.write("scheduled", job_id=job_id, run_at=run_at, path=str(path))
        return {"ok": True, "schedule": item}

    def demo(self) -> SeoJob:
        sample = self.samples / "business_brief.txt"
        text = sample.read_text(encoding="utf-8") if sample.exists() else (
            "US HVAC company in Austin needing local SEO and service pages."
        )
        self.brand.save_profile(
            {
                "business_name": "Apex Comfort HVAC",
                "business_type": "Residential HVAC",
                "service_areas": ["Austin, TX", "Round Rock, TX"],
                "website": "https://example-apex-hvac.com",
                "gbp_status": "Active ~4.7 stars",
                "primary_goal": "near_me_leads",
            }
        )
        return self.generate_content(
            text,
            content_type="service_page",
            primary_keyword="AC repair Austin",
            service_areas=["Austin, TX", "Round Rock, TX"],
            goal="More AC repair near me leads",
            title="AC Repair in Austin, TX",
        )

    def status(self) -> dict[str, Any]:
        jobs = self.store.list(limit=100)
        return {
            "version": "1.0.0",
            "service": "seo-forge",
            "business": (self.cfg.get("business") or {}).get("name"),
            "profile": self.brand.get_profile(),
            "grok": grok_available(self.cfg),
            "jobs": len(jobs),
            "pending_review": len([j for j in jobs if j.status == JobStatus.pending_review]),
            "pending_hitl": len(self.hitl.list_pending()),
            "keywords": self.keywords.summary(),
            "roi": self.roi.summary(),
            "publish_backend": self.publisher.backend,
            "usage": self.usage.summary(days=7),
        }

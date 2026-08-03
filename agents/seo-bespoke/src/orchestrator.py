"""SEO-Bespoke orchestrator — quiz → parallel graph → custom agent package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .graph.executor import GraphExecutor
from .graph.topology import EDGES, GRAPH_DESCRIPTION
from .llm import cost_usd, grok_available
from .memory.brand import BrandMemory
from .models import (
    BusinessSeoProfile,
    ChatMessage,
    ChatSession,
    GraphRun,
    KeywordItem,
    QuizAnswers,
    RunStatus,
    new_id,
)
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.keywords import KeywordStore
from .services.package_store import PackageStore
from .services.profile_store import ProfileStore
from .services.roi import RoiLedger
from .services.sessions import SessionStore
from .services.store import RunStore
from .services.usage import UsageMeter


class SEOBespoke:
    """
    Higher-tier custom SEO agent factory.

    Flow:
      Quiz answers
        → Parallel graph (20 nodes)
        → Business SEO Profile Summary
        → Custom agent code package
        → HITL approval before deploy/publish
    """

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.runs = RunStore(data)
        self.profiles = ProfileStore(data)
        self.packages = PackageStore(data)
        self.hitl = HitlQueue(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.keywords = KeywordStore(data)
        self.roi = RoiLedger(data)
        self.sessions = SessionStore(data)
        self.brand = BrandMemory(cfg)
        self.executor = GraphExecutor(cfg)

    def status(self) -> dict[str, Any]:
        return {
            "service": "seo-bespoke",
            "version": "1.0.0",
            "graph": {
                "nodes": GRAPH_DESCRIPTION["node_count"],
                "edges": GRAPH_DESCRIPTION["edge_count"],
                "parallel_groups": GRAPH_DESCRIPTION["parallel_groups"],
                "verifiers": GRAPH_DESCRIPTION["verifiers"],
            },
            "runs": len(self.runs.list(limit=500)),
            "profiles": len(self.profiles.list(limit=500)),
            "packages": len(self.packages.list(limit=100)),
            "pending_review": len(self.hitl.list_pending()),
            "keywords": self.keywords.summary(),
            "roi": self.roi.summary(),
            "usage": self.usage.summary(),
            "grok": grok_available(self.cfg),
        }

    def graph_describe(self) -> dict[str, Any]:
        return {
            **GRAPH_DESCRIPTION,
            **self.executor.describe(),
        }

    def start_run(self, answers: QuizAnswers | dict | None = None) -> GraphRun:
        if isinstance(answers, dict):
            answers = QuizAnswers(**answers)
        run = GraphRun(
            id=new_id("run_"),
            status=RunStatus.received,
            quiz=answers or QuizAnswers(),
            graph_edges=[{"from": a, "to": b} for a, b in EDGES],
        )
        self.runs.save(run)
        self.audit.write("run_created", run_id=run.id)
        return run

    def run_full_pipeline(
        self,
        answers: QuizAnswers | dict,
        *,
        existing_run_id: str | None = None,
    ) -> GraphRun:
        """Execute the full 20-node parallel graph end-to-end."""
        if isinstance(answers, dict):
            answers = QuizAnswers(**answers)

        if existing_run_id:
            run = self.runs.get(existing_run_id)
            if not run:
                raise ValueError(f"run not found: {existing_run_id}")
            run.quiz = answers
        else:
            run = self.start_run(answers)

        run.status = RunStatus.quiz_collecting
        self.runs.save(run)

        bag, node_results = self.executor.execute(
            {
                "run_id": run.id,
                "quiz_raw": answers.model_dump(),
            }
        )
        run.node_results = node_results

        if any(n.status.value == "failed" for n in node_results):
            run.status = RunStatus.failed
            run.metadata["failed_nodes"] = [
                n.node_id for n in node_results if n.status.value == "failed"
            ]
            self.runs.save(run)
            self.audit.write("run_failed", run_id=run.id, failed=run.metadata["failed_nodes"])
            return run

        # Profile
        profile_data = bag.get("profile") or {}
        if profile_data:
            profile = BusinessSeoProfile(**profile_data)
            verification = bag.get("profile_verification") or {}
            profile.verification = verification
            self.profiles.save(profile)
            run.profile = profile
            run.profile_path = str(Path(self.cfg["paths"]["profiles"]) / f"{profile.id}.json")

            # Seed keyword tracker from profile (no ranks)
            items = []
            for k in profile.seed_keywords[:12]:
                if k.get("keyword"):
                    items.append(
                        KeywordItem(
                            keyword=k["keyword"],
                            intent=k.get("intent") or "local",
                            priority=k.get("priority") or "medium",
                            city=profile.primary_location or "",
                            notes=k.get("rationale") or "",
                            profile_id=profile.id,
                        )
                    )
            if items:
                self.keywords.upsert(items)

        run.architecture = bag.get("architecture") or {}
        run.generated_modules = {
            k: bag.get(k)
            for k in (
                "module_research",
                "module_brand",
                "module_local",
                "module_content",
                "module_tracking",
                "module_roi",
            )
            if bag.get(k)
        }
        run.verification = bag.get("profile_verification") or {}
        run.safety = bag.get("safety_report") or {}
        run.smoke = bag.get("smoke_report") or {}
        run.package = bag.get("final_manifest") or bag.get("deployment_package") or {}
        run.package_path = run.package.get("path")

        # HITL gate
        require = (self.cfg.get("seo") or {}).get("require_hitl_before_package_deploy", True)
        mode = (self.cfg.get("hitl") or {}).get("mode") or "external_only"
        auto = (self.cfg.get("hitl") or {}).get("auto_approve")
        smoke_ok = bool((run.smoke or {}).get("ok", True))
        safety_ok = bool((run.safety or {}).get("ok", True))

        if require and mode != "off" and not auto:
            action = self.hitl.enqueue(
                kind="bespoke_package_review",
                payload={
                    "run_id": run.id,
                    "profile_id": run.profile.id if run.profile else None,
                    "business_name": run.profile.business_name if run.profile else None,
                    "package_path": run.package_path,
                    "package_id": run.package.get("id"),
                    "safety_ok": safety_ok,
                    "smoke_ok": smoke_ok,
                    "file_count": run.package.get("file_count"),
                },
                run_id=run.id,
            )
            run.hitl_id = action.id
            run.status = RunStatus.pending_review
            self.audit.write("hitl_queued", run_id=run.id, hitl_id=action.id)
        else:
            run.status = RunStatus.completed if smoke_ok and safety_ok else RunStatus.failed

        # ROI: time saved building custom agent
        self.roi.record(
            hours_saved=4.0,
            leads_attributed=0,
            revenue_usd=0.0,
            note=f"Custom SEO agent package generated: {run.package.get('package_name')}",
            run_id=run.id,
            profile_id=run.profile.id if run.profile else None,
            source="pipeline",
        )

        self.runs.export_run(run)
        self.runs.save(run)
        self.usage.record(action="full_pipeline", run_id=run.id)
        self.audit.write(
            "pipeline_complete",
            run_id=run.id,
            status=run.status.value,
            package=run.package.get("id"),
        )
        return run

    def approve_hitl(
        self,
        hitl_id: str,
        *,
        decided_by: str = "owner",
        note: str = "",
    ) -> dict[str, Any]:
        action = self.hitl.decide(hitl_id, approve=True, decided_by=decided_by, note=note)
        if not action:
            return {"ok": False, "error": "not_found"}
        run_id = action.run_id
        if run_id:
            run = self.runs.get(run_id)
            if run:
                run.status = RunStatus.approved
                self.runs.save(run)
                self.audit.write("hitl_approved", run_id=run_id, hitl_id=hitl_id)
        return {"ok": True, "action": action.model_dump()}

    def reject_hitl(
        self,
        hitl_id: str,
        *,
        decided_by: str = "owner",
        note: str = "",
    ) -> dict[str, Any]:
        action = self.hitl.decide(hitl_id, approve=False, decided_by=decided_by, note=note)
        if not action:
            return {"ok": False, "error": "not_found"}
        run_id = action.run_id
        if run_id:
            run = self.runs.get(run_id)
            if run:
                run.status = RunStatus.rejected
                self.runs.save(run)
                self.audit.write("hitl_rejected", run_id=run_id, hitl_id=hitl_id)
        return {"ok": True, "action": action.model_dump()}

    def regenerate_from_profile(self, profile_id: str) -> GraphRun:
        """Re-run graph from a saved profile's quiz snapshot."""
        profile = self.profiles.get(profile_id)
        if not profile:
            raise ValueError(f"profile not found: {profile_id}")
        snap = profile.quiz_snapshot or {}
        # Reconstruct QuizAnswers-shaped dict from slices
        answers = QuizAnswers(
            domain=snap.get("domain") or {},
            industry=snap.get("industry") or {},
            business=snap.get("business") or {},
            customers={
                "primary_persona": (snap.get("customers") or {}).get("primary_persona")
                or ((snap.get("customers") or {}).get("personas") or [""])[0],
                "secondary_personas": (snap.get("customers") or {}).get("personas") or [],
                "pain_points": (snap.get("customers") or {}).get("pain_points") or [],
                "buying_triggers": (snap.get("customers") or {}).get("buying_triggers") or [],
                "decision_makers": (snap.get("customers") or {}).get("decision_makers") or "",
                "notes": (snap.get("customers") or {}).get("notes") or "",
            },
            location=snap.get("location") or {},
            goals=snap.get("goals") or {},
        )
        return self.run_full_pipeline(answers)

    def demo(self) -> GraphRun:
        """Built-in demo quiz for Apex Comfort HVAC-style business."""
        sample_path = Path(self.cfg["paths"]["samples"]) / "quiz_answers.json"
        if sample_path.exists():
            import json

            answers = QuizAnswers(**json.loads(sample_path.read_text(encoding="utf-8")))
        else:
            answers = QuizAnswers(
                domain={
                    "domain": "apexcomfort.example",
                    "website_url": "https://apexcomfort.example",
                    "has_blog": True,
                    "has_gbp": True,
                    "cms": "wordpress",
                },
                industry={
                    "industry": "Home services",
                    "niche": "Residential HVAC",
                    "sub_niches": ["AC repair", "furnace install"],
                },
                business={
                    "business_name": "Apex Comfort HVAC",
                    "description": "Family-owned HVAC serving Greater Austin with same-week repairs.",
                    "unique_value": "Licensed techs, upfront pricing, real humans on the phone.",
                    "products_services": ["AC repair", "AC install", "Furnace repair", "Maintenance plans"],
                    "differentiators": ["Upfront pricing", "Same-week availability"],
                    "years_in_business": 12,
                },
                customers={
                    "primary_persona": "Homeowners 30–60 in single-family homes",
                    "pain_points": ["AC fails in summer heat", "Unclear repair costs"],
                    "buying_triggers": ["System breakdown", "High energy bills"],
                },
                location={
                    "primary_city": "Austin",
                    "primary_region": "TX",
                    "service_areas": ["Austin, TX", "Round Rock, TX", "Cedar Park, TX"],
                    "service_radius_miles": 40,
                },
                goals={
                    "maturity": "basic",
                    "primary_goal": "near_me_leads",
                    "success_metric": "more booked service calls",
                    "timeline_days": 90,
                    "monthly_content_capacity": "2-4 pieces",
                },
                owner_name="Demo Owner",
            )
        return self.run_full_pipeline(answers)

    def chat(
        self,
        message: str,
        *,
        session_id: str | None = None,
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        """Lightweight owner chat — guides toward quiz / explains profile."""
        if not session_id:
            session_id = new_id("sess_")
        session = self.sessions.get(session_id) or ChatSession(id=session_id, profile_id=profile_id)
        session.messages.append(ChatMessage(role="user", content=message))

        profile = self.profiles.get(profile_id) if profile_id else self.profiles.latest()
        lower = message.lower()

        if any(w in lower for w in ("quiz", "start", "onboard", "setup")):
            reply = (
                "To build your custom SEO agent, complete the **Business Quiz** "
                "(Domain → Industry → Business → Customers → Location → Goals). "
                "Then we generate your Business SEO Profile and specialized agent code. "
                "Open the Quiz tab in the dashboard, or run: `python -m src.cli quiz`."
            )
        elif profile and any(w in lower for w in ("profile", "summary", "who am i")):
            reply = (
                f"**{profile.business_name}** — {profile.tagline}\n\n"
                f"Goal: {profile.primary_goal} · Maturity: {profile.seo_maturity}\n"
                f"Focus areas:\n"
                + "\n".join(f"• {f}" for f in (profile.recommended_focus or [])[:5])
                + "\n\nSay **regenerate** to rebuild your custom agent from this profile."
            )
        elif any(w in lower for w in ("regenerate", "rebuild", "update agent")):
            if profile:
                run = self.regenerate_from_profile(profile.id)
                reply = (
                    f"Regenerated custom agent package.\n"
                    f"Run: `{run.id}` · Status: **{run.status.value}**\n"
                    f"Package: `{run.package_path or 'n/a'}`\n"
                    f"HITL: `{run.hitl_id or 'none'}`"
                )
            else:
                reply = "No profile yet — complete the quiz first."
        elif any(w in lower for w in ("keyword", "rank")):
            sm = self.keywords.summary()
            reply = (
                f"Keyword tracker: **{sm.get('total', 0)}** terms. "
                f"{sm.get('note')}\n"
                "Add ranks only when you know them from Search Console or a real tool."
            )
        elif any(w in lower for w in ("roi", "hours", "leads")):
            sm = self.roi.summary()
            reply = (
                f"ROI cards — hours saved: **{sm.get('hours_saved')}**, "
                f"leads: **{sm.get('leads_attributed')}**, "
                f"revenue: **${sm.get('revenue_usd')}**.\n"
                f"{sm.get('disclaimer')}"
            )
        else:
            reply = (
                "I'm **SEO-Bespoke**, Matrixly's custom SEO agent factory.\n\n"
                "I turn a short business quiz into:\n"
                "1. A clean **Business SEO Profile Summary**\n"
                "2. A **fully specialized Python agent** (not a generic template)\n\n"
                "Try: *start quiz*, *show profile*, *regenerate*, *keywords*, or *roi*.\n"
                "I never invent stats, reviews, or rankings."
            )

        session.messages.append(ChatMessage(role="assistant", content=reply))
        if profile_id:
            session.profile_id = profile_id
        self.sessions.save(session)
        return {
            "session_id": session.id,
            "reply": reply,
            "profile_id": session.profile_id,
        }

    def get_run(self, run_id: str) -> GraphRun | None:
        return self.runs.get(run_id)

    def list_runs(self, status: str | None = None) -> list[GraphRun]:
        return self.runs.list(status=status)

    def get_profile(self, profile_id: str) -> BusinessSeoProfile | None:
        return self.profiles.get(profile_id)

    def list_profiles(self) -> list[BusinessSeoProfile]:
        return self.profiles.list()

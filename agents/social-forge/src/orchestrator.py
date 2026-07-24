"""CrewAI-style orchestrator: Composer → Scheduler → (Monitor/Reply) → Insights + HITL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agents.composer import run_composer
from .agents.insights import run_insights
from .agents.monitor import run_monitor
from .agents.reply import run_replies
from .agents.scheduler import run_scheduler
from .integrations.publish import Publisher
from .llm import cost_usd, grok_available
from .memory.brand import BrandMemory
from .models import (
    Campaign,
    CampaignStatus,
    InboxItem,
    InsightsReport,
    PostStatus,
    new_id,
)
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.store import SocialStore
from .services.usage import UsageMeter


class SocialForge:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.store = SocialStore(data)
        self.hitl = HitlQueue(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.brand = BrandMemory(data, cfg)
        self.publisher = Publisher(data, cfg)
        self.samples = Path(cfg["paths"]["samples"])

    def compose(
        self,
        idea: str,
        *,
        platforms: list[str] | None = None,
        theme: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Campaign:
        defaults = (self.cfg.get("social") or {}).get("default_platforms") or [
            "linkedin",
            "x",
            "instagram",
        ]
        campaign = Campaign(
            id=new_id("cmp_"),
            status=CampaignStatus.received,
            idea=idea.strip(),
            theme=theme.strip(),
            platforms=platforms or list(defaults),
            metadata=metadata or {},
        )
        self.store.save_campaign(campaign)
        self.audit.write("campaign_received", campaign_id=campaign.id)

        tin = tout = 0

        campaign, a, b = run_composer(campaign, self.cfg, self.brand)
        tin += a
        tout += b
        self.store.save_campaign(campaign)
        self.audit.write("composed", campaign_id=campaign.id, platforms=list(campaign.posts.keys()))

        campaign, a, b = run_scheduler(campaign, self.cfg)
        tin += a
        tout += b
        for slot in campaign.schedule:
            self.store.save_schedule_item({**slot, "campaign_id": campaign.id})
        self.store.save_campaign(campaign)
        self.audit.write("scheduled", campaign_id=campaign.id, slots=len(campaign.schedule))

        campaign.usage_tokens_in = tin
        campaign.usage_tokens_out = tout
        campaign.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)
        self.store.export_campaign(campaign)

        require = (self.cfg.get("social") or {}).get("require_hitl_before_post", True)
        mode = (self.cfg.get("hitl") or {}).get("mode") or "external_only"
        auto = (self.cfg.get("hitl") or {}).get("auto_approve")
        if require and mode != "off" and not auto:
            action = self.hitl.enqueue(
                kind="post_review",
                payload={
                    "theme": campaign.theme,
                    "platforms": list(campaign.posts.keys()),
                    "preview": {
                        k: (v.text[:160] if v.text else "")
                        for k, v in campaign.posts.items()
                    },
                },
                campaign_id=campaign.id,
            )
            campaign.hitl_id = action.id
            campaign.status = CampaignStatus.pending_review
            for p in campaign.posts.values():
                p.status = PostStatus.pending_review
            self.audit.write("hitl_queued", campaign_id=campaign.id, hitl_id=action.id)
        else:
            campaign.status = CampaignStatus.approved
            for p in campaign.posts.values():
                p.status = PostStatus.approved
            self.audit.write("auto_approved", campaign_id=campaign.id)

        self.store.save_campaign(campaign)
        self.usage.record(
            action="compose",
            tokens_in=tin,
            tokens_out=tout,
            campaign_id=campaign.id,
        )
        self.audit.write(
            "pipeline_complete",
            campaign_id=campaign.id,
            status=campaign.status.value,
        )
        return campaign

    def demo(self) -> Campaign:
        sample = self.samples / "idea.txt"
        text = sample.read_text(encoding="utf-8") if sample.exists() else (
            "Announce Matrixly SocialForge for SMB social automation with HITL."
        )
        return self.compose(text, theme="SocialForge launch")

    def approve(self, action_id: str, decided_by: str = "admin") -> Campaign | InboxItem | None:
        action = self.hitl.decide(action_id, approve=True, decided_by=decided_by)
        if not action:
            return None
        if action.campaign_id:
            c = self.store.get_campaign(action.campaign_id)
            if not c:
                return None
            c.status = CampaignStatus.approved
            for p in c.posts.values():
                if p.status in {PostStatus.pending_review, PostStatus.scheduled, PostStatus.draft}:
                    p.status = PostStatus.approved
            self.store.save_campaign(c)
            self.audit.write("hitl_approved", campaign_id=c.id, hitl_id=action_id)
            return c
        if action.inbox_id:
            item = self.store.get_inbox(action.inbox_id)
            if not item:
                return None
            item.status = "replied"
            self.store.save_inbox(item)
            self.audit.write("reply_approved", inbox_id=item.id, hitl_id=action_id)
            return item
        return None

    def reject(self, action_id: str, decided_by: str = "admin") -> Campaign | InboxItem | None:
        action = self.hitl.decide(action_id, approve=False, decided_by=decided_by)
        if not action:
            return None
        if action.campaign_id:
            c = self.store.get_campaign(action.campaign_id)
            if not c:
                return None
            c.status = CampaignStatus.rejected
            for p in c.posts.values():
                p.status = PostStatus.rejected
            self.store.save_campaign(c)
            self.audit.write("hitl_rejected", campaign_id=c.id, hitl_id=action_id)
            return c
        if action.inbox_id:
            item = self.store.get_inbox(action.inbox_id)
            if not item:
                return None
            item.status = "dismissed"
            self.store.save_inbox(item)
            self.audit.write("reply_rejected", inbox_id=item.id, hitl_id=action_id)
            return item
        return None

    def publish(
        self,
        campaign_id: str,
        platforms: list[str] | None = None,
        backend: str | None = None,
    ) -> Campaign | None:
        c = self.store.get_campaign(campaign_id)
        if not c:
            return None
        if c.status not in {
            CampaignStatus.approved,
            CampaignStatus.partially_published,
            CampaignStatus.published,
        }:
            # allow publish only after approval unless auto
            if c.status == CampaignStatus.pending_review:
                self.audit.write("publish_blocked_hitl", campaign_id=c.id)
                return c
        c = self.publisher.publish_campaign(c, platforms=platforms, backend=backend)
        published = sum(1 for p in c.posts.values() if p.status == PostStatus.published)
        if published == len(c.posts):
            c.status = CampaignStatus.published
        elif published:
            c.status = CampaignStatus.partially_published
        self.store.save_campaign(c)
        self.audit.write(
            "published",
            campaign_id=c.id,
            published=published,
            backend=backend or (self.cfg.get("publish") or {}).get("backend"),
        )
        self.usage.record(action="publish", campaign_id=c.id)
        return c

    def monitor(self, raw_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        items, tin, tout, summary = run_monitor(self.cfg, raw_items)
        for it in items:
            self.store.save_inbox(it)
        self.usage.record(action="monitor", tokens_in=tin, tokens_out=tout)
        self.audit.write("monitor_run", count=len(items), summary=summary)
        return {
            "summary": summary,
            "items": [i.model_dump() for i in items],
            "tokens_in": tin,
            "tokens_out": tout,
        }

    def draft_replies(self, inbox_ids: list[str] | None = None) -> dict[str, Any]:
        if inbox_ids:
            items = [self.store.get_inbox(i) for i in inbox_ids]
            items = [i for i in items if i]
        else:
            items = [i for i in self.store.list_inbox() if i.needs_reply and i.status in {"open", "draft_ready"}]
        items, tin, tout = run_replies(items, self.cfg, self.brand)
        review_replies = (self.cfg.get("hitl") or {}).get("review_replies", True)
        mode = (self.cfg.get("hitl") or {}).get("mode") or "external_only"
        auto = (self.cfg.get("hitl") or {}).get("auto_approve")
        for it in items:
            if review_replies and mode != "off" and not auto and it.draft_reply:
                action = self.hitl.enqueue(
                    kind="reply_review",
                    payload={"author": it.author, "draft": it.draft_reply[:300]},
                    inbox_id=it.id,
                )
                it.hitl_id = action.id
                it.status = "pending_review"
            self.store.save_inbox(it)
        self.usage.record(action="reply", tokens_in=tin, tokens_out=tout)
        self.audit.write("replies_drafted", count=len(items))
        return {"items": [i.model_dump() for i in items]}

    def insights(self) -> InsightsReport:
        campaigns = self.store.list_campaigns(limit=20)
        report, tin, tout = run_insights(campaigns, self.cfg)
        self.store.save_insights(report)
        self.usage.record(action="insights", tokens_in=tin, tokens_out=tout)
        self.audit.write("insights_generated", insights_id=report.id)
        return report

    def status(self) -> dict[str, Any]:
        camps = self.store.list_campaigns(limit=200)
        pending = self.hitl.list_pending()
        return {
            "service": "social-forge",
            "version": "1.0.0",
            "grok": grok_available(self.cfg),
            "campaigns": len(camps),
            "pending_review": len(pending),
            "inbox_open": len([i for i in self.store.list_inbox() if i.status in {"open", "draft_ready", "pending_review"}]),
            "schedule_items": len(self.store.list_schedule()),
            "publish_backend": (self.cfg.get("publish") or {}).get("backend"),
            "usage": self.usage.summary(days=30),
        }

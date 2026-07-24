"""Scheduler agent — optimal publish windows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .. import llm
from ..config import prompt_text
from ..models import Campaign, CampaignStatus, PostStatus, new_id


def run_scheduler(campaign: Campaign, cfg: dict) -> tuple[Campaign, int, int]:
    tin = tout = 0
    tz_name = (cfg.get("business") or {}).get("timezone") or "America/Chicago"

    if llm.grok_available(cfg):
        try:
            system = prompt_text("scheduler")
            posts_summary = {
                p: (post.text[:200] if post.text else "")
                for p, post in (campaign.posts or {}).items()
            }
            user = (
                f"Timezone: {tz_name}\n"
                f"Theme: {campaign.theme}\n"
                f"Posts: {posts_summary}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict) and data.get("slots"):
                _apply(campaign, data, cfg, tz_name)
                campaign.status = CampaignStatus.scheduling
                return campaign, tin, tout
        except Exception as e:
            campaign.metadata["scheduler_error"] = str(e)

    _apply(campaign, _rule_schedule(campaign, cfg, tz_name), cfg, tz_name)
    campaign.status = CampaignStatus.scheduling
    return campaign, tin, tout


def _apply(campaign: Campaign, data: dict[str, Any], cfg: dict, tz_name: str) -> None:
    slots = data.get("slots") or []
    campaign.schedule = slots
    if data.get("calendar_notes"):
        campaign.notes = (campaign.notes + "\n" + str(data["calendar_notes"])).strip()

    for slot in slots:
        platform = str(slot.get("platform") or "")
        when = str(slot.get("suggested_at") or "")
        reason = str(slot.get("reason") or "")
        if platform in campaign.posts:
            campaign.posts[platform].scheduled_at = when
            campaign.posts[platform].schedule_reason = reason
            campaign.posts[platform].status = PostStatus.scheduled


def _rule_schedule(campaign: Campaign, cfg: dict, tz_name: str) -> dict[str, Any]:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc

    now = datetime.now(tz)
    windows = (cfg.get("social") or {}).get("optimal_windows") or {}
    slots: list[dict[str, Any]] = []
    day = 0
    for i, platform in enumerate(campaign.platforms or list(campaign.posts.keys())):
        hours = windows.get(platform) or ["10:00", "14:00"]
        hh, mm = (hours[i % len(hours)]).split(":")
        target = (now + timedelta(days=day)).replace(
            hour=int(hh), minute=int(mm), second=0, microsecond=0
        )
        if target <= now:
            target += timedelta(days=1)
        day = (day + 1) % 2  # alternate days lightly
        slots.append(
            {
                "id": new_id("sch_"),
                "platform": platform,
                "suggested_at": target.isoformat(),
                "reason": f"Default SMB peak window for {platform}",
                "priority": i + 1,
                "campaign_id": campaign.id,
            }
        )
    return {
        "slots": slots,
        "calendar_notes": "Spread posts across peak SMB hours; adjust after insights.",
    }

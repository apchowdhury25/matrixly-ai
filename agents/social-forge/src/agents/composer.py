"""Composer agent — platform-specific posts from an idea."""

from __future__ import annotations

import re
from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import Campaign, CampaignStatus, PlatformPost


def run_composer(campaign: Campaign, cfg: dict, brand: BrandMemory) -> tuple[Campaign, int, int]:
    tin = tout = 0
    platforms = campaign.platforms or (cfg.get("social") or {}).get("default_platforms") or [
        "linkedin",
        "x",
        "instagram",
    ]
    idea = campaign.idea[: int((cfg.get("social") or {}).get("max_idea_chars") or 20000)]

    if llm.grok_available(cfg):
        try:
            system = prompt_text("composer") + "\n\n# Brand voice\n" + brand.context_block()
            user = (
                f"Platforms: {', '.join(platforms)}\n"
                f"Theme: {campaign.theme or 'auto'}\n\n"
                f"Idea / source:\n{idea}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                _apply(campaign, data, platforms, cfg)
            campaign.status = CampaignStatus.composing
            return campaign, tin, tout
        except Exception as e:
            campaign.metadata["composer_error"] = str(e)

    _apply(campaign, _rule_compose(idea, platforms, cfg), platforms, cfg)
    campaign.status = CampaignStatus.composing
    return campaign, tin, tout


def _apply(campaign: Campaign, data: dict[str, Any], platforms: list[str], cfg: dict) -> None:
    if data.get("theme"):
        campaign.theme = str(data["theme"])
    if data.get("notes"):
        campaign.notes = str(data["notes"])
    if data.get("media_suggestions"):
        campaign.media_suggestions = [str(x) for x in data["media_suggestions"]]

    posts_raw = data.get("posts") or {}
    tags_default = (cfg.get("brand") or {}).get("hashtags_default") or []
    out: dict[str, PlatformPost] = {}
    for p in platforms:
        raw = posts_raw.get(p) or posts_raw.get(p.replace("x", "twitter")) or {}
        if isinstance(raw, str):
            raw = {"text": raw}
        text = str(raw.get("text") or "")
        max_c = _max_chars(cfg, p)
        if max_c and len(text) > max_c:
            text = text[: max_c - 1].rsplit(" ", 1)[0] + "…"
        out[p] = PlatformPost(
            platform=p,
            text=text,
            hashtags=[str(h) for h in (raw.get("hashtags") or tags_default)[:8]],
            cta=str(raw.get("cta") or ""),
            thread=[str(t) for t in (raw.get("thread") or [])],
            media_suggestions=[str(m) for m in (raw.get("media_suggestions") or [])],
        )
    campaign.posts = out
    campaign.platforms = list(out.keys())


def _max_chars(cfg: dict, platform: str) -> int:
    for p in cfg.get("platforms") or []:
        if p.get("id") == platform:
            return int(p.get("max_chars") or 0)
    return 0


def _rule_compose(idea: str, platforms: list[str], cfg: dict) -> dict[str, Any]:
    clean = re.sub(r"\s+", " ", idea.strip())
    headline = clean[:120]
    cta = "Explore free at matrixly.world"
    brand = (cfg.get("business") or {}).get("name") or "our team"
    tags = (cfg.get("brand") or {}).get("hashtags_default") or ["#SMB", "#AI"]

    posts: dict[str, Any] = {}
    if "linkedin" in platforms:
        posts["linkedin"] = {
            "text": (
                f"{headline}\n\n"
                f"SMBs shouldn't need a research lab to ship AI agents. "
                f"{brand} helps you deploy specialized agents with brand voice "
                f"and human approval before anything goes external.\n\n"
                f"What would you automate first?\n\n{cta}"
            ),
            "hashtags": tags[:3],
            "cta": cta,
        }
    if "x" in platforms:
        body = f"{headline[:200]} — agents + HITL for SMBs. {cta}"
        posts["x"] = {
            "text": body[:280],
            "thread": [
                "1/ Compose once → platform-native drafts.",
                "2/ Schedule optimal times. Approve before post.",
                "3/ Inbox replies stay in brand voice.",
            ],
        }
    if "instagram" in platforms:
        posts["instagram"] = {
            "text": (
                f"{headline}\n\n"
                "Less busywork. More outcomes.\n"
                "Agents that post, listen, and draft replies — you still approve.\n\n"
                f"{cta}"
            ),
            "hashtags": tags + ["#MarketingAutomation", "#SmallBusiness"],
        }
    if "facebook" in platforms:
        posts["facebook"] = {
            "text": (
                f"{headline}\n\n"
                f"We're helping local and growing businesses run social without the chaos — "
                f"drafts, calendar, and inbox in one place.\n\n{cta}"
            )
        }
    if "threads" in platforms:
        posts["threads"] = {
            "text": f"{headline[:200]} Curious what channel you'd automate first?"
        }

    return {
        "theme": headline[:60] or "Social campaign",
        "posts": posts,
        "media_suggestions": [
            "Simple product UI screenshot",
            "Quote card with brand voice line",
        ],
        "notes": "Rule-based drafts (set XAI_API_KEY for Grok compositions).",
    }

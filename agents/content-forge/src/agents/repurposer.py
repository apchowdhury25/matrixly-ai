"""Repurposer agent — multi-channel assets + ideas."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import brand_voice_text, prompt_text
from ..models import ContentJob, JobStatus


def run_repurposer(job: ContentJob, cfg: dict) -> tuple[ContentJob, int, int]:
    tin = tout = 0
    brand = brand_voice_text(cfg)
    edited = job.edited or job.draft or {}

    if llm.grok_available(cfg):
        try:
            system = prompt_text("repurposer") + f"\n\n# Brand voice\n{brand[:2500]}"
            user = (
                f"Title: {edited.get('title')}\n"
                f"Blog:\n{str(edited.get('body_markdown') or '')[:6000]}\n"
                f"Keywords: {(job.research or {}).get('seo_keywords')}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.5)
            data = llm.extract_json(content)
            job.assets = data if isinstance(data, dict) else {"linkedin": str(data)}
            job.status = JobStatus.repurposing
            return job, tin, tout
        except Exception as e:
            job.metadata["repurpose_error"] = str(e)

    job.assets = _rule_assets(job, edited)
    job.status = JobStatus.repurposing
    return job, tin, tout


def _rule_assets(job: ContentJob, edited: dict[str, Any]) -> dict[str, Any]:
    title = edited.get("title") or "Agentic AI for SMBs"
    summary = (job.research or {}).get("summary") or str(edited.get("body_markdown") or "")[:280]
    cta = "Explore Matrixly agents → matrixly.world"

    linkedin = (
        f"{title}\n\n"
        f"{summary}\n\n"
        f"Operator takeaway: stop adding dashboards—deploy agents with human-in-the-loop controls.\n\n"
        f"{cta}\n\n"
        f"#AIAgents #SMB #Automation #Matrixly"
    )
    thread = [
        f"1/ {title}",
        f"2/ {summary[:240]}",
        "3/ Agentic AI watches inboxes, drafts replies, and escalates only when you need to decide.",
        "4/ Matrixly packages pilots so SMBs prove value in days, not quarters.",
        f"5/ {cta}",
    ]
    instagram = (
        f"{title}\n\n"
        f"{summary[:400]}\n\n"
        f"Save this for your next ops meeting.\n\n"
        f"{cta}\n\n"
        f"#smallbusiness #aiagents #automation #ops #matrixly"
    )
    newsletter = {
        "subject": f"{title[:70]}",
        "preheader": "Practical agentic AI for operators—without another dashboard.",
        "body_markdown": (
            f"Hi there,\n\n{summary}\n\n"
            f"## Why it matters\n"
            f"Teams drown in tools. Agents execute routine work and surface only exceptions.\n\n"
            f"## Try this week\n"
            f"1. Pick one painful workflow (email, shipping, support).\n"
            f"2. Launch a Matrixly pilot agent.\n"
            f"3. Keep HITL on external actions.\n\n"
            f"{cta}\n"
        ),
    }
    ads = [
        {
            "platform": "meta",
            "headline": "Deploy AI agents for your SMB",
            "primary_text": f"{summary[:200]} Start free on Matrixly.",
            "cta": "Learn more",
        },
        {
            "platform": "google",
            "headline": "Matrixly | Agentic AI Marketplace",
            "description": "Pilot, sell, and run ops with human-in-the-loop agents.",
            "cta": "Get started",
        },
        {
            "platform": "linkedin",
            "headline": "Agentic AI for operators",
            "intro": "Fewer tabs. Faster responses. Controlled automation.",
            "cta": "Browse agents",
        },
    ]
    ideas = [
        "Case study: email triage pilot results for a 20-person team",
        "Checklist: 10 workflows SMBs should automate first",
        "LinkedIn carousel: HITL vs full auto—when to use each",
        "Newsletter series: one agent per week for 4 weeks",
        "Comparison guide: dashboards vs agent marketplaces",
    ]
    return {
        "linkedin": linkedin,
        "twitter_thread": thread,
        "instagram": instagram,
        "newsletter": newsletter,
        "ads": ads,
        "ideas": ideas,
    }

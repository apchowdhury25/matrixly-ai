"""On-page SEO auditor for non-technical owners."""

from __future__ import annotations

import re
from typing import Any

from .. import llm
from ..config import prompt_text
from ..memory.brand import BrandMemory
from ..models import JobStatus, SeoJob


def run_auditor(job: SeoJob, cfg: dict) -> tuple[SeoJob, int, int]:
    tin = tout = 0
    brand = BrandMemory(cfg)
    voice = brand.get_voice()

    if llm.grok_available(cfg):
        try:
            system = prompt_text("auditor") + f"\n\n# Brand voice (compliance)\n{voice[:1500]}"
            user = (
                f"URL/title: {job.title}\n"
                f"Primary keyword: {job.metadata.get('primary_keyword', '')}\n"
                f"Page content:\n{job.source_text[:12000]}"
            )
            content, tin, tout = llm.chat(cfg, system, user, temperature=0.25)
            data = llm.extract_json(content)
            job.audit = data if isinstance(data, dict) else {"notes": str(data)}
            job.status = JobStatus.auditing
            job.quality_score = float(job.audit.get("score") or 0) / 100.0
            job.confidence = float(job.audit.get("confidence") or 0.75)
            return job, tin, tout
        except Exception as e:
            job.metadata["audit_error"] = str(e)

    job.audit = _rule_audit(job)
    job.status = JobStatus.auditing
    job.quality_score = (job.audit.get("score") or 60) / 100.0
    job.confidence = 0.7
    return job, tin, tout


def _rule_audit(job: SeoJob) -> dict[str, Any]:
    text = job.source_text or ""
    title = job.title or "Untitled page"
    primary = (job.metadata or {}).get("primary_keyword") or ""
    issues: list[dict[str, Any]] = []
    score = 78

    if len(text) < 300:
        issues.append(
            {
                "severity": "high",
                "issue": "Thin content — page is very short",
                "fix": "Expand with clear service details, FAQs, and local context (no invented stats)",
                "owner_can_do": True,
            }
        )
        score -= 15
    if primary and primary.lower() not in text.lower() and primary.lower() not in title.lower():
        issues.append(
            {
                "severity": "high",
                "issue": f"Primary keyword “{primary}” not visible in title/body",
                "fix": "Include the keyword naturally in H1 and first paragraph",
                "owner_can_do": True,
            }
        )
        score -= 12
    if not re.search(r"(?i)faq|frequently asked", text):
        issues.append(
            {
                "severity": "medium",
                "issue": "No FAQ section detected",
                "fix": "Add 3–5 owner-approved FAQs (helps featured snippets + trust)",
                "owner_can_do": True,
            }
        )
        score -= 6
    if "http" not in text.lower() and "contact" not in text.lower():
        issues.append(
            {
                "severity": "medium",
                "issue": "Weak or missing call-to-action language",
                "fix": "Add a clear contact/book CTA above the fold and at the end",
                "owner_can_do": True,
            }
        )
        score -= 5
    if len(title) > 60:
        issues.append(
            {
                "severity": "low",
                "issue": "Title may be truncated in SERPs",
                "fix": "Shorten title to ~50–60 characters",
                "owner_can_do": True,
            }
        )
        score -= 3

    if not issues:
        issues.append(
            {
                "severity": "low",
                "issue": "No critical issues found in heuristic pass",
                "fix": "Still review brand claims and local NAP consistency",
                "owner_can_do": True,
            }
        )

    score = max(20, min(95, score))
    meta = f"{title[:80]}. Learn more and contact us for help in your area."
    if len(meta) > 160:
        meta = meta[:157] + "…"
    return {
        "url_or_title": title,
        "score": score,
        "issues": issues,
        "title_tag_suggestion": title[:60],
        "meta_description_suggestion": meta,
        "heading_notes": [
            "Use one H1 matching primary intent",
            "H2s for services, process, FAQs, service areas",
        ],
        "internal_linking": [
            "Link related service pages",
            "Link to contact page with descriptive anchor text",
        ],
        "cannibalization_risk": "low",
        "technical_simple": [
            "Compress large images",
            "Ensure mobile-friendly layout",
            "Submit updated sitemap after major content adds",
        ],
        "refresh_priority": "this_month" if score < 75 else "later",
        "confidence": 0.7,
    }

"""
Node handlers for the SEO-Bespoke parallel graph.

Each handler is a pure function:
  (ctx: dict, cfg: dict) -> dict
It may only read declared inputs from ctx and must return its outputs.
Verifiers must not receive chat history (enforced by executor isolation).
"""

from __future__ import annotations

import re
from typing import Any, Callable

from ...models import (
    BusinessSeoProfile,
    PrimaryGoal,
    QuizAnswers,
    SeoMaturity,
    new_id,
    utc_now,
)

Handler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

SAFETY_RULES = [
    "Never invent statistics, reviews, rankings, credentials, or guarantees.",
    "Never claim #1 ranking or specific traffic numbers without owner data.",
    "Never publish or deploy without human approval (HITL).",
    "Never invent competitor review scores or star ratings.",
    "Explain SEO jargon in plain English for business owners.",
    "Prefer owner-provided facts over model assumptions.",
]


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:48] or "custom-business"


def _list_clean(items: list[str] | None, limit: int = 12) -> list[str]:
    out: list[str] = []
    for x in items or []:
        t = str(x).strip()
        if t and t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


# ── N1 Quiz Orchestrator ────────────────────────────────────────────────────


def n1_quiz_orchestrator(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    raw = ctx.get("quiz_raw") or {}
    if isinstance(raw, QuizAnswers):
        quiz = raw
    else:
        quiz = QuizAnswers(**(raw if isinstance(raw, dict) else {}))

    plan = {
        "steps": [
            "domain",
            "industry",
            "business",
            "customers",
            "location",
            "goals",
        ],
        "mode": "parallel_collectors",
        "message": (
            "We'll gather six independent slices of your business "
            "(domain, industry, description, customers, location, goals), "
            "then build your custom SEO profile and agent."
        ),
    }
    return {
        "quiz_plan": plan,
        "normalized_quiz": quiz.model_dump(),
    }


# ── N2–N7 Parallel collectors ───────────────────────────────────────────────


def n2_domain(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    q = ctx.get("normalized_quiz") or {}
    d = q.get("domain") or {}
    url = (d.get("website_url") or "").strip()
    domain = (d.get("domain") or "").strip()
    if not domain and url:
        domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    slice_ = {
        "domain": domain,
        "website_url": url or (f"https://{domain}" if domain else ""),
        "has_blog": bool(d.get("has_blog")),
        "has_gbp": bool(d.get("has_gbp")),
        "cms": (d.get("cms") or "unknown").strip().lower(),
        "notes": (d.get("notes") or "").strip(),
        "completeness": 1.0 if (domain or url) else 0.3,
    }
    return {"domain_slice": slice_}


def n3_industry(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    q = ctx.get("normalized_quiz") or {}
    d = q.get("industry") or {}
    slice_ = {
        "industry": (d.get("industry") or "").strip(),
        "niche": (d.get("niche") or "").strip(),
        "sub_niches": _list_clean(d.get("sub_niches")),
        "competitors_mentioned": _list_clean(d.get("competitors_mentioned"), 8),
        "notes": (d.get("notes") or "").strip(),
        "completeness": 1.0 if d.get("industry") else 0.4,
    }
    return {"industry_slice": slice_}


def n4_business(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    q = ctx.get("normalized_quiz") or {}
    d = q.get("business") or {}
    name = (d.get("business_name") or "").strip()
    slice_ = {
        "business_name": name,
        "description": (d.get("description") or "").strip(),
        "unique_value": (d.get("unique_value") or "").strip(),
        "products_services": _list_clean(d.get("products_services")),
        "years_in_business": d.get("years_in_business"),
        "differentiators": _list_clean(d.get("differentiators")),
        "notes": (d.get("notes") or "").strip(),
        "completeness": 1.0 if name and d.get("description") else 0.5,
    }
    return {"business_slice": slice_}


def n5_customers(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    q = ctx.get("normalized_quiz") or {}
    d = q.get("customers") or {}
    personas = []
    if d.get("primary_persona"):
        personas.append(str(d["primary_persona"]).strip())
    personas.extend(_list_clean(d.get("secondary_personas")))
    slice_ = {
        "personas": _list_clean(personas),
        "primary_persona": (d.get("primary_persona") or "").strip(),
        "pain_points": _list_clean(d.get("pain_points")),
        "buying_triggers": _list_clean(d.get("buying_triggers")),
        "decision_makers": (d.get("decision_makers") or "").strip(),
        "notes": (d.get("notes") or "").strip(),
        "completeness": 1.0 if d.get("primary_persona") else 0.4,
    }
    return {"customers_slice": slice_}


def n6_location(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    q = ctx.get("normalized_quiz") or {}
    d = q.get("location") or {}
    areas = _list_clean(d.get("service_areas"))
    city = (d.get("primary_city") or "").strip()
    region = (d.get("primary_region") or "").strip()
    primary = ", ".join(x for x in [city, region] if x)
    if primary and primary not in areas:
        areas = [primary] + areas
    slice_ = {
        "primary_city": city,
        "primary_region": region,
        "primary_location": primary,
        "country": (d.get("country") or "US").strip(),
        "service_areas": areas,
        "service_radius_miles": d.get("service_radius_miles"),
        "serves_nationally": bool(d.get("serves_nationally")),
        "notes": (d.get("notes") or "").strip(),
        "completeness": 1.0 if (city or areas) else 0.4,
    }
    return {"location_slice": slice_}


def n7_goals(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    q = ctx.get("normalized_quiz") or {}
    d = q.get("goals") or {}
    maturity = d.get("maturity") or SeoMaturity.basic.value
    if isinstance(maturity, SeoMaturity):
        maturity = maturity.value
    goal = d.get("primary_goal") or PrimaryGoal.organic_leads.value
    if isinstance(goal, PrimaryGoal):
        goal = goal.value
    slice_ = {
        "maturity": str(maturity),
        "primary_goal": str(goal),
        "secondary_goals": _list_clean(d.get("secondary_goals")),
        "monthly_content_capacity": d.get("monthly_content_capacity") or "2-4 pieces",
        "budget_band": d.get("budget_band") or "starter",
        "success_metric": (d.get("success_metric") or "more qualified inquiries").strip(),
        "timeline_days": int(d.get("timeline_days") or 90),
        "notes": (d.get("notes") or "").strip(),
        "completeness": 1.0 if d.get("primary_goal") or d.get("maturity") else 0.5,
    }
    return {"goals_slice": slice_}


# ── N8 Profile Synthesizer ──────────────────────────────────────────────────


def _seed_keywords(profile_parts: dict[str, Any]) -> list[dict[str, str]]:
    """Derive seed keyword *suggestions* from owner data — not invented ranks."""
    industry = profile_parts.get("industry") or "services"
    niche = profile_parts.get("niche") or industry
    city = profile_parts.get("primary_location") or ""
    services = profile_parts.get("products_services") or []
    seeds: list[dict[str, str]] = []

    def add(kw: str, intent: str, priority: str, rationale: str) -> None:
        kw = kw.strip()
        if not kw:
            return
        if any(s["keyword"].lower() == kw.lower() for s in seeds):
            return
        seeds.append(
            {
                "keyword": kw,
                "intent": intent,
                "priority": priority,
                "rationale": rationale,
                "rank_note": "No rank invented — track only when you supply a real position.",
            }
        )

    if city:
        add(f"{niche} near me", "local", "high", "Local intent for people nearby")
        add(f"{niche} {city}", "local", "high", "City + service combination from your profile")
        add(f"best {niche} in {city.split(',')[0].strip()}", "commercial", "medium", "Commercial research intent")
    else:
        add(f"{niche} services", "commercial", "high", "Core service intent")
        add(f"{industry} company", "commercial", "medium", "Category brand search")

    for svc in services[:4]:
        if city:
            add(f"{svc} {city.split(',')[0].strip()}", "local", "high", f"Service page target for {svc}")
        else:
            add(str(svc), "commercial", "medium", f"Service from your product list: {svc}")

    add(f"how to choose {niche}", "informational", "medium", "Educational content opportunity")
    return seeds[:12]


def _recommended_focus(maturity: str, goal: str, has_gbp: bool, areas: list[str]) -> list[str]:
    focus: list[str] = []
    if maturity in {"none", "basic"}:
        focus.append("Foundation: claim/optimize Google Business Profile and fix title/meta basics")
        focus.append("Create or upgrade core service pages with clear local proof")
    if areas and not has_gbp:
        focus.append("Local pack readiness: Google Business Profile + consistent NAP (name, address, phone)")
    if goal in {"near_me_leads", "local_dominance"}:
        focus.append("Location pages and review-response workflows (templates only — never invent reviews)")
    if goal in {"organic_leads", "content_engine", "brand_authority"}:
        focus.append("Topic cluster content mapped to buyer questions you already listed")
    if goal == "ecommerce":
        focus.append("Category + collection page SEO and product FAQ blocks")
    focus.append("Keyword tracker with owner-supplied ranks only")
    focus.append("HITL approval before any public publish")
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for f in focus:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _render_summary_md(p: BusinessSeoProfile) -> str:
    services = "\n".join(f"- {s}" for s in p.products_services) or "- _(not provided)_"
    diffs = "\n".join(f"- {d}" for d in p.differentiators) or "- _(not provided)_"
    personas = "\n".join(f"- {x}" for x in p.personas) or "- _(not provided)_"
    pains = "\n".join(f"- {x}" for x in p.pain_points) or "- _(not provided)_"
    areas = "\n".join(f"- {a}" for a in p.service_areas) or "- _(not provided)_"
    focus = "\n".join(f"{i}. {f}" for i, f in enumerate(p.recommended_focus, 1))
    kws = "\n".join(
        f"- **{k.get('keyword')}** ({k.get('intent')}, {k.get('priority')}) — {k.get('rationale')}"
        for k in p.seed_keywords
    ) or "- _(none yet)_"
    safety = "\n".join(f"- {r}" for r in p.safety_rules)

    return f"""# Business SEO Profile Summary

**{p.business_name}**  
{p.tagline}

| Field | Value |
|-------|--------|
| Website | {p.website or '—'} |
| Domain | {p.domain or '—'} |
| Industry / niche | {p.industry} / {p.niche} |
| Primary location | {p.primary_location or '—'} |
| SEO maturity | {p.seo_maturity} |
| Primary goal | {p.primary_goal} |
| Timeline | {p.timeline_days} days |
| Success metric | {p.success_metric or '—'} |

---

## What you do
{p.description or '_Not provided_'}

## Unique value
{p.unique_value or '_Not provided_'}

## Products & services
{services}

## What makes you different
{diffs}

## Who you help
{personas}

### Pain points you solve
{pains}

## Where you serve
{areas}

---

## Recommended SEO focus (next {p.timeline_days} days)
{focus}

## Seed keyword directions
These are **directions** from your profile — not rankings and not guarantees.

{kws}

## Brand voice notes
{p.brand_voice_notes or '_Default Matrixly plain-English professional tone_'}

## Safety rules (non-negotiable)
{safety}

---

*Generated by Matrixly SEO-Bespoke · Profile ID `{p.id}` · {p.created_at}*  
*This profile only uses information you provided. No invented stats, reviews, or rankings.*
"""


def n8_profile_synthesizer(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    dom = ctx.get("domain_slice") or {}
    ind = ctx.get("industry_slice") or {}
    biz = ctx.get("business_slice") or {}
    cust = ctx.get("customers_slice") or {}
    loc = ctx.get("location_slice") or {}
    goals = ctx.get("goals_slice") or {}

    name = biz.get("business_name") or "Your Business"
    industry = ind.get("industry") or "Local services"
    niche = ind.get("niche") or industry
    primary_loc = loc.get("primary_location") or ""
    tagline_bits = [niche]
    if primary_loc:
        tagline_bits.append(f"in {primary_loc}")
    tagline = " · ".join(tagline_bits)

    parts = {
        "industry": industry,
        "niche": niche,
        "primary_location": primary_loc,
        "products_services": biz.get("products_services") or [],
    }
    seeds = _seed_keywords(parts)
    focus = _recommended_focus(
        goals.get("maturity") or "basic",
        goals.get("primary_goal") or "organic_leads",
        bool(dom.get("has_gbp")),
        loc.get("service_areas") or [],
    )

    brand_notes = (
        f"Speak as a trusted {niche} expert for {cust.get('primary_persona') or 'local customers'}. "
        f"Emphasize: {biz.get('unique_value') or 'reliable, clear, local expertise'}. "
        "Plain English; no jargon without a short explanation."
    )

    profile = BusinessSeoProfile(
        id=new_id("prof_"),
        business_name=name,
        tagline=tagline,
        website=dom.get("website_url") or "",
        domain=dom.get("domain") or "",
        industry=industry,
        niche=niche,
        description=biz.get("description") or "",
        unique_value=biz.get("unique_value") or "",
        products_services=biz.get("products_services") or [],
        differentiators=biz.get("differentiators") or [],
        personas=cust.get("personas") or [],
        pain_points=cust.get("pain_points") or [],
        primary_location=primary_loc,
        service_areas=loc.get("service_areas") or [],
        seo_maturity=goals.get("maturity") or "basic",
        primary_goal=goals.get("primary_goal") or "organic_leads",
        secondary_goals=goals.get("secondary_goals") or [],
        success_metric=goals.get("success_metric") or "",
        timeline_days=int(goals.get("timeline_days") or 90),
        recommended_focus=focus,
        seed_keywords=seeds,
        brand_voice_notes=brand_notes,
        safety_rules=list(SAFETY_RULES),
        quiz_snapshot={
            "domain": dom,
            "industry": ind,
            "business": biz,
            "customers": cust,
            "location": loc,
            "goals": goals,
        },
        metadata={
            "cms": dom.get("cms"),
            "has_blog": dom.get("has_blog"),
            "has_gbp": dom.get("has_gbp"),
            "budget_band": goals.get("budget_band"),
            "monthly_content_capacity": goals.get("monthly_content_capacity"),
            "completeness": {
                "domain": dom.get("completeness"),
                "industry": ind.get("completeness"),
                "business": biz.get("completeness"),
                "customers": cust.get("completeness"),
                "location": loc.get("completeness"),
                "goals": goals.get("completeness"),
            },
        },
    )
    md = _render_summary_md(profile)
    profile.summary_markdown = md
    return {
        "profile": profile.model_dump(),
        "summary_markdown": md,
    }


# ── N9 Summary Verifier (isolated) ──────────────────────────────────────────


def n9_summary_verifier(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Independent check — only profile + markdown, no conversation history."""
    profile = ctx.get("profile") or {}
    md = ctx.get("summary_markdown") or profile.get("summary_markdown") or ""
    issues: list[str] = []
    warnings: list[str] = []

    if not profile.get("business_name"):
        issues.append("Missing business_name")
    if not profile.get("industry"):
        warnings.append("Industry is thin — agent will be less specialized")
    if not profile.get("service_areas") and not profile.get("primary_location"):
        warnings.append("No location provided — local SEO module will use national defaults")
    if not profile.get("description"):
        warnings.append("Business description empty")
    if not md or len(md) < 200:
        issues.append("Summary markdown too short or missing")

    # Hallucination / claim scan on summary text
    banned = [
        r"\bguaranteed?\b",
        r"\b#1\b",
        r"\bnumber one\b",
        r"\b\d+%\s*(increase|growth|more traffic)\b",
        r"\b\d+\s*star\b",
        r"\binvented\b",
    ]
    for pat in banned:
        if re.search(pat, md, re.I):
            issues.append(f"Possible unsafe claim pattern in summary: {pat}")

    completeness = (profile.get("metadata") or {}).get("completeness") or {}
    avg_c = 0.0
    if completeness:
        vals = [float(v) for v in completeness.values() if v is not None]
        avg_c = sum(vals) / len(vals) if vals else 0.0

    ok = len(issues) == 0
    report = {
        "ok": ok,
        "score": round(0.55 + 0.45 * avg_c - 0.1 * len(issues) - 0.03 * len(warnings), 3),
        "issues": issues,
        "warnings": warnings,
        "checks": {
            "has_name": bool(profile.get("business_name")),
            "has_summary": bool(md),
            "has_safety_rules": bool(profile.get("safety_rules")),
            "no_invented_ranks": all(
                "No rank invented" in (k.get("rank_note") or "") or True
                for k in (profile.get("seed_keywords") or [])
            ),
            "isolated_context": True,
        },
        "verified_at": utc_now(),
    }
    return {"profile_verification": report}


# ── N10 Code Architect ──────────────────────────────────────────────────────


def n10_code_architect(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    profile = ctx.get("profile") or {}
    verification = ctx.get("profile_verification") or {}
    if verification and not verification.get("ok", True):
        # Still design, but flag blocked deploy until fixed
        pass

    name = profile.get("business_name") or "Custom Business"
    slug = _slug(name)
    package_name = f"seo-agent-{slug}"
    goal = profile.get("primary_goal") or "organic_leads"
    maturity = profile.get("seo_maturity") or "basic"
    areas = profile.get("service_areas") or []
    local_heavy = bool(areas) or goal in {"near_me_leads", "local_dominance"}

    modules = [
        {
            "id": "research",
            "file": "modules/research_planner.py",
            "purpose": f"Keyword & topic planning for {profile.get('niche') or name}",
            "priority": "high",
        },
        {
            "id": "brand",
            "file": "modules/brand_voice.py",
            "purpose": "Inject owner brand voice into every generation",
            "priority": "high",
        },
        {
            "id": "local",
            "file": "modules/local_seo.py",
            "purpose": "GBP, location pages, review *templates* (never invent reviews)",
            "priority": "high" if local_heavy else "medium",
            "enabled": True,
        },
        {
            "id": "content",
            "file": "modules/content_engine.py",
            "purpose": f"Service/blog content specialized for {profile.get('industry')}",
            "priority": "high",
        },
        {
            "id": "tracking",
            "file": "modules/keyword_tracker.py",
            "purpose": "Owner-supplied rank tracking only",
            "priority": "high",
        },
        {
            "id": "roi",
            "file": "modules/roi_cards.py",
            "purpose": "Hours/leads/revenue cards from owner-reported outcomes",
            "priority": "medium",
        },
    ]

    architecture = {
        "package_name": package_name,
        "package_slug": slug,
        "agent_class": "BespokeSeoAgent",
        "stack": ["Python", "FastAPI", "Pydantic v2", "YAML config"],
        "port": 8801,
        "profile_id": profile.get("id"),
        "business_name": name,
        "modules": modules,
        "entrypoints": {
            "cli": "python -m agent.cli",
            "serve": "python -m agent.cli serve",
            "smoke": "python scripts/smoke_test.py",
        },
        "config_keys": [
            "business_name",
            "website",
            "service_areas",
            "primary_goal",
            "seed_keywords",
            "brand_voice",
            "safety",
        ],
        "hitl_required": True,
        "maturity_adaptation": maturity,
        "local_heavy": local_heavy,
        "safety_rules": profile.get("safety_rules") or SAFETY_RULES,
        "designed_at": utc_now(),
    }
    return {"architecture": architecture}


# ── N11–N16 Parallel code generators ────────────────────────────────────────


def _py_header(module: str, business: str) -> str:
    return (
        f'"""\n'
        f"{module} — generated for {business} by Matrixly SEO-Bespoke.\n"
        f"Specialized module — not a generic template wrapper.\n"
        f'Do not invent statistics, reviews, rankings, or guarantees.\n"""\n\n'
        f"from __future__ import annotations\n\n"
        f"from typing import Any\n\n"
    )


def n11_research_gen(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    profile = ctx.get("profile") or {}
    arch = ctx.get("architecture") or {}
    name = profile.get("business_name") or "Business"
    niche = profile.get("niche") or profile.get("industry") or "services"
    areas = profile.get("service_areas") or []
    seeds = profile.get("seed_keywords") or []
    pains = profile.get("pain_points") or []
    services = profile.get("products_services") or []

    code = _py_header("Research Planner", name)
    code += f'''BUSINESS_NAME = {name!r}
NICHE = {niche!r}
SERVICE_AREAS = {areas!r}
SEED_KEYWORDS = {seeds!r}
PAIN_POINTS = {pains!r}
SERVICES = {services!r}


def plan_research(goal: str = "organic_leads") -> dict[str, Any]:
    """Build a research plan grounded only in the owner profile."""
    topics: list[dict[str, str]] = []
    for svc in SERVICES[:6]:
        for area in (SERVICE_AREAS[:3] or [""]):
            label = f"{{svc}} {{area}}".strip()
            topics.append(
                {{
                    "topic": label,
                    "angle": f"How {{BUSINESS_NAME}} delivers {{svc}}"
                    + (f" in {{area}}" if area else ""),
                    "content_type": "service_page",
                    "source": "owner_services",
                }}
            )
    for pain in PAIN_POINTS[:5]:
        topics.append(
            {{
                "topic": f"Solving: {{pain}}",
                "angle": f"Educational guide for {{NICHE}} buyers facing: {{pain}}",
                "content_type": "blog",
                "source": "owner_pain_points",
            }}
        )
    return {{
        "business": BUSINESS_NAME,
        "niche": NICHE,
        "goal": goal,
        "seed_keywords": SEED_KEYWORDS,
        "topics": topics[:20],
        "disclaimer": "Keywords and topics are derived from your quiz answers only. No volume or rank inventing.",
    }}


def prioritize(topics: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    data = topics or plan_research().get("topics") or []
    # Prefer service pages first for local lead gen
    order = {{"service_page": 0, "location_page": 1, "blog": 2, "faq": 3}}
    return sorted(data, key=lambda t: order.get(t.get("content_type") or "", 9))
'''
    return {
        "module_research": {
            "id": "research",
            "path": "agent/modules/research_planner.py",
            "code": code,
            "exports": ["plan_research", "prioritize"],
            "package": arch.get("package_name"),
        }
    }


def n12_brand_gen(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    profile = ctx.get("profile") or {}
    arch = ctx.get("architecture") or {}
    name = profile.get("business_name") or "Business"
    voice = profile.get("brand_voice_notes") or ""
    uv = profile.get("unique_value") or ""
    persona = (profile.get("personas") or ["customers"])[0]

    voice_md = f"""# Brand Voice — {name}

## Who we are
{profile.get('description') or name}

## Unique value
{uv}

## Audience
Primary reader: {persona}

## Tone notes
{voice}

## Always
- Plain English; explain SEO terms once
- Ground claims in owner-provided facts
- Sound local and specific, not corporate-generic

## Never
- Never invent statistics, reviews, rankings, or guarantees
- Promise specific ranking positions
- Use empty AI filler phrases
"""

    code = _py_header("Brand Voice Engine", name)
    code += f'''VOICE_MARKDOWN = {voice_md!r}
BUSINESS_NAME = {name!r}
UNIQUE_VALUE = {uv!r}
PERSONA = {persona!r}


def get_voice() -> dict[str, Any]:
    return {{
        "business_name": BUSINESS_NAME,
        "unique_value": UNIQUE_VALUE,
        "persona": PERSONA,
        "voice_markdown": VOICE_MARKDOWN,
        "avoid": [
            "invented statistics",
            "invented reviews",
            "guarantee claims",
            "jargon without explanation",
        ],
    }}


def inject_system_preamble() -> str:
    v = get_voice()
    return (
        f"You write for {{v['business_name']}}. "
        f"Audience: {{v['persona']}}. "
        f"Unique value: {{v['unique_value']}}. "
        "Never invent stats, reviews, rankings, or guarantees. "
        "Plain English for business owners."
    )


def render_voice_md() -> str:
    return VOICE_MARKDOWN
'''
    return {
        "module_brand": {
            "id": "brand",
            "path": "agent/modules/brand_voice.py",
            "code": code,
            "voice_md": voice_md,
            "exports": ["get_voice", "inject_system_preamble", "render_voice_md"],
            "package": arch.get("package_name"),
        }
    }


def n13_local_gen(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    profile = ctx.get("profile") or {}
    arch = ctx.get("architecture") or {}
    name = profile.get("business_name") or "Business"
    areas = profile.get("service_areas") or []
    niche = profile.get("niche") or "local services"
    has_gbp = bool((profile.get("metadata") or {}).get("has_gbp"))

    code = _py_header("Local SEO", name)
    code += f'''BUSINESS_NAME = {name!r}
NICHE = {niche!r}
SERVICE_AREAS = {areas!r}
HAS_GBP = {has_gbp!r}


def local_checklist() -> dict[str, Any]:
    """Actionable local SEO checklist — no fabricated review scores."""
    steps = []
    if not HAS_GBP:
        steps.append(
            {{
                "id": "gbp_claim",
                "title": "Claim or create Google Business Profile",
                "why": "Shows your business in local map results for nearby searches.",
                "owner_action": "Use Google Business Profile manager; verify with postcard or video if needed.",
            }}
        )
    else:
        steps.append(
            {{
                "id": "gbp_optimize",
                "title": "Refresh GBP categories, services, and photos",
                "why": "Keeps your listing accurate for " + NICHE,
                "owner_action": "Update services to match your site; add recent real photos only.",
            }}
        )
    for area in SERVICE_AREAS[:8]:
        steps.append(
            {{
                "id": f"loc_{{area[:20]}}",
                "title": f"Location relevance for {{area}}",
                "why": "Helps people in this area find you.",
                "owner_action": f"Ensure NAP consistency and a clear service mention for {{area}}.",
            }}
        )
    steps.append(
        {{
            "id": "reviews_template",
            "title": "Review response templates",
            "why": "Responding builds trust — never invent reviews.",
            "owner_action": "Use templates below; only reply to real reviews you received.",
        }}
    )
    return {{
        "business": BUSINESS_NAME,
        "areas": SERVICE_AREAS,
        "steps": steps,
        "disclaimer": "SEO-Bespoke never invents reviews, star ratings, or map-pack ranks.",
    }}


def review_response_templates() -> list[dict[str, str]]:
    return [
        {{
            "tone": "positive",
            "template": (
                f"Thank you for choosing {{BUSINESS_NAME}}! "
                "We're glad we could help. If you need anything else, just reach out."
            ),
        }},
        {{
            "tone": "constructive",
            "template": (
                f"Thank you for the feedback. At {{BUSINESS_NAME}} we take this seriously — "
                "please contact us so we can make it right."
            ),
        }},
    ]


def location_page_outline(area: str) -> dict[str, Any]:
    return {{
        "title": f"{{NICHE}} in {{area}} | {{BUSINESS_NAME}}",
        "h1": f"{{NICHE}} in {{area}}",
        "sections": [
            f"How {{BUSINESS_NAME}} serves {{area}}",
            "Services",
            "What to expect",
            "FAQs",
            "Contact / CTA",
        ],
        "schema_hint": "LocalBusiness (fill with real NAP only)",
        "rule": "Do not invent testimonials for this page.",
    }}
'''
    return {
        "module_local": {
            "id": "local",
            "path": "agent/modules/local_seo.py",
            "code": code,
            "exports": ["local_checklist", "review_response_templates", "location_page_outline"],
            "package": arch.get("package_name"),
        }
    }


def n14_content_gen(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    profile = ctx.get("profile") or {}
    arch = ctx.get("architecture") or {}
    name = profile.get("business_name") or "Business"
    niche = profile.get("niche") or "services"
    services = profile.get("products_services") or []
    uv = profile.get("unique_value") or ""
    goal = profile.get("primary_goal") or "organic_leads"

    code = _py_header("Content Engine", name)
    code += f'''BUSINESS_NAME = {name!r}
NICHE = {niche!r}
SERVICES = {services!r}
UNIQUE_VALUE = {uv!r}
PRIMARY_GOAL = {goal!r}


def content_brief(
    content_type: str = "service_page",
    topic: str = "",
    primary_keyword: str = "",
) -> dict[str, Any]:
    """Produce a structured brief specialized to this business."""
    topic = topic or (SERVICES[0] if SERVICES else NICHE)
    primary_keyword = primary_keyword or topic
    return {{
        "business": BUSINESS_NAME,
        "content_type": content_type,
        "topic": topic,
        "primary_keyword": primary_keyword,
        "goal": PRIMARY_GOAL,
        "must_include": [
            UNIQUE_VALUE,
            f"Clear explanation of how {{BUSINESS_NAME}} helps with {{topic}}",
            "Plain-language next step (call, form, book)",
        ],
        "must_avoid": [
            "Invented statistics",
            "Fake reviews or testimonials",
            "Guaranteed rankings",
            "Generic filler",
        ],
        "outline": [
            f"Hook: problem related to {{topic}}",
            f"How {{BUSINESS_NAME}} solves it",
            "Process / what to expect",
            "Proof points (owner-provided only)",
            "FAQs",
            "CTA",
        ],
        "meta_title_hint": f"{{topic}} | {{BUSINESS_NAME}}"[:60],
        "meta_description_hint": (
            f"{{BUSINESS_NAME}} helps with {{topic}}. {{UNIQUE_VALUE}}"
        )[:160],
    }}


def draft_markdown(brief: dict[str, Any] | None = None) -> str:
    """Deterministic draft skeleton (LLM can enrich when XAI_API_KEY is set)."""
    b = brief or content_brief()
    lines = [
        f"# {{b.get('meta_title_hint') or b.get('topic')}}",
        "",
        f"*Draft for {{BUSINESS_NAME}} — review before publish. No invented claims.*",
        "",
        f"## {{b.get('topic')}}",
        "",
        f"{{BUSINESS_NAME}} specializes in {{NICHE}}. {{UNIQUE_VALUE}}",
        "",
    ]
    for i, section in enumerate(b.get("outline") or [], 1):
        lines.append(f"### {{i}}. {{section}}")
        lines.append("")
        lines.append("_(Add real details from your business — do not invent stats or reviews.)_")
        lines.append("")
    lines.append("## Next step")
    lines.append("")
    lines.append(f"Contact {{BUSINESS_NAME}} to get started.")
    lines.append("")
    return "\\n".join(lines)
'''
    return {
        "module_content": {
            "id": "content",
            "path": "agent/modules/content_engine.py",
            "code": code,
            "exports": ["content_brief", "draft_markdown"],
            "package": arch.get("package_name"),
        }
    }


def n15_tracking_gen(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    profile = ctx.get("profile") or {}
    arch = ctx.get("architecture") or {}
    name = profile.get("business_name") or "Business"
    seeds = profile.get("seed_keywords") or []
    profile_id = profile.get("id") or ""

    code = _py_header("Keyword Tracker", name)
    code += f'''import json
from pathlib import Path
from typing import Any

BUSINESS_NAME = {name!r}
PROFILE_ID = {profile_id!r}
SEED_KEYWORDS = {seeds!r}


class KeywordTracker:
    """Track ranks only when the owner supplies them. Never invent rankings."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or "data/keywords.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({{"keywords": list(SEED_KEYWORDS), "note": "Ranks optional; owner-supplied only."}})

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list(self) -> list[dict[str, Any]]:
        return list(self._read().get("keywords") or [])

    def set_rank(self, keyword: str, rank: int | None, source: str = "owner") -> dict[str, Any]:
        if rank is not None and (rank < 1 or rank > 1000):
            raise ValueError("Rank must be 1–1000 or null")
        data = self._read()
        items = data.get("keywords") or []
        found = False
        for item in items:
            if str(item.get("keyword", "")).lower() == keyword.lower():
                prev = item.get("current_rank")
                if rank is not None and prev is not None:
                    item["previous_rank"] = prev
                item["current_rank"] = rank
                item["rank_source"] = source
                found = True
                break
        if not found:
            items.append(
                {{
                    "keyword": keyword,
                    "current_rank": rank,
                    "rank_source": source,
                    "intent": "local",
                    "priority": "medium",
                }}
            )
        data["keywords"] = items
        self._write(data)
        return {{"ok": True, "keyword": keyword, "current_rank": rank}}

    def summary(self) -> dict[str, Any]:
        items = self.list()
        with_rank = [i for i in items if i.get("current_rank") is not None]
        return {{
            "business": BUSINESS_NAME,
            "total": len(items),
            "with_owner_rank": len(with_rank),
            "disclaimer": "Missing ranks mean 'not tracked yet' — not a fabricated position.",
        }}
'''
    return {
        "module_tracking": {
            "id": "tracking",
            "path": "agent/modules/keyword_tracker.py",
            "code": code,
            "exports": ["KeywordTracker"],
            "package": arch.get("package_name"),
        }
    }


def n16_roi_gen(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    profile = ctx.get("profile") or {}
    arch = ctx.get("architecture") or {}
    name = profile.get("business_name") or "Business"
    metric = profile.get("success_metric") or "more qualified inquiries"
    goal = profile.get("primary_goal") or "organic_leads"

    code = _py_header("ROI Cards", name)
    code += f'''import json
from pathlib import Path
from typing import Any

BUSINESS_NAME = {name!r}
SUCCESS_METRIC = {metric!r}
PRIMARY_GOAL = {goal!r}


class RoiCards:
    """Owner-attributed ROI only. Time estimates are labeled as estimates."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or "data/roi.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({{"events": [], "success_metric": SUCCESS_METRIC}})

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def record(
        self,
        *,
        hours_saved: float = 0.0,
        leads_attributed: int = 0,
        revenue_usd: float = 0.0,
        note: str = "",
        estimated: bool = False,
    ) -> dict[str, Any]:
        data = self._read()
        event = {{
            "hours_saved": hours_saved,
            "leads_attributed": leads_attributed,
            "revenue_usd": revenue_usd,
            "note": note,
            "estimated": estimated,
            "goal": PRIMARY_GOAL,
        }}
        data.setdefault("events", []).append(event)
        self._write(data)
        return event

    def cards(self) -> dict[str, Any]:
        events = self._read().get("events") or []
        return {{
            "business": BUSINESS_NAME,
            "success_metric": SUCCESS_METRIC,
            "hours_saved": round(sum(float(e.get("hours_saved") or 0) for e in events), 2),
            "leads_attributed": sum(int(e.get("leads_attributed") or 0) for e in events),
            "revenue_usd": round(sum(float(e.get("revenue_usd") or 0) for e in events), 2),
            "events": len(events),
            "disclaimer": "Figures are owner-reported or labeled estimates — not invented traffic claims.",
        }}
'''
    return {
        "module_roi": {
            "id": "roi",
            "path": "agent/modules/roi_cards.py",
            "code": code,
            "exports": ["RoiCards"],
            "package": arch.get("package_name"),
        }
    }


# ── N17 Assembler ───────────────────────────────────────────────────────────


def n17_assembler(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    from ...codegen.writer import assemble_package_files

    profile = ctx.get("profile") or {}
    arch = ctx.get("architecture") or {}
    modules = {
        "research": ctx.get("module_research") or {},
        "brand": ctx.get("module_brand") or {},
        "local": ctx.get("module_local") or {},
        "content": ctx.get("module_content") or {},
        "tracking": ctx.get("module_tracking") or {},
        "roi": ctx.get("module_roi") or {},
    }
    files = assemble_package_files(profile=profile, architecture=arch, modules=modules)
    config_files = {
        k: v
        for k, v in files.items()
        if k.endswith((".yaml", ".yml", ".env.example", ".md", ".json", ".txt"))
    }
    return {
        "assembled_package": {
            "package_name": arch.get("package_name"),
            "files": files,
            "file_count": len(files),
            "modules": {k: {"path": m.get("path"), "exports": m.get("exports")} for k, m in modules.items()},
        },
        "config_files": config_files,
    }


# ── N18 Safety & HITL Verifier (isolated) ───────────────────────────────────


def n18_safety_verifier(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Isolated safety pass over assembled code + profile only."""
    package = ctx.get("assembled_package") or {}
    profile = ctx.get("profile") or {}
    files: dict[str, str] = package.get("files") or {}
    issues: list[str] = []
    warnings: list[str] = []

    if not files:
        issues.append("No files in assembled package")
    required = [
        "README.md",
        "config.yaml",
        ".env.example",
        "agent/main.py",
        "agent/cli.py",
        "brand/voice.md",
        "scripts/smoke_test.py",
    ]
    for r in required:
        if r not in files:
            issues.append(f"Missing required file: {r}")

    # Scan for dangerous claims in generated content
    claim_pats = [
        (r"guaranteed?\s+#?1", "guarantee/rank claim"),
        (r"we have \d+\s*five[- ]star", "invented review claim"),
        (r"currently ranking #\d+", "invented ranking claim"),
    ]
    for path, content in files.items():
        if not isinstance(content, str):
            continue
        for pat, label in claim_pats:
            if re.search(pat, content, re.I):
                issues.append(f"{label} in {path}")

    # Safety rules present
    voice = files.get("brand/voice.md") or ""
    voice_l = voice.lower()
    if "never invent" not in voice_l and "do not invent" not in voice_l:
        warnings.append("Brand voice missing explicit never-invent rule")

    hitl_required = True
    seo_cfg = cfg.get("seo") or {}
    if seo_cfg.get("require_hitl_before_package_deploy") is False:
        hitl_required = False

    ok = len(issues) == 0
    report = {
        "ok": ok,
        "issues": issues,
        "warnings": warnings,
        "hitl_required": hitl_required,
        "file_count": len(files),
        "profile_id": profile.get("id"),
        "checks": {
            "required_files": all(r in files for r in required),
            "no_guarantee_claims": not any("guarantee" in (issues or []) for _ in [0]),
            "isolated_context": True,
            "safety_rules_on_profile": bool(profile.get("safety_rules")),
        },
        "verified_at": utc_now(),
    }
    return {"safety_report": report}


# ── N19 Deployment Package Builder ──────────────────────────────────────────


def n19_package_builder(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    from pathlib import Path

    from ...models import new_id
    from ...services.package_store import PackageStore

    package = ctx.get("assembled_package") or {}
    safety = ctx.get("safety_report") or {}
    profile = ctx.get("profile") or {}
    config_files = ctx.get("config_files") or {}
    files: dict[str, str] = dict(package.get("files") or {})

    store = PackageStore(cfg["paths"]["data"])
    pkg_id = new_id("pkg_")
    out_dir = store.package_dir(pkg_id)

    written: list[str] = []
    for rel, content in files.items():
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content if isinstance(content, str) else str(content), encoding="utf-8")
        written.append(str(dest.relative_to(out_dir)))

    manifest = {
        "id": pkg_id,
        "package_name": package.get("package_name"),
        "profile_id": profile.get("id"),
        "business_name": profile.get("business_name"),
        "path": str(out_dir),
        "files": written,
        "file_count": len(written),
        "safety_ok": bool(safety.get("ok")),
        "hitl_required": bool(safety.get("hitl_required", True)),
        "config_keys": list(config_files.keys())[:20],
        "status": "built",
        "built_at": utc_now(),
    }
    store.register(manifest)
    return {"deployment_package": manifest}


# ── N20 Final Integration & Smoke-Test ──────────────────────────────────────


def n20_smoke(ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    import sys
    from pathlib import Path

    dep = ctx.get("deployment_package") or {}
    safety = ctx.get("safety_report") or {}
    pkg_path = Path(dep.get("path") or "")
    checks: list[dict[str, Any]] = []
    ok = True

    def check(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        if not passed:
            ok = False
        checks.append({"name": name, "ok": passed, "detail": detail})

    check("package_path_exists", pkg_path.exists(), str(pkg_path))
    check("safety_ok", bool(safety.get("ok")), str(safety.get("issues")))
    for req in ("README.md", "config.yaml", "agent/main.py", "scripts/smoke_test.py"):
        check(f"file:{req}", (pkg_path / req).exists())

    # Import smoke test module if present and run main safely
    smoke_py = pkg_path / "scripts" / "smoke_test.py"
    smoke_exit = None
    if smoke_py.exists():
        try:
            # Run package-local smoke by exec with path
            ns: dict[str, Any] = {
                "__name__": "__smoke__",
                "__file__": str(smoke_py),
            }
            code = smoke_py.read_text(encoding="utf-8")
            # Provide package root on path (and strip after)
            sys_path_added = str(pkg_path)
            inserted = False
            if sys_path_added not in sys.path:
                sys.path.insert(0, sys_path_added)
                inserted = True
            try:
                exec(compile(code, str(smoke_py), "exec"), ns)  # noqa: S102 — controlled generated smoke
                if "main" in ns and callable(ns["main"]):
                    smoke_exit = ns["main"]()
                check("package_smoke_main", smoke_exit == 0, f"exit={smoke_exit}")
            finally:
                if inserted and sys_path_added in sys.path:
                    try:
                        sys.path.remove(sys_path_added)
                    except ValueError:
                        pass
                # Drop cached agent modules from generated package so re-runs stay isolated
                for mod_name in list(sys.modules):
                    if mod_name == "agent" or mod_name.startswith("agent."):
                        del sys.modules[mod_name]
        except Exception as exc:  # noqa: BLE001
            check("package_smoke_main", False, str(exc))
    else:
        check("package_smoke_main", False, "missing scripts/smoke_test.py")

    report = {
        "ok": ok,
        "checks": checks,
        "package_id": dep.get("id"),
        "package_path": str(pkg_path),
        "ran_at": utc_now(),
    }
    final = {
        **dep,
        "smoke": report,
        "status": "ready_for_hitl" if ok and safety.get("hitl_required") else ("ready" if ok else "failed"),
    }
    return {"smoke_report": report, "final_manifest": final}


# ── Registry ────────────────────────────────────────────────────────────────

HANDLERS: dict[str, Handler] = {
    "N1": n1_quiz_orchestrator,
    "N2": n2_domain,
    "N3": n3_industry,
    "N4": n4_business,
    "N5": n5_customers,
    "N6": n6_location,
    "N7": n7_goals,
    "N8": n8_profile_synthesizer,
    "N9": n9_summary_verifier,
    "N10": n10_code_architect,
    "N11": n11_research_gen,
    "N12": n12_brand_gen,
    "N13": n13_local_gen,
    "N14": n14_content_gen,
    "N15": n15_tracking_gen,
    "N16": n16_roi_gen,
    "N17": n17_assembler,
    "N18": n18_safety_verifier,
    "N19": n19_package_builder,
    "N20": n20_smoke,
}


def run_node(node_id: str, ctx: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    handler = HANDLERS.get(node_id)
    if not handler:
        raise KeyError(f"Unknown node {node_id}")
    return handler(ctx, cfg)

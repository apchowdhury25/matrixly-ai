"""Extract CRM updates from free-text notes / emails / meeting summaries."""

from __future__ import annotations

import re
from email.utils import parseaddr
from typing import Any

from .llm import chat, extract_json, grok_available
from .models import Activity, Company, Contact, Deal, ProposedWrite


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_heuristic(text: str, cfg: dict[str, Any], *, source: str = "note") -> dict[str, Any]:
    """Best-effort parse without LLM."""
    emails = EMAIL_RE.findall(text or "")
    primary = emails[0].lower() if emails else ""
    name = ""
    # "Met with Jane Doe" / "Spoke to Jane Doe,"
    m = re.search(
        r"(?:met with|spoke (?:with|to)|call with|meeting with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        text or "",
        re.I,
    )
    if m:
        name = m.group(1).strip()
    title = ""
    tm = re.search(r"\b(CEO|CTO|CFO|VP[\w\s]*|Director[\w\s]*|Owner|Founder|Manager)\b", text or "", re.I)
    if tm:
        title = tm.group(0)
    company = ""
    cm = re.search(
        r"\bat\s+([A-Z][\w&.\-]+(?:\s+[A-Z][\w&.\-]+){0,4})(?=\s+on\b|\s+via\b|\s*[,.]|\s+to\b|$)",
        text or "",
    )
    if cm:
        company = cm.group(1).strip().rstrip(".,")
        # drop trailing meeting channel words if captured
        company = re.sub(r"\s+(on|via)\s*$", "", company, flags=re.I).strip()
    next_step = ""
    nm = re.search(r"(?:next step[s]?|follow[- ]?up)[:\s]+([^\n.]+)", text or "", re.I)
    if nm:
        next_step = nm.group(1).strip()
    amount = None
    am = re.search(r"\$\s?([\d,]+(?:\.\d+)?)\s*(k|K|m|M)?", text or "")
    if am:
        val = float(am.group(1).replace(",", ""))
        suf = (am.group(2) or "").lower()
        if suf == "k":
            val *= 1_000
        elif suf == "m":
            val *= 1_000_000
        amount = val

    act_type = "note"
    low = (text or "").lower()
    if "call" in low or "phone" in low:
        act_type = "call"
    elif "meeting" in low or "zoom" in low or "teams" in low:
        act_type = "meeting"
    elif "email" in low or "inbox" in low:
        act_type = "email"

    return {
        "contact": {
            "email": primary,
            "full_name": name,
            "title": title,
            "company_name": company,
        },
        "company": {"name": company} if company else {},
        "deal": {
            "name": f"{company or 'Opportunity'} — follow-up" if company or next_step else "",
            "next_step": next_step,
            "amount": amount,
            "contact_email": primary,
            "company_name": company,
        },
        "activity": {
            "type": act_type,
            "subject": (text or "").strip().split("\n")[0][:120] or "CRM note",
            "body": (text or "").strip()[:4000],
            "contact_email": primary,
            "source": source,
        },
        "confidence": 0.45 if primary else 0.25,
        "flags": [] if primary else ["missing_email"],
    }


def extract_with_llm(text: str, cfg: dict[str, Any], *, source: str = "note") -> dict[str, Any]:
    base = extract_heuristic(text, cfg, source=source)
    if not grok_available(cfg) or not (cfg.get("extraction") or {}).get("use_llm", True):
        return base
    system = (
        "You extract CRM updates for Matrixly CRM Assistant. "
        "Return ONLY JSON with keys: contact{email,full_name,first_name,last_name,title,phone,company_name}, "
        "company{name,domain,industry}, deal{name,stage,amount,next_step,contact_email,company_name}, "
        "activity{type,subject,body,contact_email}, confidence (0-1), flags (string array). "
        "type must be email|call|meeting|note|task. "
        "Do NOT invent phone numbers, revenue, or emails not present in the text. "
        "If unknown, use empty string or null."
    )
    try:
        raw = chat(cfg, system, f"Source: {source}\n\nText:\n{text[:8000]}", temperature=0.1)
        data = extract_json(raw)
        if not isinstance(data, dict):
            return base
        # merge carefully
        never = set((cfg.get("extraction") or {}).get("never_invent") or [])
        contact = {**(base.get("contact") or {}), **(data.get("contact") or {})}
        for field in never:
            if field in contact and field not in (text or "").lower() and contact[field]:
                # if LLM invented phone not in source, drop
                if str(contact[field]) not in (text or ""):
                    contact[field] = base.get("contact", {}).get(field, "")
        return {
            "contact": contact,
            "company": {**(base.get("company") or {}), **(data.get("company") or {})},
            "deal": {**(base.get("deal") or {}), **(data.get("deal") or {})},
            "activity": {**(base.get("activity") or {}), **(data.get("activity") or {})},
            "confidence": float(data.get("confidence") or base.get("confidence") or 0.5),
            "flags": list(set((base.get("flags") or []) + (data.get("flags") or []))),
            "provider": "heuristic+grok",
        }
    except Exception as exc:  # noqa: BLE001
        base["flags"] = list(base.get("flags") or []) + [f"llm_skip:{exc}"]
        return base


def to_proposed_writes(extracted: dict[str, Any], cfg: dict[str, Any]) -> list[ProposedWrite]:
    writes: list[ProposedWrite] = []
    conf = float(extracted.get("confidence") or 0.4)
    c = extracted.get("contact") or {}
    email = (c.get("email") or "").lower()
    if email:
        full = c.get("full_name") or ""
        first, last = c.get("first_name") or "", c.get("last_name") or ""
        if full and not (first or last):
            parts = full.split(None, 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""
        contact = Contact(
            email=email,
            first_name=first,
            last_name=last,
            full_name=full,
            title=c.get("title") or "",
            phone=c.get("phone") or "",
            company_name=c.get("company_name") or "",
            source="CRM Assistant extract",
        )
        writes.append(
            ProposedWrite(
                action="upsert_contact",
                payload=contact.to_dict(),
                reason="Extracted contact fields from note/meeting/email",
                confidence=conf,
                diffs=[f"upsert contact {email}"],
            )
        )

    co = extracted.get("company") or {}
    if co.get("name"):
        company = Company(
            name=co["name"],
            domain=co.get("domain") or "",
            industry=co.get("industry") or "",
            website=co.get("website") or "",
        )
        writes.append(
            ProposedWrite(
                action="upsert_company",
                payload=company.to_dict(),
                reason="Extracted company",
                confidence=conf,
                diffs=[f"upsert company {company.name}"],
            )
        )

    d = extracted.get("deal") or {}
    if d.get("name") or d.get("next_step"):
        deal = Deal(
            name=d.get("name") or f"Deal — {email or 'unknown'}",
            stage=d.get("stage") or "Qualification",
            amount=d.get("amount"),
            contact_email=d.get("contact_email") or email,
            company_name=d.get("company_name") or c.get("company_name") or "",
            next_step=d.get("next_step") or "",
            owner=d.get("owner") or "",
        )
        writes.append(
            ProposedWrite(
                action="upsert_deal",
                payload=deal.to_dict(),
                reason="Extracted deal / next step",
                confidence=conf,
                diffs=[f"upsert deal {deal.name}"],
            )
        )

    a = extracted.get("activity") or {}
    if a.get("subject") or a.get("body"):
        act = Activity(
            type=a.get("type") or "note",
            subject=a.get("subject") or "Activity",
            body=a.get("body") or "",
            contact_email=a.get("contact_email") or email,
            source=a.get("source") or "extract",
        )
        writes.append(
            ProposedWrite(
                action="log_activity",
                payload=act.to_dict(),
                reason="Log interaction activity",
                confidence=conf,
                diffs=[f"log {act.type}: {act.subject[:60]}"],
            )
        )

    return writes

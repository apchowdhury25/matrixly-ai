"""Inbox triage: score, label, and report."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from .llm import chat, extract_json, grok_available
from .models import EmailMessage
from .urgent import UrgencyResult, score_message


class SupportsTriage(Protocol):
    def fetch_inbox(
        self,
        max_results: int = 40,
        unread_only: bool = True,
        extra_query: str = "",
    ) -> list[EmailMessage]: ...

    def ensure_label(self, name: str) -> str: ...

    def apply_labels(
        self,
        message_id: str,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> None: ...


@dataclass
class TriageItem:
    message: dict[str, Any]
    score: float
    is_urgent: bool
    category: str
    reasons: list[str]
    labels_applied: list[str]


def _llm_refine(cfg: dict, items: list[tuple[EmailMessage, UrgencyResult]]) -> dict[str, dict]:
    """Optional Grok pass to refine categories for ambiguous items."""
    if not grok_available(cfg) or not items:
        return {}

    payload = [
        {
            "id": m.id,
            "subject": m.subject,
            "from": m.from_email,
            "snippet": m.snippet,
            "rule_category": r.category,
            "rule_score": r.score,
        }
        for m, r in items[:25]
    ]
    system = (
        "You are the Matrixly.AI Email Assistant for Matrix Bazaar "
        "(usmatrixbazaar.com / matrixbazaar.com). "
        "Classify each email as one of: urgent, needs_reply, fyi, newsletter, automated, waiting. "
        "Return ONLY a JSON object mapping message id → "
        '{"category": "...", "score": 0-1, "reason": "..."}. '
        "Prioritize customer, payment, legal, shipping exceptions, and time-bound asks as urgent."
    )
    user = f"Emails:\n{payload}"
    try:
        raw = chat(cfg, system, user, temperature=0.1)
        data = extract_json(raw)
        if isinstance(data, dict):
            return data
    except Exception as exc:  # noqa: BLE001
        print(f"warn: LLM refine skipped: {exc}")
    return {}


def triage_inbox(
    client: SupportsTriage,
    cfg: dict[str, Any],
    *,
    apply_labels: bool = True,
    max_results: int | None = None,
    use_llm: bool = True,
) -> list[TriageItem]:
    gmail_cfg = cfg.get("gmail") or {}
    imap_cfg = cfg.get("imap") or {}
    triage_cfg = cfg.get("triage") or {}
    label_names: dict[str, str] = triage_cfg.get("labels") or {}
    max_n = max_results or int(
        imap_cfg.get("max_results") or gmail_cfg.get("max_results") or 40
    )
    unread_only = bool(triage_cfg.get("unread_only", True))

    messages = client.fetch_inbox(max_results=max_n, unread_only=unread_only)

    # Pre-score with rules
    scored: list[tuple[EmailMessage, UrgencyResult]] = [
        (m, score_message(m, cfg)) for m in messages
    ]

    refinements: dict[str, dict] = {}
    if use_llm:
        refinements = _llm_refine(cfg, scored)

    # Ensure labels exist once
    label_ids: dict[str, str] = {}
    if apply_labels:
        for key, name in label_names.items():
            label_ids[key] = client.ensure_label(name)

    results: list[TriageItem] = []
    for msg, rule in scored:
        category = rule.category
        score = rule.score
        reasons = list(rule.reasons)
        is_urgent = rule.is_urgent

        ref = refinements.get(msg.id) or refinements.get(str(msg.id))
        if isinstance(ref, dict):
            if ref.get("category") in {
                "urgent",
                "needs_reply",
                "fyi",
                "newsletter",
                "automated",
                "waiting",
            }:
                category = ref["category"]
            if isinstance(ref.get("score"), (int, float)):
                score = float(ref["score"])
            if ref.get("reason"):
                reasons.append(f"Grok: {ref['reason']}")
            is_urgent = category == "urgent" or score >= float(
                (cfg.get("urgency") or {}).get("urgent_threshold") or 0.65
            )

        applied: list[str] = []
        if apply_labels and category in label_ids:
            client.apply_labels(msg.id, add=[label_ids[category]])
            applied.append(label_names[category])
            # Urgent also gets needs_reply when a human response is expected
            if category == "urgent" and "needs_reply" in label_ids:
                client.apply_labels(msg.id, add=[label_ids["needs_reply"]])
                applied.append(label_names["needs_reply"])

        results.append(
            TriageItem(
                message=msg.to_dict(),
                score=round(score, 3),
                is_urgent=is_urgent,
                category=category,
                reasons=reasons,
                labels_applied=applied,
            )
        )

    # Urgent first, then score desc
    results.sort(key=lambda x: (not x.is_urgent, -x.score))
    return results


def triage_report(items: list[TriageItem]) -> str:
    lines = ["# Inbox Triage Report", ""]
    if not items:
        lines.append("No matching messages.")
        return "\n".join(lines)

    urgent = [i for i in items if i.is_urgent or i.category == "urgent"]
    needs = [i for i in items if i.category == "needs_reply"]
    lines.append(f"**Total reviewed:** {len(items)}")
    lines.append(f"**Urgent:** {len(urgent)}")
    lines.append(f"**Needs reply:** {len(needs)}")
    lines.append("")

    def _section(title: str, rows: list[TriageItem]) -> None:
        lines.append(f"## {title}")
        if not rows:
            lines.append("_None_")
            lines.append("")
            return
        for i in rows:
            m = i.message
            lines.append(
                f"- **{m.get('subject') or '(no subject)'}** — {m.get('from_email')} "
                f"(score {i.score}, {i.category})"
            )
            if i.reasons:
                lines.append(f"  - {'; '.join(i.reasons[:3])}")
            if i.labels_applied:
                lines.append(f"  - Labels: {', '.join(i.labels_applied)}")
        lines.append("")

    _section("Urgent", urgent)
    _section("Needs reply", needs)
    _section(
        "Other",
        [i for i in items if i not in urgent and i not in needs],
    )
    return "\n".join(lines)


def items_as_jsonable(items: list[TriageItem]) -> list[dict]:
    return [asdict(i) for i in items]

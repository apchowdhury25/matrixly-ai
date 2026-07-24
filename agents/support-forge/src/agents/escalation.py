"""Escalation Manager — ticket handoff + customer acknowledgment."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..integrations.tickets import TicketStore
from ..models import SupportState
from ..services.followup import FollowupQueue
from ..services.hitl import HitlQueue


def run_escalation(
    state: SupportState,
    cfg: dict,
    tickets: TicketStore,
    hitl: HitlQueue,
    followups: FollowupQueue,
) -> SupportState:
    pack = _build_pack(state, cfg)

    # Ensure ticket exists
    if not state.ticket_id:
        t = tickets.create(
            subject=pack["subject"],
            channel=state.channel.value,
            customer=state.customer,
            body=state.text,
            priority=pack["priority"],
            tags=["escalated", state.topic.value, state.urgency.value],
            metadata={"session_id": state.session_id, "reason": state.escalate_reason},
        )
        state.ticket_id = t.id
    else:
        t = tickets.get(state.ticket_id)
        if t:
            t.status = "escalated"
            if "escalated" not in t.tags:
                t.tags.append("escalated")
            t.priority = pack["priority"]
            t.subject = pack["subject"]
            tickets.save(t)

    tickets.add_message(
        state.ticket_id,
        role="system",
        content=pack["summary"],
        meta={
            "recommended_next_steps": pack["recommended_next_steps"],
            "confidence": state.confidence,
            "citations": [h.model_dump() for h in state.kb_hits],
        },
    )
    tickets.update_fields(
        state.ticket_id,
        status="escalated",
        confidence=state.confidence,
        topic=state.topic.value,
        urgency=state.urgency.value,
        sentiment=state.sentiment.value,
        citations=[h.model_dump() for h in state.kb_hits],
    )

    # Customer-facing ack becomes the answer if escalating
    state.answer = pack["customer_facing_ack"]
    state.requires_human = True

    # Queue human review of any draft external action
    action = hitl.enqueue(
        kind="publish_reply",
        payload={
            "reply": state.answer,
            "original": state.text,
            "escalation_summary": pack["summary"],
            "channel": state.channel.value,
        },
        ticket_id=state.ticket_id,
        session_id=state.session_id,
    )
    state.hitl_id = action.id

    # Schedule a follow-up if email known
    if state.customer.email:
        followups.schedule(
            ticket_id=state.ticket_id,
            message=(
                f"Following up on ticket {state.ticket_id}: "
                "A specialist is reviewing your request."
            ),
            hours_from_now=24,
            customer_email=state.customer.email,
        )

    state.add_audit(
        "escalated",
        ticket_id=state.ticket_id,
        hitl_id=state.hitl_id,
        priority=pack["priority"],
    )
    return state


def _build_pack(state: SupportState, cfg: dict) -> dict[str, Any]:
    default = {
        "subject": f"[{state.urgency.value.upper()}] {state.topic.value}: {state.text[:60]}",
        "priority": _priority(state),
        "summary": (
            f"Customer message requires human review. Topic={state.topic.value}, "
            f"urgency={state.urgency.value}, sentiment={state.sentiment.value}, "
            f"confidence={state.confidence:.2f}. Reason={state.escalate_reason or 'low confidence or policy'}."
        ),
        "recommended_next_steps": [
            "Review conversation and knowledge citations",
            "Reply to customer within SLA",
            "Update ticket status when resolved",
        ],
        "customer_facing_ack": (
            "Thanks for your patience — I've escalated this to a human specialist with your full conversation context. "
            "You'll hear back as soon as possible during business hours."
        ),
    }

    if not llm.grok_available(cfg):
        return default

    try:
        system = prompt_text("escalation") or "Create escalation JSON pack."
        user = (
            f"Message: {state.text}\n"
            f"Urgency: {state.urgency.value}\nSentiment: {state.sentiment.value}\n"
            f"Topic: {state.topic.value}\nConfidence: {state.confidence}\n"
            f"Escalate reason: {state.escalate_reason}\nPII flags: {state.pii_flags}"
        )
        content, tin, tout = llm.chat(cfg, system, user)
        state.usage_tokens_in += tin
        state.usage_tokens_out += tout
        data = llm.extract_json(content)
        for k in default:
            if data.get(k):
                default[k] = data[k]
        if not default.get("priority"):
            default["priority"] = _priority(state)
    except Exception as e:
        state.add_audit("escalation_llm_fallback", error=str(e))
    return default


def _priority(state: SupportState) -> str:
    if state.urgency.value == "critical":
        return "urgent"
    if state.urgency.value == "high" or state.sentiment.value == "angry":
        return "high"
    if state.urgency.value == "low":
        return "low"
    return "normal"

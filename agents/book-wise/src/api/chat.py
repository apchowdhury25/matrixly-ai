"""Chat endpoints for embed widget."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..models import ChatRequest, ChatResponse, ChatSessionRequest, ChatSessionResponse, Customer
from ..orchestrator import BookWise
from .deps import rate_limiter, require_widget_or_api_key


def build_chat_router(agent: BookWise, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/chat", tags=["chat"])
    auth = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("chat_per_minute") or 40)

    @router.post("/session", response_model=ChatSessionResponse)
    async def create_session(
        body: ChatSessionRequest,
        request: Request,
        _: None = Depends(auth),
    ) -> ChatSessionResponse:
        rate_limiter.check(f"chat:{request.client.host if request.client else 'x'}", limit)
        doc = agent.sessions.create(customer=body.customer, metadata=body.metadata)
        welcome = (
            (cfg.get("channels") or {}).get("chat") or {}
        ).get("welcome") or "Hi! How can I help you book?"
        return ChatSessionResponse(session_id=doc["session_id"], welcome=welcome)

    @router.post("", response_model=ChatResponse)
    async def chat(
        body: ChatRequest,
        request: Request,
        _: None = Depends(auth),
    ) -> ChatResponse:
        rate_limiter.check(f"chat:{request.client.host if request.client else 'x'}", limit)
        state = agent.process(
            body.message,
            channel=body.channel,
            session_id=body.session_id,
            customer=body.customer or Customer(),
            selected_slot=body.selected_slot,
            service_id=body.service_id,
            booking_id=body.booking_id,
            metadata=body.metadata,
        )
        return ChatResponse(
            session_id=state.session_id,
            message_id=state.message_id,
            reply=state.reply,
            intent=state.intent,
            proposals=state.proposals,
            booking=state.booking,
            requires_human=state.requires_human,
            hitl_id=state.hitl_id,
            intake_missing=state.intake_missing,
            usage={
                "tokens_in": state.usage_tokens_in,
                "tokens_out": state.usage_tokens_out,
                "estimated_cost_usd": state.estimated_cost_usd,
            },
        )

    return router

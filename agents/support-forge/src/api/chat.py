"""Chat session endpoints for the embed widget."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..models import (
    ChatRequest,
    ChatResponse,
    ChatSessionRequest,
    ChatSessionResponse,
    Customer,
)
from ..orchestrator import SupportForge
from .deps import rate_limiter, require_widget_or_api_key


def build_chat_router(forge: SupportForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1/chat", tags=["chat"])
    auth = require_widget_or_api_key(cfg)
    limit = int((cfg.get("rate_limit") or {}).get("chat_per_minute") or 30)

    @router.post("/session", response_model=ChatSessionResponse)
    async def create_session(
        body: ChatSessionRequest,
        request: Request,
        _: None = Depends(auth),
    ) -> ChatSessionResponse:
        rate_limiter.check(f"chat:{request.client.host if request.client else 'x'}", limit)
        doc = forge.sessions.create(customer=body.customer, metadata=body.metadata)
        welcome = (
            (cfg.get("channels") or {}).get("chat") or {}
        ).get("welcome") or "Hi! How can I help?"
        return ChatSessionResponse(session_id=doc["session_id"], welcome=welcome)

    @router.post("", response_model=ChatResponse)
    async def chat(
        body: ChatRequest,
        request: Request,
        _: None = Depends(auth),
    ) -> ChatResponse:
        rate_limiter.check(f"chat:{request.client.host if request.client else 'x'}", limit)
        state = forge.process(
            body.message,
            channel=body.channel,
            session_id=body.session_id,
            customer=body.customer or Customer(),
            metadata=body.metadata,
        )
        return ChatResponse(
            session_id=state.session_id,
            message_id=state.message_id,
            reply=state.answer,
            action=state.action,
            confidence=state.confidence,
            urgency=state.urgency,
            sentiment=state.sentiment,
            topic=state.topic,
            ticket_id=state.ticket_id,
            citations=state.kb_hits,
            requires_human=state.requires_human,
            hitl_id=state.hitl_id,
            usage={
                "tokens_in": state.usage_tokens_in,
                "tokens_out": state.usage_tokens_out,
                "estimated_cost_usd": state.estimated_cost_usd,
            },
        )

    return router

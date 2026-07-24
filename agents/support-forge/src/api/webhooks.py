"""Inbound form/email/generic webhooks."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..integrations.form_webhook import form_to_ingest
from ..models import Channel, Customer, EmailWebhook, FormWebhook, IngestMessage
from ..orchestrator import SupportForge
from .deps import require_api_key


def build_webhook_router(forge: SupportForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["webhooks"])
    auth = require_api_key(cfg)

    def _run(ingest: IngestMessage):
        state = forge.process(
            ingest.text,
            channel=ingest.channel,
            session_id=ingest.session_id,
            customer=ingest.customer,
            subject=ingest.subject or "",
            metadata=ingest.metadata,
        )
        return {
            "ok": True,
            "session_id": state.session_id,
            "ticket_id": state.ticket_id,
            "action": state.action.value,
            "confidence": state.confidence,
            "reply": state.answer,
            "requires_human": state.requires_human,
            "hitl_id": state.hitl_id,
        }

    @router.post("/webhooks/form")
    async def form_hook(body: FormWebhook, _: None = Depends(auth)):
        return _run(form_to_ingest(body))

    @router.post("/webhooks/email")
    async def email_hook(body: EmailWebhook, _: None = Depends(auth)):
        text = body.body
        if body.subject:
            text = f"Subject: {body.subject}\n\n{text}"
        ingest = IngestMessage(
            channel=Channel.email,
            text=text,
            customer=Customer(name=body.from_name, email=body.from_email),
            subject=body.subject,
            metadata={"email_message_id": body.message_id, **(body.metadata or {})},
        )
        return _run(ingest)

    @router.post("/ingest/message")
    async def ingest(body: IngestMessage, _: None = Depends(auth)):
        return _run(body)

    return router

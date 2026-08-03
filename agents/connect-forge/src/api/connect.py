"""ConnectForge public + admin API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from ..models import HitlDecision, SendSmsRequest, StartConversationRequest, VoiceCallRequest
from ..orchestrator import ConnectForge
from .deps import rate_limiter, require_api_key, require_widget_or_api_key


def build_connect_router(agent: ConnectForge, cfg: dict) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["connect-forge"])
    admin = require_api_key(cfg)
    auth = require_widget_or_api_key(cfg)
    sms_limit = int((cfg.get("rate_limit") or {}).get("sms_per_minute") or 20)
    wh_limit = int((cfg.get("rate_limit") or {}).get("webhook_per_minute") or 120)

    @router.get("/status")
    async def status(_: None = Depends(auth)):
        return agent.status()

    @router.post("/sms/send")
    async def send_sms(body: SendSmsRequest, request: Request, _: None = Depends(auth)):
        rate_limiter.check(f"sms:{request.client.host if request.client else 'x'}", sms_limit)
        if not body.to.strip() or not body.body.strip():
            raise HTTPException(400, "to and body required")
        result = agent.send_sms(
            body.to,
            body.body,
            skip_hitl=body.force_send,
            conversation_sid=body.conversation_sid,
            language=body.language,
        )
        return result

    @router.post("/conversations/start")
    async def start_conversation(
        body: StartConversationRequest, request: Request, _: None = Depends(auth)
    ):
        rate_limiter.check(f"sms:{request.client.host if request.client else 'x'}", sms_limit)
        if not body.to.strip():
            raise HTTPException(400, "to required")
        return agent.start_conversation(body.to, body.body, language=body.language)

    @router.get("/messages")
    async def list_messages(limit: int = 50, _: None = Depends(auth)):
        return {"items": [m.model_dump() for m in agent.store.list_messages(limit=limit)]}

    @router.get("/conversations")
    async def list_conversations(limit: int = 50, _: None = Depends(auth)):
        return {
            "items": [c.model_dump() for c in agent.store.list_conversations(limit=limit)]
        }

    @router.get("/calls")
    async def list_calls(limit: int = 30, _: None = Depends(auth)):
        return {"items": [c.model_dump() for c in agent.store.list_calls(limit=limit)]}

    @router.post("/voice/call")
    async def voice_call(body: VoiceCallRequest, _: None = Depends(admin)):
        if not body.to.strip():
            raise HTTPException(400, "to required")
        return agent.start_call(body.to, say=body.say)

    @router.get("/hitl/pending")
    async def hitl_pending(_: None = Depends(auth)):
        return {"items": [a.model_dump() for a in agent.hitl.list_pending()]}

    @router.post("/hitl/{hitl_id}/decide")
    async def hitl_decide(hitl_id: str, body: HitlDecision, _: None = Depends(admin)):
        if body.action == "approve":
            return agent.approve_hitl(hitl_id, decided_by=body.decided_by, note=body.note)
        if body.action == "reject":
            return agent.reject_hitl(hitl_id, decided_by=body.decided_by, note=body.note)
        raise HTTPException(400, "action must be approve or reject")

    @router.post("/settings/test-mode")
    async def set_test_mode(enabled: bool = True, _: None = Depends(admin)):
        return agent.set_test_mode(enabled)

    @router.post("/settings/hitl-outbound")
    async def set_hitl(required: bool = True, _: None = Depends(admin)):
        return agent.set_hitl_outbound(required)

    @router.post("/demo")
    async def demo(_: None = Depends(auth)):
        return agent.demo()

    # ── Twilio webhooks (no API key — secured by network / Twilio signature later) ──

    @router.post("/webhooks/sms")
    async def webhook_sms(
        request: Request,
        From: str = Form(default=""),
        To: str = Form(default=""),
        Body: str = Form(default=""),
        MessageSid: str = Form(default=""),
    ):
        rate_limiter.check(
            f"wh:{request.client.host if request.client else 'x'}", wh_limit
        )
        result = agent.handle_inbound_sms(From, To, Body, MessageSid)
        # If reply is pending HITL, send empty TwiML (operator will approve)
        # If already sent, avoid double-send via Messages API — return empty Response
        # (we already sent via REST for consistency with HITL)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
        )

    @router.post("/webhooks/voice/status")
    async def webhook_voice_status(request: Request):
        rate_limiter.check(
            f"wh:{request.client.host if request.client else 'x'}", wh_limit
        )
        form = await request.form()
        agent.audit.write(
            "voice_status",
            call_sid=str(form.get("CallSid") or ""),
            status=str(form.get("CallStatus") or ""),
        )
        return {"ok": True}

    @router.get("/webhooks/voice/twiml")
    async def voice_twiml():
        """Optional webhook URL style TwiML for expandable Conversation Relay."""
        say = (cfg.get("voice") or {}).get("say_message") or "Hello from Matrixly ConnectForge."
        safe = (
            say.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Response><Say>{safe}</Say><Hangup/></Response>"
        )
        return PlainTextResponse(xml, media_type="application/xml")

    return router

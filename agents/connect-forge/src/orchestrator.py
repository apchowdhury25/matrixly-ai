"""ConnectForge orchestrator — SMS, Conversations, voice stub, HITL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .integrations.twilio_client import TwilioService, normalize_e164
from .llm import generate_reply
from .models import (
    CallRecord,
    ConversationThread,
    MessageDirection,
    MessageStatus,
    SmsMessage,
    new_id,
)
from .services.audit import AuditLog
from .services.hitl import HitlQueue
from .services.store import MessageStore


class ConnectForge:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.store = MessageStore(data)
        self.hitl = HitlQueue(data)
        self.audit = AuditLog(data)
        self.twilio = TwilioService(cfg)

    def status(self) -> dict[str, Any]:
        conn = self.twilio.connection_status()
        hitl_cfg = self.cfg.get("hitl") or {}
        return {
            "service": "connect-forge",
            "version": "1.0.0",
            "connection": conn,
            "messages": len(self.store.list_messages(limit=500)),
            "conversations": len(self.store.list_conversations(limit=500)),
            "pending_hitl": len(self.hitl.list_pending()),
            "calls": len(self.store.list_calls(limit=200)),
            "hitl_outbound_required": bool(
                hitl_cfg.get("require_approval_outbound", True)
            )
            and not hitl_cfg.get("auto_approve")
            and (hitl_cfg.get("mode") or "external_only") != "off",
            "llm": "grok" if (self.cfg.get("xai") or {}).get("api_key") else "rules",
            "market": (self.cfg.get("business") or {}).get("market") or "Houston, TX",
        }

    def _hitl_required(self) -> bool:
        hitl = self.cfg.get("hitl") or {}
        if hitl.get("auto_approve"):
            return False
        if (hitl.get("mode") or "external_only") == "off":
            return False
        return bool(hitl.get("require_approval_outbound", True))

    def set_test_mode(self, enabled: bool) -> dict[str, Any]:
        tw = self.cfg.setdefault("twilio", {})
        tw["test_mode"] = bool(enabled)
        self.twilio = TwilioService(self.cfg)
        self.audit.write("test_mode_set", enabled=enabled)
        return self.twilio.connection_status()

    def set_hitl_outbound(self, required: bool) -> dict[str, Any]:
        hitl = self.cfg.setdefault("hitl", {})
        hitl["require_approval_outbound"] = bool(required)
        self.audit.write("hitl_outbound_set", required=required)
        return {"require_approval_outbound": required}

    def send_sms(
        self,
        to: str,
        body: str,
        *,
        skip_hitl: bool = False,
        conversation_sid: str | None = None,
        language: str = "en",
    ) -> dict[str, Any]:
        to_n = normalize_e164(to)
        body = (body or "").strip()
        if not body:
            return {"ok": False, "error": "Message body required"}

        msg = SmsMessage(
            id=new_id("msg_"),
            direction=MessageDirection.outbound,
            from_number=self.twilio.from_number or "",
            to_number=to_n,
            body=body,
            status=MessageStatus.queued,
            conversation_sid=conversation_sid,
            language=language,
        )

        if self._hitl_required() and not skip_hitl:
            action = self.hitl.enqueue(
                kind="outbound_sms",
                payload={
                    "message_id": msg.id,
                    "to": to_n,
                    "body": body,
                    "conversation_sid": conversation_sid,
                },
            )
            msg.status = MessageStatus.pending_approval
            msg.hitl_id = action.id
            self.store.save_message(msg)
            self.audit.write("sms_pending_hitl", message_id=msg.id, hitl_id=action.id, to=to_n)
            return {
                "ok": True,
                "pending_approval": True,
                "message": msg.model_dump(),
                "hitl_id": action.id,
                "note": "Outbound SMS waiting for human approval in the HITL queue.",
            }

        return self._deliver_outbound(msg, conversation_sid=conversation_sid)

    def _deliver_outbound(
        self,
        msg: SmsMessage,
        conversation_sid: str | None = None,
    ) -> dict[str, Any]:
        result = self.twilio.send_sms(msg.to_number, msg.body)
        if not result.get("ok"):
            msg.status = MessageStatus.failed
            msg.error = result.get("error")
            self.store.save_message(msg)
            self.audit.write("sms_failed", message_id=msg.id, error=msg.error)
            return {"ok": False, "error": msg.error, "message": msg.model_dump()}

        msg.twilio_sid = result.get("sid")
        msg.trial_note = result.get("trial_note")
        msg.status = MessageStatus.mocked if result.get("mocked") else MessageStatus.sent
        if conversation_sid:
            msg.conversation_sid = conversation_sid
            self.twilio.post_conversation_message(conversation_sid, msg.body, author="connectforge")
        self.store.save_message(msg)

        # Attach to local conversation thread
        conv = self.store.find_conversation_by_number(msg.to_number)
        if conv:
            if msg.id not in conv.messages:
                conv.messages.append(msg.id)
            conv.last_body = msg.body
            if conversation_sid:
                conv.conversation_sid = conversation_sid
            self.store.save_conversation(conv)

        self.audit.write(
            "sms_sent",
            message_id=msg.id,
            sid=msg.twilio_sid,
            mocked=bool(result.get("mocked")),
            to=msg.to_number,
        )
        return {
            "ok": True,
            "pending_approval": False,
            "message": msg.model_dump(),
            "twilio": {k: result.get(k) for k in ("sid", "status", "mocked", "trial_note")},
        }

    def approve_hitl(
        self,
        hitl_id: str,
        *,
        decided_by: str = "owner",
        note: str = "",
    ) -> dict[str, Any]:
        action = self.hitl.decide(hitl_id, approve=True, decided_by=decided_by, note=note)
        if not action:
            return {"ok": False, "error": "HITL action not found"}
        payload = action.payload or {}
        msg = self.store.get_message(payload.get("message_id") or "")
        if not msg:
            # Reconstruct from payload
            msg = SmsMessage(
                id=payload.get("message_id") or new_id("msg_"),
                direction=MessageDirection.outbound,
                to_number=payload.get("to") or "",
                body=payload.get("body") or "",
                from_number=self.twilio.from_number or "",
                conversation_sid=payload.get("conversation_sid"),
            )
        result = self._deliver_outbound(msg, conversation_sid=payload.get("conversation_sid"))
        self.audit.write("hitl_approved", hitl_id=hitl_id)
        return {"ok": True, "action": action.model_dump(), "send": result}

    def reject_hitl(
        self,
        hitl_id: str,
        *,
        decided_by: str = "owner",
        note: str = "",
    ) -> dict[str, Any]:
        action = self.hitl.decide(hitl_id, approve=False, decided_by=decided_by, note=note)
        if not action:
            return {"ok": False, "error": "HITL action not found"}
        payload = action.payload or {}
        msg = self.store.get_message(payload.get("message_id") or "")
        if msg:
            msg.status = MessageStatus.failed
            msg.error = "Rejected by human review"
            self.store.save_message(msg)
        self.audit.write("hitl_rejected", hitl_id=hitl_id)
        return {"ok": True, "action": action.model_dump()}

    def start_conversation(self, to: str, body: str, language: str = "en") -> dict[str, Any]:
        to_n = normalize_e164(to)
        conv_result = self.twilio.ensure_conversation(to_n)
        conversation_sid = conv_result.get("conversation_sid")

        existing = self.store.find_conversation_by_number(to_n)
        if existing:
            thread = existing
            if conversation_sid and conv_result.get("ok"):
                thread.conversation_sid = conversation_sid
        else:
            thread = ConversationThread(
                id=new_id("conv_"),
                conversation_sid=conversation_sid if conv_result.get("ok") else None,
                participant_number=to_n,
            )
        self.store.save_conversation(thread)

        send = self.send_sms(
            to_n,
            body,
            conversation_sid=thread.conversation_sid,
            language=language,
        )
        if send.get("message", {}).get("id"):
            mid = send["message"]["id"]
            if mid not in thread.messages:
                thread.messages.append(mid)
            thread.last_body = body
            self.store.save_conversation(thread)

        return {
            "ok": True,
            "conversation": thread.model_dump(),
            "twilio_conversations": conv_result,
            "send": send,
        }

    def handle_inbound_sms(
        self,
        from_number: str,
        to_number: str,
        body: str,
        message_sid: str = "",
    ) -> dict[str, Any]:
        from_n = normalize_e164(from_number)
        to_n = normalize_e164(to_number)
        inbound = SmsMessage(
            id=new_id("msg_"),
            direction=MessageDirection.inbound,
            from_number=from_n,
            to_number=to_n,
            body=body or "",
            status=MessageStatus.received,
            twilio_sid=message_sid or None,
        )
        self.store.save_message(inbound)

        thread = self.store.find_conversation_by_number(from_n)
        if not thread:
            thread = ConversationThread(
                id=new_id("conv_"),
                participant_number=from_n,
            )
        thread.messages.append(inbound.id)
        thread.last_body = body or ""
        self.store.save_conversation(thread)

        # Build short history for LLM
        history: list[dict[str, str]] = []
        for mid in thread.messages[-10:]:
            m = self.store.get_message(mid)
            if not m:
                continue
            role = "user" if m.direction == MessageDirection.inbound else "assistant"
            history.append({"role": role, "content": m.body})

        reply_text, meta = generate_reply(
            self.cfg,
            body or "",
            history=history,
            language="auto",
        )

        # Auto-reply: still respect HITL for outbound
        send = self.send_sms(
            from_n,
            reply_text,
            conversation_sid=thread.conversation_sid,
            language=meta.get("language") or "auto",
        )
        self.audit.write(
            "inbound_handled",
            inbound_id=inbound.id,
            reply_source=meta.get("source"),
            pending=bool(send.get("pending_approval")),
        )
        return {
            "ok": True,
            "inbound": inbound.model_dump(),
            "reply": send,
            "llm": meta,
            "conversation_id": thread.id,
        }

    def start_call(self, to: str, say: str | None = None) -> dict[str, Any]:
        voice_cfg = self.cfg.get("voice") or {}
        if not voice_cfg.get("enabled", True):
            return {"ok": False, "error": "Voice disabled in config"}
        text = (say or voice_cfg.get("say_message") or "Hello from Matrixly ConnectForge.").strip()
        public = self.cfg.get("public_base_url") or ""
        status_cb = f"{public}/v1/webhooks/voice/status" if public else None
        result = self.twilio.start_voice_call(to, text, status_callback=status_cb)
        rec = CallRecord(
            id=new_id("call_"),
            to_number=normalize_e164(to),
            from_number=self.twilio.from_number or "",
            status=result.get("status") or ("failed" if not result.get("ok") else "initiated"),
            twilio_sid=result.get("sid"),
            error=result.get("error"),
            note=result.get("note") or "",
        )
        self.store.save_call(rec)
        self.audit.write("voice_call", call_id=rec.id, ok=result.get("ok"), sid=rec.twilio_sid)
        return {"ok": bool(result.get("ok")), "call": rec.model_dump(), "twilio": result}

    def demo(self) -> dict[str, Any]:
        """Offline-friendly demo path (mock Twilio)."""
        demo_to = "+17135550123"
        # Ensure verified for test mode
        tw = self.cfg.setdefault("twilio", {})
        verified = list(tw.get("verified_numbers") or [])
        if demo_to not in verified:
            verified.append(demo_to)
            tw["verified_numbers"] = verified
            self.twilio = TwilioService(self.cfg)

        # Temporarily allow auto-send for demo clarity if no credentials
        was_hitl = self._hitl_required()
        if not self.twilio.configured:
            self.cfg.setdefault("hitl", {})["auto_approve"] = True

        start = self.start_conversation(
            demo_to,
            "Hi from ConnectForge demo — thanks for contacting our Houston team. How can we help?",
        )
        inbound = self.handle_inbound_sms(
            from_number=demo_to,
            to_number=self.twilio.from_number or "+17135550999",
            body="Can you confirm my AC repair appointment tomorrow in Katy?",
            message_sid="SM_demo_inbound",
        )
        call = self.start_call(demo_to)

        if was_hitl and not self.twilio.configured:
            self.cfg.setdefault("hitl", {})["auto_approve"] = False

        return {
            "ok": True,
            "conversation": start,
            "inbound_flow": inbound,
            "call": call,
            "status": self.status(),
        }

"""
Twilio SDK wrapper with mock mode when credentials are missing.

Trial-account notes:
- SMS only to verified numbers on trial
- Outbound may include a trial prefix from Twilio
- Conversations API requires Conversations product enabled on the account
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("connectforge.twilio")

E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def normalize_e164(number: str) -> str:
    n = (number or "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if n and not n.startswith("+") and n.isdigit() and len(n) == 10:
        n = "+1" + n  # US default for Houston SMBs
    if n and not n.startswith("+") and n.isdigit() and len(n) == 11 and n.startswith("1"):
        n = "+" + n
    return n


def is_e164(number: str) -> bool:
    return bool(E164.match(normalize_e164(number)))


class TwilioService:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        tw = cfg.get("twilio") or {}
        self.account_sid = (tw.get("account_sid") or "").strip()
        self.auth_token = (tw.get("auth_token") or "").strip()
        self.from_number = normalize_e164(tw.get("phone_number") or "")
        self.conversations_service_sid = (tw.get("conversations_service_sid") or "").strip()
        self.test_mode = bool(tw.get("test_mode", True))
        self.verified = [normalize_e164(n) for n in (tw.get("verified_numbers") or []) if n]
        self._client = None
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client

                self._client = Client(self.account_sid, self.auth_token)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to init Twilio client: %s", exc)
                self._client = None

    @property
    def configured(self) -> bool:
        return bool(self._client and self.from_number)

    def connection_status(self) -> dict[str, Any]:
        if not self.account_sid or not self.auth_token:
            return {
                "status": "mock",
                "label": "Mock (no credentials)",
                "configured": False,
                "test_mode": self.test_mode,
                "from_number": self.from_number or None,
                "verified_count": len(self.verified),
                "note": "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER to go live.",
            }
        if not self.from_number:
            return {
                "status": "disconnected",
                "label": "Missing phone number",
                "configured": False,
                "test_mode": self.test_mode,
                "note": "Set TWILIO_PHONE_NUMBER in E.164 format (+1...).",
            }
        # Trial vs live: Twilio does not always expose a simple flag; use test_mode as operator intent
        status = "trial" if self.test_mode else "live"
        return {
            "status": status,
            "label": "Trial / Test Mode" if self.test_mode else "Live",
            "configured": True,
            "test_mode": self.test_mode,
            "from_number": self.from_number,
            "verified_count": len(self.verified),
            "conversations_service_sid": self.conversations_service_sid or None,
            "note": (
                "Test Mode: outbound only to verified numbers (Twilio trial safe)."
                if self.test_mode
                else "Live mode: ensure compliance and opt-in before mass SMS."
            ),
        }

    def assert_can_send(self, to: str) -> tuple[bool, str | None]:
        to_n = normalize_e164(to)
        if not is_e164(to_n):
            return False, f"Invalid destination number (use E.164): {to}"
        if self.test_mode:
            if not self.verified:
                return (
                    False,
                    "Test Mode is on but no verified numbers configured. "
                    "Set TWILIO_VERIFIED_NUMBERS=+1... in .env",
                )
            if to_n not in self.verified:
                return (
                    False,
                    f"Test Mode blocks {to_n}. Add it to TWILIO_VERIFIED_NUMBERS "
                    "(Twilio trial must verify the handset first).",
                )
        return True, None

    def send_sms(self, to: str, body: str) -> dict[str, Any]:
        to_n = normalize_e164(to)
        ok, err = self.assert_can_send(to_n)
        if not ok:
            return {"ok": False, "error": err, "to": to_n}

        if not self.configured:
            # Mock send for local demos without Twilio
            mock_sid = f"SM_mock_{abs(hash(to_n + body)) % 10**10}"
            logger.info("MOCK SMS to %s: %s", to_n, body[:80])
            return {
                "ok": True,
                "mocked": True,
                "sid": mock_sid,
                "to": to_n,
                "from": self.from_number or "+10000000000",
                "status": "mocked",
                "trial_note": "Mocked — credentials not configured.",
            }

        try:
            msg = self._client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_n,
            )
            trial_note = None
            # Trial accounts often prepend messaging; surface status for operators
            if self.test_mode:
                trial_note = (
                    "Trial/Test Mode: if send fails, verify the destination in Twilio Console "
                    "and ensure the body does not violate trial policies."
                )
            return {
                "ok": True,
                "mocked": False,
                "sid": msg.sid,
                "to": to_n,
                "from": self.from_number,
                "status": msg.status,
                "trial_note": trial_note,
            }
        except Exception as exc:  # noqa: BLE001
            err_s = str(exc)
            hint = ""
            low = err_s.lower()
            if "unverified" in low or "not a valid" in low or "21608" in low or "21211" in low:
                hint = (
                    " Twilio trial can only SMS verified numbers. "
                    "Verify the handset in Console → Phone Numbers → Verified Caller IDs."
                )
            if "authenticate" in low or "20003" in low:
                hint = " Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
            logger.exception("Twilio SMS failed: %s", exc)
            return {"ok": False, "error": err_s + hint, "to": to_n}

    def ensure_conversation(self, participant: str, friendly_name: str | None = None) -> dict[str, Any]:
        """Create or return a Conversations API thread for a mobile participant."""
        participant = normalize_e164(participant)
        if not self.configured:
            return {
                "ok": True,
                "mocked": True,
                "conversation_sid": f"CH_mock_{abs(hash(participant)) % 10**10}",
                "participant": participant,
            }

        try:
            # Prefer messaging binding via conversation + sms participant
            conv = self._client.conversations.v1.conversations.create(
                friendly_name=friendly_name or f"Matrixly {participant}",
            )
            # Add SMS participant
            self._client.conversations.v1.conversations(conv.sid).participants.create(
                messaging_binding_address=participant,
                messaging_binding_proxy_address=self.from_number,
            )
            return {
                "ok": True,
                "mocked": False,
                "conversation_sid": conv.sid,
                "participant": participant,
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("Conversations create failed: %s", exc)
            # Fallback: still allow SMS without Conversations SID
            return {
                "ok": False,
                "error": str(exc),
                "fallback": "sms_only",
                "participant": participant,
                "note": (
                    "Conversations API may be disabled or misconfigured. "
                    "SMS can still work via Messages API."
                ),
            }

    def post_conversation_message(self, conversation_sid: str, body: str, author: str = "system") -> dict[str, Any]:
        if conversation_sid.startswith("CH_mock_") or not self.configured:
            return {"ok": True, "mocked": True, "sid": f"IM_mock_{abs(hash(body)) % 10**8}"}
        try:
            m = self._client.conversations.v1.conversations(conversation_sid).messages.create(
                author=author,
                body=body,
            )
            return {"ok": True, "sid": m.sid, "mocked": False}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Conversation message failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def start_voice_call(self, to: str, say_text: str, status_callback: str | None = None) -> dict[str, Any]:
        """Basic outbound call with TwiML Say (Conversation Relay stub later)."""
        to_n = normalize_e164(to)
        ok, err = self.assert_can_send(to_n)
        if not ok:
            return {"ok": False, "error": err, "to": to_n}

        if not self.configured:
            return {
                "ok": True,
                "mocked": True,
                "sid": f"CA_mock_{abs(hash(to_n)) % 10**10}",
                "to": to_n,
                "status": "mocked",
                "note": "Mock call — configure Twilio credentials for live dial.",
            }

        # Escape XML special chars in say text
        safe = (
            say_text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="Polly.Joanna">{safe}</Say><Pause length="1"/><Hangup/></Response>'

        try:
            kwargs: dict[str, Any] = {
                "to": to_n,
                "from_": self.from_number,
                "twiml": twiml,
            }
            if status_callback:
                kwargs["status_callback"] = status_callback
            call = self._client.calls.create(**kwargs)
            return {
                "ok": True,
                "mocked": False,
                "sid": call.sid,
                "to": to_n,
                "status": call.status,
                "note": "Basic Say call. Expand to Conversation Relay for full duplex AI voice.",
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("Voice call failed: %s", exc)
            err_s = str(exc)
            if "unverified" in err_s.lower():
                err_s += " Verify the destination number on your Twilio trial account."
            return {"ok": False, "error": err_s, "to": to_n}

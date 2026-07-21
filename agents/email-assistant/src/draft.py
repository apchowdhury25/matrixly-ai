"""Draft reply generation (always creates Gmail drafts — never auto-sends)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .llm import chat, grok_available
from .models import EmailMessage


class SupportsDraft(Protocol):
    def get_message(self, message_id: str, format: str = "full") -> EmailMessage: ...

    def create_draft_reply(
        self,
        original: EmailMessage,
        body_text: str,
        reply_all: bool = False,
    ) -> dict: ...


@dataclass
class DraftResult:
    message_id: str
    subject: str
    to: str
    body: str
    draft_id: str | None
    mode: str  # llm | template


def _template_reply(msg: EmailMessage, cfg: dict[str, Any]) -> str:
    draft_cfg = cfg.get("draft") or {}
    signature = (draft_cfg.get("signature") or "").strip()
    first = (msg.from_name or msg.from_email or "there").split()[0]
    body = (
        f"Hi {first},\n\n"
        f"Thanks for your email regarding \"{msg.subject}\". "
        f"I've received it and will follow up with a full response shortly.\n\n"
        f"If anything is time-sensitive, reply to this note and I'll prioritize it.\n\n"
        f"Best regards"
    )
    if signature:
        body = f"{body}\n{signature}"
    return body


def _llm_reply(msg: EmailMessage, cfg: dict[str, Any]) -> str:
    draft_cfg = cfg.get("draft") or {}
    signature = (draft_cfg.get("signature") or "").strip()
    max_words = int(draft_cfg.get("max_words") or 180)
    tone = draft_cfg.get("tone") or "professional"

    system = (
        "You are the Email Assistant for Anwar Chowdhury, CEO of Matrix Bazaar / Matrixly.AI "
        "(domains: matrixbazaar.com, usmatrixbazaar.com). "
        f"Write a {tone} email reply draft. "
        f"Keep it under ~{max_words} words. "
        "Do not invent facts, prices, or commitments. "
        "If info is missing, ask a clear clarifying question. "
        "Do NOT include a subject line. "
        "Do NOT wrap the reply in quotes or markdown fences. "
        "Write only the email body."
    )
    user = (
        f"From: {msg.from_raw}\n"
        f"Subject: {msg.subject}\n"
        f"Date: {msg.date}\n"
        f"Body:\n{msg.body[:6000] or msg.snippet}\n"
    )
    text = chat(cfg, system, user, temperature=0.35).strip()
    if signature and signature not in text:
        text = f"{text.rstrip()}\n\n{signature}"
    return text


def draft_reply(
    client: SupportsDraft,
    cfg: dict[str, Any],
    msg: EmailMessage,
    *,
    create_gmail_draft: bool = True,
    force_template: bool = False,
) -> DraftResult:
    mode = "template"
    if not force_template and grok_available(cfg):
        try:
            body = _llm_reply(msg, cfg)
            mode = "llm"
        except Exception as exc:  # noqa: BLE001
            print(f"warn: LLM draft failed, using template: {exc}")
            body = _template_reply(msg, cfg)
    else:
        body = _template_reply(msg, cfg)

    draft_id = None
    if create_gmail_draft:
        created = client.create_draft_reply(msg, body)
        draft_id = created.get("id")

    return DraftResult(
        message_id=msg.id,
        subject=msg.subject,
        to=msg.from_email,
        body=body,
        draft_id=draft_id,
        mode=mode,
    )


def draft_for_message_id(
    client: SupportsDraft,
    cfg: dict[str, Any],
    message_id: str,
    **kwargs: Any,
) -> DraftResult:
    msg = client.get_message(message_id)
    return draft_reply(client, cfg, msg, **kwargs)

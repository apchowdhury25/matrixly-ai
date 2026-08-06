"""Test Mode: sample inbox so SMBs can try Email Assistant without connecting mail."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import EmailMessage


def _sample_messages() -> list[EmailMessage]:
    """Small, realistic SMB inbox for demos (no real PII beyond fake domains)."""
    now = datetime.now(timezone.utc)

    def _msg(
        *,
        sid: str,
        subject: str,
        from_name: str,
        from_email: str,
        body: str,
        hours_ago: float,
        unread: bool = True,
        category_hint: str = "",
    ) -> EmailMessage:
        when = now - timedelta(hours=hours_ago)
        date_hdr = when.strftime("%a, %d %b %Y %H:%M:%S +0000")
        return EmailMessage(
            id=sid,
            thread_id=f"thread-{sid}",
            subject=subject,
            from_raw=f"{from_name} <{from_email}>",
            from_email=from_email.lower(),
            from_name=from_name,
            to="you@yourbusiness.com",
            date=date_hdr,
            snippet=body[:160].replace("\n", " "),
            body=body.strip(),
            label_ids=["INBOX"] + (["UNREAD"] if unread else []),
            is_unread=unread,
            message_id_header=f"<{sid}@sample.matrixly.local>",
            uid=sid,
            folder="INBOX",
        )

    return [
        _msg(
            sid="sample-urgent-ac",
            subject="URGENT: AC unit not cooling — customer waiting at home",
            from_name="Maria Lopez",
            from_email="maria.lopez@example-home.com",
            hours_ago=0.5,
            body=(
                "Hi,\n\n"
                "Our AC stopped cooling this morning and we have a baby at home. "
                "Can someone come today? This is urgent — please call me back ASAP.\n\n"
                "Address: 4421 Oak Street\nPhone: (713) 555-0142\n\nThanks,\nMaria"
            ),
            category_hint="urgent",
        ),
        _msg(
            sid="sample-quote-request",
            subject="Quote request for kitchen remodel",
            from_name="James Chen",
            from_email="james.chen@example-home.com",
            hours_ago=2,
            body=(
                "Hello,\n\n"
                "We found you online and would like a quote for a full kitchen remodel "
                "(cabinets + counters). Available next week for a walk-through.\n\n"
                "Best,\nJames"
            ),
            category_hint="needs_reply",
        ),
        _msg(
            sid="sample-invoice-past-due",
            subject="Invoice #1042 past due — action required",
            from_name="Apex Supply Co",
            from_email="billing@apex-supply.example",
            hours_ago=5,
            body=(
                "Dear Customer,\n\n"
                "Invoice #1042 for $1,280 is past due. Please remit payment by EOD "
                "or contact us to arrange a plan. Wire transfer details attached in portal.\n\n"
                "Accounts Receivable\nApex Supply"
            ),
            category_hint="urgent",
        ),
        _msg(
            sid="sample-ship-delay",
            subject="Shipment delayed — order #SS-88921",
            from_name="ShipStation Alerts",
            from_email="noreply@shipstation.example",
            hours_ago=8,
            body=(
                "Order #SS-88921 to Austin, TX is delayed (carrier exception). "
                "Customer may ask 'where is my order'. Tracking shows out for delivery tomorrow."
            ),
            category_hint="fyi",
        ),
        _msg(
            sid="sample-newsletter",
            subject="This week in small business: 5 marketing tips",
            from_name="SMB Weekly",
            from_email="digest@smb-weekly.example",
            hours_ago=12,
            body=(
                "Your weekly newsletter is here. Tip #1: Answer leads within 5 minutes...\n"
                "Unsubscribe anytime."
            ),
            category_hint="newsletter",
        ),
        _msg(
            sid="sample-review",
            subject="New 5-star Google review for your business",
            from_name="Google Business Profile",
            from_email="noreply@google.example",
            hours_ago=18,
            body=(
                "Great news! A customer left a 5-star review: "
                "\"Showed up on time and fixed our issue fast. Highly recommend.\""
            ),
            category_hint="fyi",
        ),
        _msg(
            sid="sample-meeting",
            subject="Re: Partnership intro call tomorrow?",
            from_name="Priya Patel",
            from_email="priya@partnerco.example",
            hours_ago=20,
            body=(
                "Hi — following up on our chat. Are you free tomorrow at 10am CT "
                "for a 20-minute intro call? Happy to work around your schedule.\n\nPriya"
            ),
            category_hint="needs_reply",
        ),
        _msg(
            sid="sample-automated",
            subject="Your receipt from Amazon Web Services",
            from_name="Amazon Web Services",
            from_email="no-reply@amazonaws.example",
            hours_ago=22,
            body="This is an automated receipt for your recent AWS charges. No action needed.",
            category_hint="automated",
            unread=True,
        ),
    ]


class TestMailClient:
    """In-memory mail client that implements the same surface as IMAP / Gmail."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg or {}
        self._messages = _sample_messages()
        self._labels: dict[str, str] = {}  # name -> id
        self._msg_labels: dict[str, list[str]] = {m.id: list(m.label_ids) for m in self._messages}
        self._drafts: list[dict] = []
        self._sent: list[dict] = []
        self._authed = False

    def authenticate(self) -> None:
        self._authed = True

    def profile(self) -> dict:
        self.authenticate()
        return {
            "emailAddress": "demo@yourbusiness.com",
            "messagesTotal": len(self._messages),
            "threadsTotal": len(self._messages),
            "historyId": "test-mode",
            "backend": "test",
            "imapHost": "test-mode (sample inbox)",
            "testMode": True,
        }

    def list_messages(
        self,
        query: str = "is:unread",
        max_results: int = 40,
        label_ids: list[str] | None = None,
    ) -> list[dict]:
        q = (query or "").lower()
        out: list[dict] = []
        for m in self._messages:
            labels = self._msg_labels.get(m.id, [])
            if label_ids and not any(lid in labels for lid in label_ids):
                continue
            if "is:unread" in q and "UNREAD" not in labels and not m.is_unread:
                continue
            if "in:inbox" in q or not q:
                pass
            out.append({"id": m.id, "threadId": m.thread_id})
            if len(out) >= max_results:
                break
        return out

    def get_message(self, message_id: str, format: str = "full") -> EmailMessage:
        for m in self._messages:
            if m.id == message_id:
                labels = self._msg_labels.get(m.id, m.label_ids)
                return EmailMessage(
                    id=m.id,
                    thread_id=m.thread_id,
                    subject=m.subject,
                    from_raw=m.from_raw,
                    from_email=m.from_email,
                    from_name=m.from_name,
                    to=m.to,
                    date=m.date,
                    snippet=m.snippet,
                    body=m.body,
                    label_ids=list(labels),
                    is_unread="UNREAD" in labels or m.is_unread,
                    message_id_header=m.message_id_header,
                    uid=m.uid,
                    folder=m.folder,
                )
        raise KeyError(f"Sample message not found: {message_id}")

    def fetch_inbox(
        self,
        max_results: int = 40,
        unread_only: bool = True,
        extra_query: str = "",
    ) -> list[EmailMessage]:
        q = "in:inbox"
        if unread_only:
            q = "is:unread in:inbox"
        if extra_query:
            q = f"{q} {extra_query}"
        refs = self.list_messages(query=q, max_results=max_results)
        return [self.get_message(r["id"]) for r in refs]

    def ensure_label(self, name: str) -> str:
        if name in self._labels:
            return self._labels[name]
        lid = f"LBL-{uuid.uuid4().hex[:8]}"
        self._labels[name] = lid
        return lid

    def apply_labels(
        self,
        message_id: str,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> None:
        cur = self._msg_labels.setdefault(message_id, [])
        for lid in add or []:
            if lid not in cur:
                cur.append(lid)
        for lid in remove or []:
            if lid in cur:
                cur.remove(lid)

    def create_draft_reply(
        self,
        original: EmailMessage,
        body_text: str,
        reply_all: bool = False,
    ) -> dict:
        draft_id = f"draft-{uuid.uuid4().hex[:10]}"
        self._drafts.append(
            {
                "id": draft_id,
                "to": original.from_email,
                "subject": original.subject,
                "body": body_text,
                "message_id": original.id,
            }
        )
        return {"id": draft_id, "message": {"id": original.id, "threadId": original.thread_id}}

    def send_email(self, to: str, subject: str, body_text: str) -> dict:
        mid = f"sent-{uuid.uuid4().hex[:10]}"
        self._sent.append({"id": mid, "to": to, "subject": subject, "body": body_text})
        return {"id": mid, "labelIds": ["SENT"]}

    def search(self, query: str, max_results: int = 25) -> list[EmailMessage]:
        refs = self.list_messages(query=query, max_results=max_results)
        return [self.get_message(r["id"]) for r in refs]

    def list_created_labels(self) -> list[str]:
        return sorted(self._labels.keys())

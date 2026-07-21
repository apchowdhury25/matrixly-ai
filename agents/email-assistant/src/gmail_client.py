"""Gmail API client with desktop OAuth for Matrixly Email Assistant."""

from __future__ import annotations

import base64
import re
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .models import EmailMessage


def _header(headers: list[dict], name: str) -> str:
    name_l = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_l:
            return h.get("value", "") or ""
    return ""


def _decode_body(payload: dict) -> str:
    """Extract plain-text body from a Gmail message payload."""
    if not payload:
        return ""

    mime = payload.get("mimeType", "")
    body = payload.get("body", {}) or {}
    data = body.get("data")
    if data and mime.startswith("text/plain"):
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")

    parts = payload.get("parts") or []
    # Prefer text/plain
    for part in parts:
        if part.get("mimeType", "").startswith("text/plain"):
            pdata = (part.get("body") or {}).get("data")
            if pdata:
                return base64.urlsafe_b64decode(pdata.encode("utf-8")).decode(
                    "utf-8", errors="replace"
                )
        nested = _decode_body(part)
        if nested:
            return nested

    # Fallback: any text/html stripped lightly
    if data and mime.startswith("text/html"):
        html = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", html)

    for part in parts:
        if part.get("mimeType", "").startswith("text/html"):
            pdata = (part.get("body") or {}).get("data")
            if pdata:
                html = base64.urlsafe_b64decode(pdata.encode("utf-8")).decode(
                    "utf-8", errors="replace"
                )
                return re.sub(r"<[^>]+>", " ", html)
    return ""


class GmailClient:
    def __init__(self, credentials_file: str, token_file: str, scopes: list[str], user_id: str = "me"):
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.scopes = scopes
        self.user_id = user_id
        self._service = None

    def authenticate(self) -> None:
        creds: Credentials | None = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    raise FileNotFoundError(
                        f"Missing OAuth client secrets at {self.credentials_file}.\n"
                        "Download Desktop OAuth credentials from Google Cloud Console "
                        "and save as data/credentials.json. See README.md."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), self.scopes
                )
                creds = flow.run_local_server(port=0, prompt="consent")
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")

        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    @property
    def service(self):
        if self._service is None:
            self.authenticate()
        return self._service

    def profile(self) -> dict:
        return self.service.users().getProfile(userId=self.user_id).execute()

    def list_messages(
        self,
        query: str = "is:unread",
        max_results: int = 40,
        label_ids: list[str] | None = None,
    ) -> list[dict]:
        kwargs: dict[str, Any] = {
            "userId": self.user_id,
            "q": query,
            "maxResults": max_results,
        }
        if label_ids:
            kwargs["labelIds"] = label_ids
        resp = self.service.users().messages().list(**kwargs).execute()
        return resp.get("messages", []) or []

    def get_message(self, message_id: str, format: str = "full") -> EmailMessage:
        msg = (
            self.service.users()
            .messages()
            .get(userId=self.user_id, id=message_id, format=format)
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        subject = _header(headers, "Subject")
        from_raw = _header(headers, "From")
        name, email = parseaddr(from_raw)
        to = _header(headers, "To")
        date = _header(headers, "Date")
        label_ids = msg.get("labelIds", []) or []
        body = _decode_body(msg.get("payload", {}))
        return EmailMessage(
            id=msg["id"],
            thread_id=msg.get("threadId", ""),
            subject=subject,
            from_raw=from_raw,
            from_email=email.lower(),
            from_name=name or email,
            to=to,
            date=date,
            snippet=msg.get("snippet", "") or "",
            body=body.strip(),
            label_ids=label_ids,
            is_unread="UNREAD" in label_ids,
            message_id_header=_header(headers, "Message-ID") or _header(headers, "Message-Id"),
            uid=msg["id"],
            folder="INBOX",
        )

    def fetch_inbox(
        self,
        max_results: int = 40,
        unread_only: bool = True,
        extra_query: str = "",
    ) -> list[EmailMessage]:
        parts = []
        if unread_only:
            parts.append("is:unread")
        parts.append("in:inbox")
        if extra_query:
            parts.append(extra_query)
        query = " ".join(parts)
        refs = self.list_messages(query=query, max_results=max_results)
        messages: list[EmailMessage] = []
        for ref in refs:
            try:
                messages.append(self.get_message(ref["id"]))
            except Exception as exc:  # noqa: BLE001
                print(f"warn: skip message {ref.get('id')}: {exc}")
        return messages

    def ensure_label(self, name: str) -> str:
        """Return label id, creating the label if missing."""
        existing = self.service.users().labels().list(userId=self.user_id).execute()
        for lab in existing.get("labels", []) or []:
            if lab.get("name") == name:
                return lab["id"]
        body = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        created = self.service.users().labels().create(userId=self.user_id, body=body).execute()
        return created["id"]

    def apply_labels(self, message_id: str, add: list[str] | None = None, remove: list[str] | None = None) -> None:
        body: dict[str, Any] = {}
        if add:
            body["addLabelIds"] = add
        if remove:
            body["removeLabelIds"] = remove
        if not body:
            return
        self.service.users().messages().modify(
            userId=self.user_id, id=message_id, body=body
        ).execute()

    def create_draft_reply(
        self,
        original: EmailMessage,
        body_text: str,
        reply_all: bool = False,
    ) -> dict:
        """Create a draft reply in the same thread (does not send)."""
        subject = original.subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        to_addr = original.from_email
        mime = MIMEText(body_text, _charset="utf-8")
        mime["To"] = to_addr
        mime["Subject"] = subject
        mime["In-Reply-To"] = original.id
        mime["References"] = original.id

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
        draft_body = {
            "message": {
                "raw": raw,
                "threadId": original.thread_id,
            }
        }
        return (
            self.service.users()
            .drafts()
            .create(userId=self.user_id, body=draft_body)
            .execute()
        )

    def send_email(self, to: str, subject: str, body_text: str) -> dict:
        mime = MIMEText(body_text, _charset="utf-8")
        mime["To"] = to
        mime["Subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
        return (
            self.service.users()
            .messages()
            .send(userId=self.user_id, body={"raw": raw})
            .execute()
        )

    def search(self, query: str, max_results: int = 25) -> list[EmailMessage]:
        refs = self.list_messages(query=query, max_results=max_results)
        return [self.get_message(r["id"]) for r in refs]

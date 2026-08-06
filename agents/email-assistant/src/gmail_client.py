"""Gmail API client with desktop OAuth for Matrixly Email Assistant."""

from __future__ import annotations

import base64
import re
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import EmailMessage

# Canonical scopes for SMB Email Assistant (HITL drafts + labels + self-brief send)
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]


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


class GmailAuthError(RuntimeError):
    """User-facing OAuth / token errors (deny, expired, missing scopes)."""


class GmailClient:
    def __init__(
        self,
        credentials_file: str,
        token_file: str,
        scopes: list[str] | None = None,
        user_id: str = "me",
    ):
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.scopes = list(scopes or DEFAULT_SCOPES)
        self.user_id = user_id
        self._service = None
        self._creds: Credentials | None = None

    def authenticate(self, *, force: bool = False) -> None:
        """Desktop OAuth with token refresh. Never logs secrets."""
        if force and self.token_file.exists():
            try:
                self.token_file.unlink()
            except OSError:
                pass
            self._service = None
            self._creds = None

        creds: Credentials | None = None
        if self.token_file.exists() and not force:
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)
            except Exception as exc:  # noqa: BLE001
                raise GmailAuthError(
                    f"Could not read saved login at {self.token_file}: {exc}\n"
                    "Fix: delete data/token.json and run: python -m src.cli connect-gmail"
                ) from exc

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError as exc:
                    raise GmailAuthError(
                        "Your Google login expired or was revoked.\n"
                        "Fix: run  python -m src.cli connect-gmail --force\n"
                        "Then approve access again in the browser.\n"
                        f"Details: {exc}"
                    ) from exc
            else:
                if not self.credentials_file.exists():
                    raise FileNotFoundError(
                        f"Missing Google app credentials at:\n  {self.credentials_file}\n\n"
                        "For small business setup (about 5 minutes):\n"
                        "  1. Open scripts/setup_oauth.md and create a Desktop OAuth client\n"
                        "  2. Download the JSON and save it as data/credentials.json\n"
                        "  3. Run: python -m src.cli connect-gmail\n\n"
                        "Your emails stay in your Google account. We never train on them."
                    )
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), self.scopes
                    )
                    # port=0 = pick free port; prompt=consent ensures refresh_token on re-auth
                    creds = flow.run_local_server(
                        port=0,
                        prompt="consent",
                        authorization_prompt_message=(
                            "\nOpening your browser to connect Gmail…\n"
                            "Sign in with the Google account you use for business email.\n"
                            "If the browser does not open, copy the URL shown below.\n"
                        ),
                        success_message=(
                            "Gmail connected to Matrixly Email Assistant. "
                            "You can close this tab and return to the terminal."
                        ),
                    )
                except Exception as exc:  # noqa: BLE001
                    msg = str(exc).lower()
                    if "access_denied" in msg or "denied" in msg or "consent" in msg:
                        raise GmailAuthError(
                            "You declined Google access — no problem.\n"
                            "Nothing was connected. When you are ready:\n"
                            "  python -m src.cli connect-gmail\n"
                            "Or try sample emails first (no Gmail needed):\n"
                            "  python -m src.cli test-mode"
                        ) from exc
                    raise GmailAuthError(
                        f"Could not complete Google sign-in: {exc}\n"
                        "See scripts/test_oauth.md for troubleshooting."
                    ) from exc

            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            # Restrictive permissions where supported (best-effort on Windows)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
            try:
                self.token_file.chmod(0o600)
            except OSError:
                pass

        self._creds = creds
        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    def token_status(self) -> dict[str, Any]:
        """Non-secret status for verification / debugging."""
        status: dict[str, Any] = {
            "credentials_file_exists": self.credentials_file.exists(),
            "token_file_exists": self.token_file.exists(),
            "token_path": str(self.token_file),
            "scopes_configured": list(self.scopes),
        }
        if not self.token_file.exists():
            status["valid"] = False
            status["message"] = "No token yet — run connect-gmail"
            return status
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)
            status["valid"] = bool(creds and creds.valid)
            status["expired"] = bool(creds.expired) if creds else None
            status["has_refresh_token"] = bool(creds and creds.refresh_token)
            status["scopes_granted"] = list(creds.scopes or []) if creds else []
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.token_file.write_text(creds.to_json(), encoding="utf-8")
                    status["valid"] = True
                    status["refreshed_now"] = True
                except RefreshError as exc:
                    status["valid"] = False
                    status["refresh_error"] = str(exc)
            missing = [s for s in self.scopes if s not in (creds.scopes or [])]
            # Google sometimes returns broader scopes; only flag hard misses when scopes present
            if creds and creds.scopes:
                status["missing_scopes"] = missing
        except Exception as exc:  # noqa: BLE001
            status["valid"] = False
            status["error"] = str(exc)
        return status

    @property
    def service(self):
        if self._service is None:
            self.authenticate()
        return self._service

    def profile(self) -> dict:
        try:
            prof = self.service.users().getProfile(userId=self.user_id).execute()
        except HttpError as exc:
            self._raise_http(exc, action="read mailbox profile")
        prof["backend"] = "gmail"
        prof["imapHost"] = "gmail-api"
        return prof

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
        try:
            resp = self.service.users().messages().list(**kwargs).execute()
        except HttpError as exc:
            self._raise_http(exc, action="list messages")
        return resp.get("messages", []) or []

    def get_message(self, message_id: str, format: str = "full") -> EmailMessage:
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId=self.user_id, id=message_id, format=format)
                .execute()
            )
        except HttpError as exc:
            self._raise_http(exc, action=f"get message {message_id}")
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
        """Return label id, creating the label if missing (Matrixly/* tree)."""
        try:
            existing = self.service.users().labels().list(userId=self.user_id).execute()
        except HttpError as exc:
            self._raise_http(exc, action="list labels")
        for lab in existing.get("labels", []) or []:
            if lab.get("name") == name:
                return lab["id"]
        body = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        try:
            created = (
                self.service.users().labels().create(userId=self.user_id, body=body).execute()
            )
        except HttpError as exc:
            # Race: label created between list and create
            if exc.resp is not None and exc.resp.status == 409:
                existing = self.service.users().labels().list(userId=self.user_id).execute()
                for lab in existing.get("labels", []) or []:
                    if lab.get("name") == name:
                        return lab["id"]
            self._raise_http(exc, action=f"create label {name}")
        return created["id"]

    def ensure_matrixly_labels(self, label_names: dict[str, str] | list[str]) -> dict[str, str]:
        """Create all Matrixly/* labels; return name -> id map."""
        if isinstance(label_names, dict):
            names = list(label_names.values())
        else:
            names = list(label_names)
        out: dict[str, str] = {}
        for name in names:
            out[name] = self.ensure_label(name)
        return out

    def apply_labels(
        self,
        message_id: str,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> None:
        body: dict[str, Any] = {}
        if add:
            body["addLabelIds"] = add
        if remove:
            body["removeLabelIds"] = remove
        if not body:
            return
        try:
            self.service.users().messages().modify(
                userId=self.user_id, id=message_id, body=body
            ).execute()
        except HttpError as exc:
            self._raise_http(exc, action="apply labels")

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
        # Prefer RFC Message-ID for proper threading
        ref = original.message_id_header or original.id
        mime["In-Reply-To"] = ref
        mime["References"] = ref

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
        draft_body = {
            "message": {
                "raw": raw,
                "threadId": original.thread_id,
            }
        }
        try:
            return (
                self.service.users()
                .drafts()
                .create(userId=self.user_id, body=draft_body)
                .execute()
            )
        except HttpError as exc:
            self._raise_http(exc, action="create draft (never auto-sends)")

    def send_email(self, to: str, subject: str, body_text: str) -> dict:
        """Send mail — used only for self-addressed daily brief, not customer replies."""
        mime = MIMEText(body_text, _charset="utf-8")
        mime["To"] = to
        mime["Subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
        try:
            return (
                self.service.users()
                .messages()
                .send(userId=self.user_id, body={"raw": raw})
                .execute()
            )
        except HttpError as exc:
            self._raise_http(exc, action="send email")

    def search(self, query: str, max_results: int = 25) -> list[EmailMessage]:
        refs = self.list_messages(query=query, max_results=max_results)
        return [self.get_message(r["id"]) for r in refs]

    def _raise_http(self, exc: HttpError, *, action: str) -> None:
        status = getattr(exc.resp, "status", None) if exc.resp is not None else None
        content = ""
        try:
            content = (exc.content or b"").decode("utf-8", errors="replace")[:400]
        except Exception:  # noqa: BLE001
            content = str(exc)
        if status in {401, 403}:
            raise GmailAuthError(
                f"Google blocked this action ({action}). Status {status}.\n"
                "Usually means: login expired, access revoked, or missing permissions.\n"
                "Fix:\n"
                "  1. python -m src.cli connect-gmail --force\n"
                "  2. Approve all requested permissions on the consent screen\n"
                "  3. Or revoke the app at https://myaccount.google.com/permissions then reconnect\n"
                f"Details: {content}"
            ) from exc
        raise RuntimeError(f"Gmail API error while trying to {action}: {content or exc}") from exc

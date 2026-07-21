"""IMAP/SMTP mail client for Hostinger / Thunderbird mailboxes."""

from __future__ import annotations

import email
import imaplib
import re
import smtplib
import ssl
import uuid
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.message import EmailMessage as MimeEmailMessage
from email.utils import formatdate, make_msgid, parseaddr, parsedate_to_datetime
from typing import Any

from .models import EmailMessage


def _decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001
        return value


def _body_from_message(msg: email.message.Message) -> str:
    if msg.is_multipart():
        plain = ""
        html = ""
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp.lower():
                continue
            try:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
            except Exception:  # noqa: BLE001
                continue
            if ctype == "text/plain" and not plain:
                plain = text
            elif ctype == "text/html" and not html:
                html = text
        if plain:
            return plain.strip()
        if html:
            return re.sub(r"<[^>]+>", " ", html).strip()
        return ""
    try:
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if msg.get_content_type() == "text/html":
            return re.sub(r"<[^>]+>", " ", text).strip()
        return text.strip()
    except Exception:  # noqa: BLE001
        return ""


class ImapMailClient:
    """Thunderbird-compatible IMAP + SMTP client (Hostinger defaults)."""

    def __init__(self, cfg: dict[str, Any]):
        account = cfg.get("account") or {}
        imap = cfg.get("imap") or {}
        smtp = cfg.get("smtp") or {}

        self.email_address = (
            imap.get("username")
            or account.get("primary_email")
            or ""
        ).strip()
        self.password = (imap.get("password") or "").strip()
        self.imap_host = imap.get("host") or "imap.hostinger.com"
        self.imap_port = int(imap.get("port") or 993)
        self.smtp_host = smtp.get("host") or "smtp.hostinger.com"
        self.smtp_port = int(smtp.get("port") or 465)
        self.inbox = imap.get("inbox") or "INBOX"
        self.drafts_folder = imap.get("drafts_folder") or "INBOX/Drafts"
        self.sent_folder = imap.get("sent_folder") or "INBOX/Sent"
        self.max_results = int(imap.get("max_results") or (cfg.get("gmail") or {}).get("max_results") or 40)
        self._conn: imaplib.IMAP4_SSL | None = None
        self._label_folders: dict[str, str] = {}

    def authenticate(self) -> None:
        placeholder = {
            "",
            "your-mailbox-password-here",
            "your-gmail-app-password-here",
            "********",
            "changeme",
        }
        if not self.email_address or not self.password or self.password.strip().lower() in placeholder:
            is_gmail = "gmail.com" in self.imap_host or "gmail.com" in self.email_address
            if is_gmail:
                raise RuntimeError(
                    "Gmail IMAP credentials missing. In agents/email-assistant/.env set:\n"
                    "  EMAIL_PROFILE=gmail\n"
                    "  EMAIL_GMAIL_USER=usmatrixbazaar@gmail.com\n"
                    "  EMAIL_GMAIL_PASSWORD=<Google App Password>\n"
                    "Create an App Password at https://myaccount.google.com/apppasswords "
                    "(2-Step Verification must be on). Do not paste the password into chat."
                )
            raise RuntimeError(
                "IMAP credentials missing. Set EMAIL_HOSTINGER_PASSWORD or EMAIL_IMAP_PASSWORD "
                "in agents/email-assistant/.env (see .env.example). "
                "Do not paste the password into chat."
            )
        if self._conn is not None:
            try:
                self._conn.noop()
                return
            except Exception:  # noqa: BLE001
                self._conn = None

        ctx = ssl.create_default_context()
        self._conn = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=ctx)
        self._conn.login(self.email_address, self.password)

    @property
    def conn(self) -> imaplib.IMAP4_SSL:
        if self._conn is None:
            self.authenticate()
        assert self._conn is not None
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.logout()
            except Exception:  # noqa: BLE001
                pass
            self._conn = None

    def profile(self) -> dict:
        self.authenticate()
        typ, data = self.conn.select(self.inbox, readonly=True)
        count = 0
        if typ == "OK" and data and data[0]:
            try:
                count = int(data[0])
            except ValueError:
                count = 0
        return {
            "emailAddress": self.email_address,
            "backend": "imap",
            "imapHost": self.imap_host,
            "messagesTotal": count,
            "inbox": self.inbox,
        }

    def _select(self, folder: str, readonly: bool = True) -> None:
        # Try common Hostinger/Thunderbird folder name variants
        candidates = [folder]
        if "/" in folder:
            candidates.append(folder.replace("/", "."))
        if folder.startswith("INBOX/") or folder.startswith("INBOX."):
            pass
        elif folder != "INBOX":
            candidates.extend([f"INBOX/{folder}", f"INBOX.{folder}"])

        last_err = None
        for name in candidates:
            typ, _ = self.conn.select(f'"{name}"' if " " in name else name, readonly=readonly)
            if typ == "OK":
                return
            last_err = name
        # bare select without quotes
        for name in candidates:
            typ, _ = self.conn.select(name, readonly=readonly)
            if typ == "OK":
                return
        raise RuntimeError(f"Could not select IMAP folder {folder!r} (last tried {last_err})")

    def _parse_fetch(self, uid: str, raw: bytes, folder: str) -> EmailMessage:
        msg = email.message_from_bytes(raw)
        subject = _decode_mime_header(msg.get("Subject"))
        from_raw = _decode_mime_header(msg.get("From"))
        name, addr = parseaddr(from_raw)
        to = _decode_mime_header(msg.get("To"))
        date = msg.get("Date") or ""
        mid = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
        body = _body_from_message(msg)
        snippet = re.sub(r"\s+", " ", body)[:180].strip()

        # flags via separate call if needed — default unread unknown
        is_unread = True
        labels: list[str] = [folder]

        return EmailMessage(
            id=f"{folder}:{uid}",
            thread_id=mid or f"{folder}:{uid}",
            subject=subject,
            from_raw=from_raw,
            from_email=(addr or "").lower(),
            from_name=name or addr or "",
            to=to,
            date=date,
            snippet=snippet,
            body=body,
            label_ids=labels,
            is_unread=is_unread,
            message_id_header=mid,
            uid=str(uid),
            folder=folder,
        )

    def _search_uids(self, folder: str, criteria: list[str]) -> list[str]:
        self._select(folder, readonly=True)
        typ, data = self.conn.uid("search", None, *criteria)
        if typ != "OK" or not data or not data[0]:
            return []
        return [u.decode() if isinstance(u, bytes) else str(u) for u in data[0].split()]

    def _fetch_uid(self, folder: str, uid: str) -> EmailMessage:
        self._select(folder, readonly=True)
        typ, data = self.conn.uid("fetch", uid, "(RFC822 FLAGS)")
        if typ != "OK" or not data:
            raise RuntimeError(f"Failed to fetch UID {uid} in {folder}")

        raw = None
        flags = ""
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2:
                meta = item[0].decode(errors="replace") if isinstance(item[0], bytes) else str(item[0])
                flags = meta
                raw = item[1]
                break
        if raw is None:
            raise RuntimeError(f"Empty body for UID {uid}")

        parsed = self._parse_fetch(uid, raw, folder)
        flags_u = flags.upper()
        parsed.is_unread = "\\SEEN" not in flags_u
        if "\\FLAGGED" in flags_u:
            parsed.label_ids.append("FLAGGED")
        return parsed

    def list_messages(
        self,
        query: str = "is:unread",
        max_results: int = 40,
        label_ids: list[str] | None = None,
    ) -> list[dict]:
        """Approximate Gmail-style queries for summary/triage compatibility."""
        folder = self.inbox
        criteria = ["ALL"]
        q = (query or "").lower()
        if "is:unread" in q:
            criteria = ["UNSEEN"]
        if "newer_than:" in q:
            m = re.search(r"newer_than:(\d+)d", q)
            days = int(m.group(1)) if m else 1
            since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
            if criteria == ["UNSEEN"]:
                criteria = ["UNSEEN", "SINCE", since]
            else:
                criteria = ["SINCE", since]

        uids = self._search_uids(folder, criteria)
        uids = uids[-max_results:]  # most recent typically last
        uids = list(reversed(uids))
        return [{"id": f"{folder}:{uid}", "threadId": f"{folder}:{uid}"} for uid in uids[:max_results]]

    def get_message(self, message_id: str, format: str = "full") -> EmailMessage:  # noqa: A002
        folder, uid = self._split_id(message_id)
        return self._fetch_uid(folder, uid)

    def _split_id(self, message_id: str) -> tuple[str, str]:
        if ":" in message_id:
            folder, uid = message_id.rsplit(":", 1)
            return folder, uid
        return self.inbox, message_id

    def fetch_inbox(
        self,
        max_results: int = 40,
        unread_only: bool = True,
        extra_query: str = "",
    ) -> list[EmailMessage]:
        criteria = ["UNSEEN"] if unread_only else ["ALL"]
        if extra_query:
            # support newer_than:Nd
            m = re.search(r"newer_than:(\d+)d", extra_query, re.I)
            if m:
                since = (datetime.now(timezone.utc) - timedelta(days=int(m.group(1)))).strftime("%d-%b-%Y")
                if unread_only:
                    criteria = ["UNSEEN", "SINCE", since]
                else:
                    criteria = ["SINCE", since]

        uids = self._search_uids(self.inbox, criteria)
        uids = list(reversed(uids))[:max_results]
        messages: list[EmailMessage] = []
        for uid in uids:
            try:
                messages.append(self._fetch_uid(self.inbox, uid))
            except Exception as exc:  # noqa: BLE001
                print(f"warn: skip uid {uid}: {exc}")
        return messages

    def ensure_label(self, name: str) -> str:
        """Create IMAP folder for label; return folder path used as label id."""
        if name in self._label_folders:
            return self._label_folders[name]

        # Prefer INBOX.Matrixly.Urgent style for Hostinger/Dovecot
        safe = name.replace("/", ".")
        if not safe.upper().startswith("INBOX"):
            folder = f"INBOX.{safe}"
        else:
            folder = safe

        # LIST and CREATE if missing
        typ, data = self.conn.list()
        existing = set()
        if typ == "OK" and data:
            for line in data:
                if not line:
                    continue
                s = line.decode(errors="replace") if isinstance(line, bytes) else str(line)
                # last quoted token is folder name
                m = re.search(r'"([^"]+)"\s*$', s)
                if m:
                    existing.add(m.group(1))
                else:
                    parts = s.split()
                    if parts:
                        existing.add(parts[-1].strip('"'))

        if folder not in existing and folder.replace(".", "/") not in existing:
            # try create
            for candidate in (folder, folder.replace(".", "/"), safe):
                typ, _ = self.conn.create(candidate)
                if typ == "OK":
                    folder = candidate
                    break
            else:
                # folder may already exist under alternate name — keep intended path
                pass

        self._label_folders[name] = folder
        return folder

    def apply_labels(
        self,
        message_id: str,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> None:
        """Copy message into label folders; flag urgent with \\Flagged."""
        folder, uid = self._split_id(message_id)
        self._select(folder, readonly=False)

        for lab in add or []:
            # lab may already be folder path from ensure_label
            dest = lab
            try:
                self.conn.uid("copy", uid, dest)
            except Exception:  # noqa: BLE001
                try:
                    self.conn.uid("copy", uid, dest.replace(".", "/"))
                except Exception as exc:  # noqa: BLE001
                    print(f"warn: could not copy to label folder {dest}: {exc}")

            # Flag messages going to Urgent folders
            if "urgent" in dest.lower():
                try:
                    self.conn.uid("store", uid, "+FLAGS", "(\\Flagged)")
                except Exception:  # noqa: BLE001
                    pass

        # remove not strongly supported without moving; no-op for IMAP MVP

    def _folder_candidates(self, folder: str) -> list[str]:
        """Hostinger/Dovecot and Gmail folder name variants."""
        variants = [
            folder,
            folder.replace("/", "."),
            folder.replace(".", "/"),
        ]
        # Gmail special-use folders
        if "draft" in folder.lower():
            variants.extend(
                [
                    "[Gmail]/Drafts",
                    '"[Gmail]/Drafts"',
                    "INBOX.Drafts",
                    "INBOX/Drafts",
                    "Drafts",
                ]
            )
        if "sent" in folder.lower():
            variants.extend(
                [
                    "[Gmail]/Sent Mail",
                    '"[Gmail]/Sent Mail"',
                    "[Gmail]/Sent Mail",
                    "INBOX.Sent",
                    "INBOX/Sent",
                    "Sent",
                    "Sent Items",
                ]
            )
        if folder.upper() in {"DRAFTS", "INBOX/DRAFTS", "INBOX.DRAFTS"}:
            variants.extend(["INBOX.Drafts", "INBOX/Drafts", "Drafts", "[Gmail]/Drafts"])
        if folder.upper() in {"SENT", "INBOX/SENT", "INBOX.SENT"}:
            variants.extend(["INBOX.Sent", "INBOX/Sent", "Sent", "[Gmail]/Sent Mail"])
        # de-dupe preserve order
        seen: set[str] = set()
        out: list[str] = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                out.append(v)
        return out

    def _resolve_folder(self, folder: str, readonly: bool = True) -> str:
        last_err: Exception | None = None
        for name in self._folder_candidates(folder):
            bare = name.strip('"')
            try:
                # Gmail folders with spaces/brackets need quoting
                needs_quote = any(c in bare for c in (" ", "[", "]", "/"))
                candidates = [f'"{bare}"', bare] if needs_quote else [bare, f'"{bare}"']
                for sel in candidates:
                    typ, _ = self.conn.select(sel, readonly=readonly)
                    if typ == "OK":
                        return bare
            except Exception as exc:  # noqa: BLE001
                last_err = exc
        raise RuntimeError(f"Could not select IMAP folder {folder!r}: {last_err}")

    def create_draft_reply(
        self,
        original: EmailMessage,
        body_text: str,
        reply_all: bool = False,
    ) -> dict:
        subject = original.subject or ""
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        mime = MimeEmailMessage()
        mime["From"] = self.email_address
        mime["To"] = original.from_email
        mime["Subject"] = subject
        mime["Date"] = formatdate(localtime=True)
        mime["Message-ID"] = make_msgid(domain=self.email_address.split("@")[-1])
        if original.message_id_header:
            mime["In-Reply-To"] = original.message_id_header
            mime["References"] = original.message_id_header
        mime.set_content(body_text)

        raw = mime.as_bytes()
        draft_folder = self._ensure_folder(self.drafts_folder)

        # APPEND needs mailbox name; try flags variants for Dovecot
        last = None
        for flags in ("\\Draft", "(\\Draft)", None):
            try:
                typ, data = self.conn.append(draft_folder, flags, None, raw)
                if typ == "OK":
                    draft_id = None
                    if data and data[0]:
                        draft_id = data[0].decode() if isinstance(data[0], bytes) else str(data[0])
                    else:
                        draft_id = f"draft-{uuid.uuid4().hex[:10]}"
                    return {
                        "id": draft_id,
                        "folder": draft_folder,
                        "message": {"threadId": original.thread_id, "subject": subject},
                    }
                last = (typ, data)
            except Exception as exc:  # noqa: BLE001
                last = exc
        raise RuntimeError(f"Failed to append draft to {draft_folder}: {last}")

    def _ensure_folder(self, folder: str) -> str:
        """Return a selectable folder name, creating it if needed."""
        try:
            return self._resolve_folder(folder, readonly=True)
        except Exception:  # noqa: BLE001
            pass
        for candidate in self._folder_candidates(folder):
            typ, _ = self.conn.create(candidate)
            if typ == "OK":
                try:
                    return self._resolve_folder(candidate, readonly=True)
                except Exception:  # noqa: BLE001
                    return candidate
        # Last resort: return dotted form Hostinger expects
        return folder.replace("/", ".")

    def send_email(self, to: str, subject: str, body_text: str) -> dict:
        mime = MimeEmailMessage()
        mime["From"] = self.email_address
        mime["To"] = to
        mime["Subject"] = subject
        mime["Date"] = formatdate(localtime=True)
        mime["Message-ID"] = make_msgid(domain=self.email_address.split("@")[-1])
        mime.set_content(body_text)

        context = ssl.create_default_context()
        if self.smtp_port == 465:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as smtp:
                smtp.login(self.email_address, self.password)
                smtp.send_message(mime)
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.login(self.email_address, self.password)
                smtp.send_message(mime)

        # Optional: copy to Sent
        try:
            self._ensure_folder(self.sent_folder)
            self.conn.append(self.sent_folder, "\\Seen", None, mime.as_bytes())
        except Exception:  # noqa: BLE001
            pass

        return {"id": mime["Message-ID"], "to": to, "subject": subject}

    def search(self, query: str, max_results: int = 25) -> list[EmailMessage]:
        refs = self.list_messages(query=query, max_results=max_results)
        return [self.get_message(r["id"]) for r in refs]

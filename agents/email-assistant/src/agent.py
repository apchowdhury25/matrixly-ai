"""High-level Email Assistant agent facade."""

from __future__ import annotations

from typing import Any

from .config import load_config
from .draft import DraftResult, draft_for_message_id, draft_reply
from .mail_factory import MailClient, create_mail_client
from .models import EmailMessage
from .summary import build_daily_summary, deliver_summary
from .triage import TriageItem, items_as_jsonable, triage_inbox, triage_report


class EmailAssistant:
    """Matrixly Email Assistant for Hostinger IMAP (Thunderbird) or Gmail API."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg or load_config()
        self.client: MailClient = create_mail_client(self.cfg)

    def connect(self) -> dict:
        self.client.authenticate()
        return self.client.profile()

    def triage(
        self,
        *,
        apply_labels: bool = True,
        max_results: int | None = None,
        use_llm: bool = True,
    ) -> list[TriageItem]:
        return triage_inbox(
            self.client,
            self.cfg,
            apply_labels=apply_labels,
            max_results=max_results,
            use_llm=use_llm,
        )

    def triage_text(self, **kwargs: Any) -> str:
        return triage_report(self.triage(**kwargs))

    def flag_urgent(self, **kwargs: Any) -> list[TriageItem]:
        items = self.triage(**kwargs)
        return [i for i in items if i.is_urgent or i.category == "urgent"]

    def draft(
        self,
        message_id: str,
        *,
        create_gmail_draft: bool = True,
        force_template: bool = False,
    ) -> DraftResult:
        return draft_for_message_id(
            self.client,
            self.cfg,
            message_id,
            create_gmail_draft=create_gmail_draft,
            force_template=force_template,
        )

    def draft_for(self, msg: EmailMessage, **kwargs: Any) -> DraftResult:
        return draft_reply(self.client, self.cfg, msg, **kwargs)

    def daily_summary(
        self,
        *,
        deliver: bool = True,
        apply_labels: bool = True,
        use_llm: bool = True,
    ) -> dict[str, Any]:
        text = build_daily_summary(
            self.client,
            self.cfg,
            apply_labels=apply_labels,
            use_llm=use_llm,
        )
        meta = deliver_summary(
            self.client,
            self.cfg,
            text,
            send_email=deliver,
        )
        meta["summary"] = text
        return meta

    def run(self, action: str, **kwargs: Any) -> Any:
        action = (action or "").lower().strip()
        if action in {"triage", "inbox"}:
            items = self.triage(**kwargs)
            return {"report": triage_report(items), "items": items_as_jsonable(items)}
        if action in {"urgent", "flag", "flag_urgent"}:
            items = self.flag_urgent(**kwargs)
            return {"report": triage_report(items), "items": items_as_jsonable(items)}
        if action in {"draft", "reply"}:
            mid = kwargs.get("message_id") or kwargs.get("id")
            if not mid:
                raise ValueError("message_id required for draft")
            d = self.draft(mid, create_gmail_draft=kwargs.get("create_gmail_draft", True))
            return {
                "message_id": d.message_id,
                "to": d.to,
                "subject": d.subject,
                "body": d.body,
                "draft_id": d.draft_id,
                "mode": d.mode,
            }
        if action in {"summary", "daily", "brief"}:
            return self.daily_summary(
                deliver=kwargs.get("deliver", True),
                apply_labels=kwargs.get("apply_labels", True),
                use_llm=kwargs.get("use_llm", True),
            )
        if action in {"profile", "whoami", "auth"}:
            return self.connect()
        raise ValueError(
            f"Unknown action '{action}'. Use: triage | urgent | draft | summary | profile"
        )

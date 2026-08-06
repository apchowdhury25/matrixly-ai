"""High-level Email Assistant agent facade."""

from __future__ import annotations

from typing import Any

from .config import load_config
from .draft import DraftResult, draft_for_message_id, draft_reply
from .gmail_client import GmailClient
from .impact import build_impact_report, write_impact_report
from .mail_factory import MailClient, create_mail_client
from .models import EmailMessage
from .summary import build_daily_summary, deliver_summary
from .test_mode import TestMailClient
from .triage import TriageItem, items_as_jsonable, triage_inbox, triage_report


class EmailAssistant:
    """Matrixly Email Assistant for Gmail API, Hostinger IMAP, or Test Mode."""

    def __init__(
        self,
        cfg: dict[str, Any] | None = None,
        *,
        test_mode: bool = False,
    ):
        self.cfg = cfg or load_config()
        if test_mode:
            self.cfg.setdefault("agent", {})["backend"] = "test"
        force_test = test_mode or self._is_test_backend()
        self.client: MailClient = create_mail_client(self.cfg, force_test=force_test)
        self._test_mode = isinstance(self.client, TestMailClient)

    def _is_test_backend(self) -> bool:
        be = ((self.cfg.get("agent") or {}).get("backend") or "").lower()
        return be in {"test", "demo", "sample", "test_mode"}

    @property
    def test_mode(self) -> bool:
        return self._test_mode

    def connect(self, *, force: bool = False) -> dict:
        if isinstance(self.client, GmailClient):
            self.client.authenticate(force=force)
        else:
            self.client.authenticate()
        profile = self.client.profile()
        # Ensure Matrixly labels exist early (Gmail + test); IMAP creates on triage
        labels = (self.cfg.get("triage") or {}).get("labels") or {}
        if labels and hasattr(self.client, "ensure_label"):
            for name in labels.values():
                try:
                    self.client.ensure_label(name)
                except Exception:  # noqa: BLE001
                    pass
        return profile

    def connect_gmail(self, *, force: bool = False) -> dict:
        """Force Gmail API backend and run OAuth."""
        self.cfg.setdefault("agent", {})["backend"] = "gmail"
        self.cfg["agent"]["profile"] = "gmail"
        self.client = create_mail_client(self.cfg)
        if not isinstance(self.client, GmailClient):
            raise RuntimeError("Failed to create Gmail client")
        self.client.authenticate(force=force)
        profile = self.client.profile()
        labels = (self.cfg.get("triage") or {}).get("labels") or {}
        created = []
        if hasattr(self.client, "ensure_matrixly_labels"):
            created_map = self.client.ensure_matrixly_labels(labels)
            created = list(created_map.keys())
        else:
            for name in labels.values():
                self.client.ensure_label(name)
                created.append(name)
        profile["matrixly_labels"] = created
        profile["token_status"] = self.client.token_status()
        return profile

    def token_status(self) -> dict[str, Any]:
        if isinstance(self.client, GmailClient):
            return self.client.token_status()
        return {
            "backend": (self.cfg.get("agent") or {}).get("backend"),
            "message": "Token status only applies to EMAIL_BACKEND=gmail",
        }

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
        # Safety: never auto-send customer replies
        draft_cfg = self.cfg.setdefault("draft", {})
        if draft_cfg.get("auto_send"):
            draft_cfg["auto_send"] = False
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

    def impact_report(
        self,
        items: list[TriageItem] | None = None,
        *,
        apply_labels: bool = True,
        use_llm: bool = True,
        write: bool = True,
    ) -> dict[str, Any]:
        if items is None:
            items = self.triage(apply_labels=apply_labels, use_llm=use_llm)
        profile_email = None
        try:
            profile_email = (self.client.profile() or {}).get("emailAddress")
        except Exception:  # noqa: BLE001
            pass
        text = build_impact_report(
            items,
            self.cfg,
            mailbox=profile_email,
            backend="test" if self._test_mode else (self.cfg.get("agent") or {}).get("backend"),
            test_mode=self._test_mode,
        )
        out: dict[str, Any] = {"report": text, "items": items_as_jsonable(items)}
        if write:
            path = write_impact_report(text)
            out["markdown_path"] = str(path)
            out["latest_path"] = str(path.parent / "impact-first-24h-latest.md")
        return out

    def run(self, action: str, **kwargs: Any) -> Any:
        action = (action or "").lower().strip()
        if action in {"triage", "inbox"}:
            gen_impact = bool(kwargs.pop("impact", True))
            items = self.triage(
                apply_labels=kwargs.get("apply_labels", True),
                max_results=kwargs.get("max_results"),
                use_llm=kwargs.get("use_llm", True),
            )
            result = {
                "report": triage_report(items),
                "items": items_as_jsonable(items),
            }
            # Auto-generate first 24h impact after successful triage
            if items and gen_impact:
                impact = self.impact_report(items, write=True)
                result["impact_path"] = impact.get("markdown_path")
                result["impact_report"] = impact.get("report")
            return result
        if action in {"urgent", "flag", "flag_urgent"}:
            items = self.flag_urgent(
                apply_labels=kwargs.get("apply_labels", True),
                max_results=kwargs.get("max_results"),
                use_llm=kwargs.get("use_llm", True),
            )
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
        if action in {"impact", "impact_report", "first-impact"}:
            return self.impact_report(
                apply_labels=kwargs.get("apply_labels", True),
                use_llm=kwargs.get("use_llm", True),
            )
        if action in {"profile", "whoami", "auth"}:
            return self.connect(force=bool(kwargs.get("force")))
        if action in {"connect-gmail", "connect_gmail", "gmail-auth"}:
            return self.connect_gmail(force=bool(kwargs.get("force")))
        if action in {"test-mode", "test_mode", "demo"}:
            demo = EmailAssistant(self.cfg, test_mode=True)
            items = demo.triage(apply_labels=True, use_llm=kwargs.get("use_llm", True))
            impact = demo.impact_report(items, write=True)
            return {
                "report": triage_report(items),
                "items": items_as_jsonable(items),
                "impact_report": impact.get("report"),
                "impact_path": impact.get("markdown_path"),
                "profile": demo.connect(),
                "test_mode": True,
            }
        raise ValueError(
            f"Unknown action '{action}'. Use: triage | urgent | draft | summary | "
            "impact | profile | connect-gmail | test-mode"
        )

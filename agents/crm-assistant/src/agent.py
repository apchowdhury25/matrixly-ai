"""CRM Assistant agent facade."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_config
from .export_sf import export_store
from .extract import extract_with_llm, to_proposed_writes
from .hygiene import hygiene_report, run_hygiene
from .models import Activity, Company, Contact, Deal, ProposedWrite
from .store import CRMStore


class CRMAssistant:
    """Matrixly CRM Assistant — contacts, activities, hygiene, HITL writes."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg or load_config()
        self.store = CRMStore(self.cfg["_paths"]["store"])

    def process_note(
        self,
        text: str,
        *,
        source: str = "note",
        use_llm: bool = True,
        apply: bool = False,
    ) -> dict[str, Any]:
        """Extract CRM updates from free text; queue or apply writes."""
        local_cfg = self.cfg
        if not use_llm:
            local_cfg = {
                **self.cfg,
                "extraction": {**(self.cfg.get("extraction") or {}), "use_llm": False},
            }
        extracted = extract_with_llm(text, local_cfg, source=source)
        writes = to_proposed_writes(extracted, self.cfg)
        queued: list[ProposedWrite] = []
        applied: list[str] = []

        require = (self.cfg.get("writes") or {}).get("require_approval", True)
        auto_local = (self.cfg.get("writes") or {}).get("auto_apply_local", False)

        for w in writes:
            if apply or (not require and auto_local):
                self._apply_write(w)
                w.status = "applied"
                applied.append(w.id)
            else:
                self.store.queue_write(w)
                queued.append(w)

        return {
            "extracted": extracted,
            "queued": [w.to_dict() for w in queued],
            "applied": applied,
            "pending_count": len(self.store.list_pending()),
        }

    def _apply_write(self, w: ProposedWrite) -> None:
        p = w.payload
        if w.action == "upsert_contact":
            self.store.upsert_contact(Contact.from_dict(p))
        elif w.action == "upsert_company":
            self.store.upsert_company(Company.from_dict(p))
        elif w.action == "upsert_deal":
            self.store.upsert_deal(Deal.from_dict(p))
        elif w.action == "log_activity":
            self.store.add_activity(Activity.from_dict(p))
        else:
            raise ValueError(f"Unknown action {w.action}")

    def approve(self, write_id: str) -> dict[str, Any]:
        w = self.store.get_write(write_id)
        if not w:
            raise ValueError(f"Write not found: {write_id}")
        if w.status != "pending":
            raise ValueError(f"Write not pending: {w.status}")
        self._apply_write(w)
        self.store.set_write_status(write_id, "applied")
        return {"id": write_id, "status": "applied", "action": w.action}

    def reject(self, write_id: str) -> dict[str, Any]:
        w = self.store.set_write_status(write_id, "rejected")
        if not w:
            raise ValueError(f"Write not found: {write_id}")
        return {"id": write_id, "status": "rejected"}

    def approve_all(self) -> list[dict[str, Any]]:
        results = []
        for w in list(self.store.list_pending()):
            results.append(self.approve(w.id))
        return results

    def list_pending(self) -> list[dict[str, Any]]:
        return [w.to_dict() for w in self.store.list_pending()]

    def hygiene(self) -> dict[str, Any]:
        issues = run_hygiene(self.store, self.cfg)
        return {"issues": [i.to_dict() for i in issues], "report": hygiene_report(issues)}

    def export(self) -> dict[str, str]:
        return export_store(self.store, self.cfg)

    def upsert_contact_direct(self, data: dict[str, Any], *, approve: bool = False) -> dict[str, Any]:
        c = Contact.from_dict(data) if "email" in data else Contact(email=data.get("email", ""), **{k: v for k, v in data.items() if k != "email"})
        w = ProposedWrite(
            action="upsert_contact",
            payload=c.to_dict(),
            reason="Direct contact upsert",
            confidence=1.0,
            diffs=[f"upsert {c.email}"],
        )
        if approve or not (self.cfg.get("writes") or {}).get("require_approval", True):
            self._apply_write(w)
            w.status = "applied"
            return w.to_dict()
        self.store.queue_write(w)
        return w.to_dict()

    def log_activity_direct(self, data: dict[str, Any], *, approve: bool = False) -> dict[str, Any]:
        a = Activity.from_dict(data)
        w = ProposedWrite(
            action="log_activity",
            payload=a.to_dict(),
            reason="Direct activity log",
            confidence=1.0,
            diffs=[f"log {a.type}"],
        )
        if approve or not (self.cfg.get("writes") or {}).get("require_approval", True):
            self._apply_write(w)
            w.status = "applied"
            return w.to_dict()
        self.store.queue_write(w)
        return w.to_dict()

    def seed_from_file(self, path: str | Path) -> dict[str, int]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        n_c = n_d = n_a = 0
        for c in data.get("contacts") or []:
            self.store.upsert_contact(Contact.from_dict(c))
            n_c += 1
        for d in data.get("deals") or []:
            self.store.upsert_deal(Deal.from_dict(d))
            n_d += 1
        for a in data.get("activities") or []:
            self.store.add_activity(Activity.from_dict(a))
            n_a += 1
        return {"contacts": n_c, "deals": n_d, "activities": n_a}

    def status_report(self) -> str:
        lines = [
            "# CRM Assistant Status",
            "",
            f"**Contacts:** {len(self.store.list_contacts())}",
            f"**Companies:** {len(self.store.data.get('companies', {}))}",
            f"**Deals:** {len(self.store.list_deals())}",
            f"**Activities:** {len(self.store.list_activities())}",
            f"**Pending writes:** {len(self.store.list_pending())}",
            "",
        ]
        pending = self.store.list_pending()
        if pending:
            lines.append("## Pending approvals")
            for w in pending[:20]:
                lines.append(f"- `{w.id}` **{w.action}** conf={w.confidence:.2f} — {w.reason}")
                for d in w.diffs[:3]:
                    lines.append(f"  - {d}")
        return "\n".join(lines)

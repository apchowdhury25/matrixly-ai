"""Local CRM store (JSON) for pilot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Activity, Company, Contact, Deal, ProposedWrite


class CRMStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict[str, Any] = {
            "contacts": {},
            "companies": {},
            "deals": {},
            "activities": {},
            "pending_writes": {},
        }
        self.load()

    def load(self) -> None:
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            for k in ("contacts", "companies", "deals", "activities", "pending_writes"):
                self.data.setdefault(k, {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    # --- contacts ---
    def get_contact_by_email(self, email: str) -> Contact | None:
        email = (email or "").lower()
        for c in self.data["contacts"].values():
            if c.get("email") == email:
                return Contact.from_dict(c)
        return None

    def upsert_contact(self, contact: Contact) -> Contact:
        existing = self.get_contact_by_email(contact.email)
        if existing:
            # merge non-empty fields
            base = existing.to_dict()
            incoming = contact.to_dict()
            for k, v in incoming.items():
                if k in ("id", "created_at"):
                    continue
                if v not in (None, "", [], {}):
                    base[k] = v
            contact = Contact.from_dict(base)
        self.data["contacts"][contact.id] = contact.to_dict()
        self.save()
        return contact

    def list_contacts(self) -> list[Contact]:
        return [Contact.from_dict(c) for c in self.data["contacts"].values()]

    # --- companies ---
    def get_company_by_name(self, name: str) -> Company | None:
        key = (name or "").strip().lower()
        for c in self.data["companies"].values():
            if (c.get("name") or "").strip().lower() == key:
                return Company.from_dict(c)
        return None

    def upsert_company(self, company: Company) -> Company:
        existing = self.get_company_by_name(company.name)
        if existing:
            base = existing.to_dict()
            for k, v in company.to_dict().items():
                if k in ("id",):
                    continue
                if v not in (None, "", []):
                    base[k] = v
            company = Company.from_dict(base)
        self.data["companies"][company.id] = company.to_dict()
        self.save()
        return company

    # --- deals ---
    def list_deals(self) -> list[Deal]:
        return [Deal.from_dict(d) for d in self.data["deals"].values()]

    def upsert_deal(self, deal: Deal) -> Deal:
        if deal.id in self.data["deals"]:
            base = self.data["deals"][deal.id]
            for k, v in deal.to_dict().items():
                if v not in (None, "", []):
                    base[k] = v
            deal = Deal.from_dict(base)
        self.data["deals"][deal.id] = deal.to_dict()
        self.save()
        return deal

    # --- activities ---
    def add_activity(self, activity: Activity) -> Activity:
        self.data["activities"][activity.id] = activity.to_dict()
        # bump deal last_activity
        if activity.deal_id and activity.deal_id in self.data["deals"]:
            self.data["deals"][activity.deal_id]["last_activity_at"] = activity.occurred_at
        self.save()
        return activity

    def list_activities(self) -> list[Activity]:
        return [Activity.from_dict(a) for a in self.data["activities"].values()]

    # --- pending writes ---
    def queue_write(self, write: ProposedWrite) -> ProposedWrite:
        self.data["pending_writes"][write.id] = write.to_dict()
        self.save()
        return write

    def list_pending(self) -> list[ProposedWrite]:
        return [
            ProposedWrite.from_dict(w)
            for w in self.data["pending_writes"].values()
            if w.get("status") == "pending"
        ]

    def get_write(self, write_id: str) -> ProposedWrite | None:
        w = self.data["pending_writes"].get(write_id)
        return ProposedWrite.from_dict(w) if w else None

    def set_write_status(self, write_id: str, status: str) -> ProposedWrite | None:
        w = self.get_write(write_id)
        if not w:
            return None
        w.status = status
        self.data["pending_writes"][write_id] = w.to_dict()
        self.save()
        return w

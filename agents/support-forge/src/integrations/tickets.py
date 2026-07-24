"""Zendesk-style tickets with JSON fallback (and optional Zendesk REST stub)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import httpx

from ..models import Customer, Ticket, TicketMessage, new_id, utc_now


class TicketStore:
    def __init__(self, data_dir: str | Path, cfg: dict | None = None) -> None:
        self.dir = Path(data_dir) / "tickets"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.crm_path = Path(data_dir) / "crm" / "contacts.json"
        self.crm_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_path = Path(data_dir) / "crm" / "contacts.csv"
        self.cfg = cfg or {}

    def _path(self, ticket_id: str) -> Path:
        return self.dir / f"{ticket_id}.json"

    def create(
        self,
        *,
        subject: str,
        channel: str,
        customer: Customer | None = None,
        body: str = "",
        priority: str = "normal",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Ticket:
        t = Ticket(
            id=new_id("tkt_"),
            subject=subject or "Support request",
            channel=channel,
            customer=customer or Customer(),
            priority=priority,
            tags=tags or [],
            metadata=metadata or {},
        )
        if body:
            t.messages.append(TicketMessage(role="customer", content=body))
        self.save(t)
        self._upsert_crm(t.customer)
        self._maybe_push_zendesk(t)
        return t

    def save(self, ticket: Ticket) -> None:
        ticket.updated_at = utc_now()
        with self._path(ticket.id).open("w", encoding="utf-8") as f:
            json.dump(ticket.model_dump(), f, indent=2, ensure_ascii=False)

    def get(self, ticket_id: str) -> Ticket | None:
        p = self._path(ticket_id)
        if not p.exists():
            return None
        with p.open(encoding="utf-8") as f:
            return Ticket(**json.load(f))

    def list(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Ticket]:
        tickets: list[Ticket] = []
        for p in sorted(self.dir.glob("*.json"), reverse=True):
            try:
                with p.open(encoding="utf-8") as f:
                    t = Ticket(**json.load(f))
                if status and t.status != status:
                    continue
                tickets.append(t)
            except Exception:
                continue
            if len(tickets) >= limit:
                break
        return tickets

    def list_escalated(self, limit: int = 50) -> list[Ticket]:
        return [
            t
            for t in self.list(limit=200)
            if t.status == "escalated" or "escalated" in t.tags
        ][:limit]

    def add_message(
        self,
        ticket_id: str,
        role: str,
        content: str,
        meta: dict[str, Any] | None = None,
    ) -> Ticket | None:
        t = self.get(ticket_id)
        if not t:
            return None
        t.messages.append(
            TicketMessage(role=role, content=content, meta=meta or {})
        )
        self.save(t)
        return t

    def update_fields(self, ticket_id: str, **fields: Any) -> Ticket | None:
        t = self.get(ticket_id)
        if not t:
            return None
        data = t.model_dump()
        data.update(fields)
        t2 = Ticket(**data)
        self.save(t2)
        return t2

    def _upsert_crm(self, customer: Customer) -> None:
        if not customer.email and not customer.name:
            return
        contacts: list[dict[str, Any]] = []
        if self.crm_path.exists():
            try:
                contacts = json.loads(self.crm_path.read_text(encoding="utf-8"))
            except Exception:
                contacts = []
        email = (customer.email or "").lower()
        found = False
        for c in contacts:
            if email and (c.get("email") or "").lower() == email:
                c.update({k: v for k, v in customer.model_dump().items() if v})
                c["updated_at"] = utc_now()
                found = True
                break
        if not found:
            row = customer.model_dump()
            row["updated_at"] = utc_now()
            contacts.append(row)
        self.crm_path.write_text(
            json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        # CSV mirror for non-technical export
        with self.csv_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f, fieldnames=["name", "email", "phone", "external_id", "updated_at"]
            )
            w.writeheader()
            for c in contacts:
                w.writerow({k: c.get(k, "") for k in w.fieldnames})

    def _maybe_push_zendesk(self, ticket: Ticket) -> None:
        zd = self.cfg.get("zendesk") or {}
        sub = zd.get("subdomain") or ""
        email = zd.get("email") or ""
        token = zd.get("api_token") or ""
        if not (sub and email and token):
            return
        # Optional live create — failures are non-fatal
        url = f"https://{sub}.zendesk.com/api/v2/tickets.json"
        payload = {
            "ticket": {
                "subject": ticket.subject,
                "comment": {
                    "body": ticket.messages[0].content if ticket.messages else ticket.subject
                },
                "priority": ticket.priority,
                "requester": {
                    "name": ticket.customer.name or "Customer",
                    "email": ticket.customer.email or "unknown@example.com",
                },
                "tags": ticket.tags,
            }
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    url,
                    json=payload,
                    auth=(f"{email}/token", token),
                )
                if resp.is_success:
                    data = resp.json()
                    zid = (data.get("ticket") or {}).get("id")
                    if zid:
                        ticket.metadata["zendesk_id"] = zid
                        self.save(ticket)
        except Exception:
            pass

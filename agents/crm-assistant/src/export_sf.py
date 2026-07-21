"""Salesforce-shaped export for contacts, tasks, opportunities."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Activity, Contact, Deal
from .store import CRMStore


def contact_to_sf(c: Contact) -> dict[str, Any]:
    return {
        "attributes": {"type": "Contact"},
        "FirstName": c.first_name or None,
        "LastName": c.last_name or c.full_name or "Unknown",
        "Email": c.email,
        "Title": c.title or None,
        "Phone": c.phone or None,
        "Account": {"Name": c.company_name} if c.company_name else None,
        "LeadSource": c.source or "Matrixly CRM Assistant",
        "Description": f"Matrixly contact id={c.id}",
    }


def activity_to_sf_task(a: Activity) -> dict[str, Any]:
    return {
        "attributes": {"type": "Task"},
        "Subject": a.subject,
        "Description": a.body,
        "Status": "Completed",
        "Priority": "Normal",
        "ActivityDate": (a.occurred_at or "")[:10] or None,
        "Type": a.type.title() if a.type else "Other",
        "Who": {"Email": a.contact_email} if a.contact_email else None,
    }


def deal_to_sf_opp(d: Deal) -> dict[str, Any]:
    return {
        "attributes": {"type": "Opportunity"},
        "Name": d.name,
        "StageName": d.stage,
        "Amount": d.amount,
        "NextStep": d.next_step or None,
        "CloseDate": (d.close_date or "")[:10] or None,
        "Description": f"contact={d.contact_email}; company={d.company_name}; matrixly_id={d.id}",
    }


def export_store(store: CRMStore, cfg: dict[str, Any]) -> dict[str, str]:
    sf = cfg.get("salesforce") or {}
    out = Path(sf.get("export_dir") or "data/output/salesforce")
    if not out.is_absolute():
        out = Path((cfg.get("_paths") or {}).get("root") or ".") / out
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    contacts = [contact_to_sf(c) for c in store.list_contacts()]
    tasks = [activity_to_sf_task(a) for a in store.list_activities()]
    opps = [deal_to_sf_opp(d) for d in store.list_deals()]

    bundle = {"contacts": contacts, "tasks": tasks, "opportunities": opps}
    json_path = out / f"crm-export-{stamp}.json"
    json_path.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")

    # Contacts CSV
    csv_path = out / f"contacts-{stamp}.csv"
    rows = []
    for c in store.list_contacts():
        rows.append(
            {
                "FirstName": c.first_name,
                "LastName": c.last_name or c.full_name or "Unknown",
                "Email": c.email,
                "Title": c.title,
                "Phone": c.phone,
                "Company": c.company_name,
                "Owner": c.owner,
            }
        )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        fields = list(rows[0].keys()) if rows else ["Email"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    return {"json": str(json_path), "contacts_csv": str(csv_path)}

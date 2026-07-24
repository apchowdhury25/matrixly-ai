"""CRM adapters: local JSON/CSV, HubSpot, Salesforce stubs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import httpx

from ..models import CrmUpdate, Opportunity, utc_now


class CrmClient:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.dir = Path(data_dir) / "crm"
        self.dir.mkdir(parents=True, exist_ok=True)

    def load_opportunities(self) -> list[Opportunity]:
        backend = ((self.cfg.get("crm") or {}).get("backend") or "local").lower()
        if backend == "hubspot":
            return self._hubspot_load()
        if backend == "salesforce":
            return self._salesforce_load()
        return self._local_load()

    def apply_updates(self, updates: list[CrmUpdate]) -> list[CrmUpdate]:
        backend = ((self.cfg.get("crm") or {}).get("backend") or "local").lower()
        applied: list[CrmUpdate] = []
        for u in updates:
            if backend == "hubspot":
                result = self._hubspot_write(u)
            elif backend == "salesforce":
                result = self._salesforce_write(u)
            else:
                result = self._local_write(u)
            u.applied = bool(result.get("ok"))
            u.result = result
            applied.append(u)
        self._export_csv(applied)
        return applied

    def _local_load(self) -> list[Opportunity]:
        path = self.dir / "opportunities.json"
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [Opportunity(**row) for row in data]
        except Exception:
            return []

    def seed_local(self, opps: list[Opportunity]) -> Path:
        path = self.dir / "opportunities.json"
        path.write_text(
            json.dumps([o.model_dump() for o in opps], indent=2),
            encoding="utf-8",
        )
        return path

    def _local_write(self, u: CrmUpdate) -> dict[str, Any]:
        log = self.dir / "writes.jsonl"
        row = {"ts": utc_now(), "backend": "local", **u.model_dump()}
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        # also update stage in local opportunities if present
        if u.action == "update_stage" and u.stage:
            opps = self._local_load()
            changed = False
            for o in opps:
                if o.id == u.opportunity_id:
                    o.stage = u.stage
                    changed = True
            if changed:
                self.seed_local(opps)
        return {"ok": True, "backend": "local", "logged": True}

    def _export_csv(self, updates: list[CrmUpdate]) -> None:
        path = self.dir / "pending_updates.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                ["opportunity_id", "action", "stage", "task_subject", "note", "applied", "confidence"]
            )
            for u in updates:
                w.writerow(
                    [
                        u.opportunity_id,
                        u.action,
                        u.stage or "",
                        u.task_subject or "",
                        (u.note or "")[:200],
                        u.applied,
                        u.confidence,
                    ]
                )

    def _hubspot_load(self) -> list[Opportunity]:
        token = (self.cfg.get("hubspot") or {}).get("access_token")
        if not token:
            return self._local_load()
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.hubapi.com/crm/v3/objects/deals/search",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "filterGroups": [],
                        "properties": [
                            "dealname",
                            "amount",
                            "dealstage",
                            "hubspot_owner_id",
                            "closedate",
                        ],
                        "limit": 50,
                    },
                )
                if resp.status_code >= 400:
                    return self._local_load()
                data = resp.json()
                out: list[Opportunity] = []
                for row in data.get("results") or []:
                    props = row.get("properties") or {}
                    out.append(
                        Opportunity(
                            id=str(row.get("id")),
                            name=str(props.get("dealname") or row.get("id")),
                            amount=float(props.get("amount") or 0),
                            stage=str(props.get("dealstage") or "lead"),
                            owner=str(props.get("hubspot_owner_id") or ""),
                            source="hubspot",
                        )
                    )
                return out
        except Exception:
            return self._local_load()

    def _hubspot_write(self, u: CrmUpdate) -> dict[str, Any]:
        token = (self.cfg.get("hubspot") or {}).get("access_token")
        if not token:
            r = self._local_write(u)
            r["note"] = "HUBSPOT token missing — local stub"
            return r
        try:
            with httpx.Client(timeout=30.0) as client:
                if u.action == "update_stage" and u.stage:
                    resp = client.patch(
                        f"https://api.hubapi.com/crm/v3/objects/deals/{u.opportunity_id}",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        json={"properties": {"dealstage": u.stage}},
                    )
                    return {
                        "ok": resp.status_code < 400,
                        "backend": "hubspot",
                        "status_code": resp.status_code,
                        "body": resp.text[:400],
                    }
                # notes/tasks as engagement stub
                return {
                    "ok": True,
                    "backend": "hubspot",
                    "note": "Logged engagement intent; create task via HubSpot tasks API in production.",
                    "update": u.model_dump(),
                }
        except Exception as e:
            r = self._local_write(u)
            r["ok"] = False
            r["error"] = str(e)
            return r

    def _salesforce_load(self) -> list[Opportunity]:
        sf = self.cfg.get("salesforce") or {}
        if not sf.get("instance_url") or not sf.get("access_token"):
            return self._local_load()
        try:
            ver = sf.get("api_version") or "v59.0"
            q = "SELECT Id,Name,Amount,StageName,Owner.Name FROM Opportunity WHERE IsClosed=false LIMIT 50"
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{sf['instance_url']}/services/data/{ver}/query",
                    params={"q": q},
                    headers={"Authorization": f"Bearer {sf['access_token']}"},
                )
                if resp.status_code >= 400:
                    return self._local_load()
                data = resp.json()
                out: list[Opportunity] = []
                for row in data.get("records") or []:
                    owner = (row.get("Owner") or {}).get("Name") or ""
                    out.append(
                        Opportunity(
                            id=str(row.get("Id")),
                            name=str(row.get("Name") or ""),
                            amount=float(row.get("Amount") or 0),
                            stage=str(row.get("StageName") or "lead"),
                            owner=str(owner),
                            source="salesforce",
                        )
                    )
                return out
        except Exception:
            return self._local_load()

    def _salesforce_write(self, u: CrmUpdate) -> dict[str, Any]:
        sf = self.cfg.get("salesforce") or {}
        if not sf.get("instance_url") or not sf.get("access_token"):
            r = self._local_write(u)
            r["note"] = "Salesforce credentials missing — local stub"
            return r
        ver = sf.get("api_version") or "v59.0"
        try:
            with httpx.Client(timeout=30.0) as client:
                if u.action == "update_stage" and u.stage:
                    resp = client.patch(
                        f"{sf['instance_url']}/services/data/{ver}/sobjects/Opportunity/{u.opportunity_id}",
                        headers={
                            "Authorization": f"Bearer {sf['access_token']}",
                            "Content-Type": "application/json",
                        },
                        json={"StageName": u.stage},
                    )
                    return {
                        "ok": resp.status_code < 400,
                        "backend": "salesforce",
                        "status_code": resp.status_code,
                        "body": resp.text[:400],
                    }
                if u.action == "create_task" and u.task_subject:
                    resp = client.post(
                        f"{sf['instance_url']}/services/data/{ver}/sobjects/Task",
                        headers={
                            "Authorization": f"Bearer {sf['access_token']}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "Subject": u.task_subject,
                            "WhatId": u.opportunity_id,
                            "Status": "Not Started",
                            "Description": u.note or "",
                        },
                    )
                    return {
                        "ok": resp.status_code < 400,
                        "backend": "salesforce",
                        "status_code": resp.status_code,
                        "body": resp.text[:400],
                    }
                return self._local_write(u)
        except Exception as e:
            r = self._local_write(u)
            r["ok"] = False
            r["error"] = str(e)
            return r

"""Optional CRM client lookup for document intake."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


class ClientCrm:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.dir = Path(data_dir) / "crm"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.local_path = self.dir / "clients.json"

    def get_client(self, account: str) -> dict[str, Any] | None:
        backend = ((self.cfg.get("crm") or {}).get("backend") or "local").lower()
        if backend == "hubspot":
            return self._hubspot(account)
        if backend == "salesforce":
            return self._salesforce(account)
        return self._local(account)

    def seed_demo(self) -> None:
        if self.local_path.exists():
            return
        data = [
            {
                "company": "Acme Logistics",
                "name": "Jordan Lee",
                "contact": "Jordan Lee",
                "email": "jordan@acmelogistics.example",
                "industry": "logistics",
            },
            {
                "company": "Nova SaaS",
                "name": "Sam Chen",
                "contact": "Sam Chen",
                "email": "sam@novasaas.example",
                "industry": "saas",
            },
        ]
        self.local_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _local(self, account: str) -> dict[str, Any] | None:
        self.seed_demo()
        if not self.local_path.exists():
            return None
        try:
            rows = json.loads(self.local_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        key = (account or "").lower()
        for row in rows:
            if key in str(row.get("company") or "").lower() or key in str(row.get("name") or "").lower():
                return row
        return rows[0] if rows and not account else None

    def _hubspot(self, account: str) -> dict[str, Any] | None:
        token = (self.cfg.get("hubspot") or {}).get("access_token")
        if not token:
            return self._local(account)
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    "https://api.hubapi.com/crm/v3/objects/companies/search",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "filterGroups": [
                            {
                                "filters": [
                                    {
                                        "propertyName": "name",
                                        "operator": "CONTAINS_TOKEN",
                                        "value": account or "a",
                                    }
                                ]
                            }
                        ],
                        "properties": ["name", "domain", "industry"],
                        "limit": 1,
                    },
                )
                if resp.status_code >= 400:
                    return self._local(account)
                results = (resp.json() or {}).get("results") or []
                if not results:
                    return self._local(account)
                props = results[0].get("properties") or {}
                return {
                    "company": props.get("name") or account,
                    "name": props.get("name") or account,
                    "email": "",
                    "industry": props.get("industry") or "",
                }
        except Exception:
            return self._local(account)

    def _salesforce(self, account: str) -> dict[str, Any] | None:
        sf = self.cfg.get("salesforce") or {}
        if not sf.get("instance_url") or not sf.get("access_token"):
            return self._local(account)
        try:
            q = f"SELECT Name, Industry FROM Account WHERE Name LIKE '%{(account or 'A')[:40]}%' LIMIT 1"
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(
                    f"{sf['instance_url']}/services/data/v59.0/query",
                    params={"q": q},
                    headers={"Authorization": f"Bearer {sf['access_token']}"},
                )
                if resp.status_code >= 400:
                    return self._local(account)
                recs = (resp.json() or {}).get("records") or []
                if not recs:
                    return self._local(account)
                r = recs[0]
                return {
                    "company": r.get("Name") or account,
                    "name": r.get("Name") or account,
                    "industry": r.get("Industry") or "",
                    "email": "",
                }
        except Exception:
            return self._local(account)

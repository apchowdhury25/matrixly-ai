"""Salesforce Lead payload builder + file export (MVP)."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Enrichment, Lead, ScoreResult


def build_lead_payload(
    lead: Lead,
    enrichment: Enrichment,
    score: ScoreResult,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    sf = cfg.get("salesforce") or {}
    company = enrichment.company or lead.company or lead.domain or "Unknown"
    description_parts = [
        f"Matrixly score: {score.score} ({score.tier})",
        f"Action: {score.recommended_action}",
        f"Reasons: {'; '.join(score.reasons[:6])}",
        f"Enrichment: {enrichment.provider} conf={enrichment.confidence}",
    ]
    if lead.notes:
        description_parts.append(f"Notes: {lead.notes[:500]}")

    # Salesforce Lead standard fields
    payload = {
        "attributes": {"type": sf.get("object") or "Lead"},
        "FirstName": lead.first_name or None,
        "LastName": lead.last_name or lead.full_name or "Unknown",
        "Email": lead.email,
        "Company": company,
        "Title": lead.title or None,
        "Phone": lead.phone or None,
        "Website": enrichment.website or lead.website or None,
        "Industry": enrichment.industry or lead.industry or None,
        "City": lead.city or None,
        "State": lead.state or None,
        "Country": lead.country or None,
        "LeadSource": lead.source or sf.get("default_source") or "Matrixly Lead Qualifier",
        "Status": sf.get("default_status") or "Open - Not Contacted",
        "Description": "\n".join(description_parts),
        # Custom fields (create in SF org as needed)
        "Matrixly_Score__c": score.score,
        "Matrixly_Tier__c": score.tier,
        "Matrixly_Fit__c": score.fit,
        "Matrixly_Intent__c": score.intent,
    }
    # Drop nulls for cleaner export
    return {k: v for k, v in payload.items() if v is not None}


def export_leads(
    payloads: list[dict[str, Any]],
    cfg: dict[str, Any],
    *,
    stem: str | None = None,
) -> dict[str, str]:
    sf = cfg.get("salesforce") or {}
    out_dir = Path(sf.get("export_dir") or "data/output/salesforce")
    if not out_dir.is_absolute():
        root = Path((cfg.get("_paths") or {}).get("root") or ".")
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = stem or f"leads-{stamp}"
    json_path = out_dir / f"{base}.json"
    csv_path = out_dir / f"{base}.csv"

    json_path.write_text(json.dumps(payloads, indent=2), encoding="utf-8")

    # Flatten for Data Loader CSV
    rows: list[dict[str, Any]] = []
    for p in payloads:
        row = {k: v for k, v in p.items() if k != "attributes"}
        rows.append(row)
    fieldnames: list[str] = []
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames or ["Email"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return {"json": str(json_path), "csv": str(csv_path)}

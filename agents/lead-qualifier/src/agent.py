"""Lead Qualifier agent facade."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_config
from .enrich import enrich_lead
from .gmail_ingest import ingest_leads_from_gmail
from .models import Lead, QualifiedLead
from .outreach import build_sequence
from .salesforce import build_lead_payload, export_leads
from .scoring import score_lead


class LeadQualifier:
    """Matrixly Lead Qualifier — score, enrich, outreach, Salesforce export."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg or load_config()

    def qualify_one(
        self,
        lead: Lead | dict[str, Any],
        *,
        use_llm: bool = True,
    ) -> QualifiedLead:
        if isinstance(lead, dict):
            lead = Lead.from_dict(lead)
        enrichment = enrich_lead(lead, self.cfg, use_llm=use_llm)
        score = score_lead(lead, enrichment, self.cfg)
        sequence = build_sequence(lead, enrichment, score, self.cfg, use_llm=use_llm)
        sf_payload = build_lead_payload(lead, enrichment, score, self.cfg)
        return QualifiedLead(
            lead=lead,
            enrichment=enrichment,
            score=score,
            sequence=sequence,
            salesforce_payload=sf_payload,
        )

    def qualify_many(
        self,
        leads: list[Lead | dict[str, Any]],
        *,
        use_llm: bool = True,
    ) -> list[QualifiedLead]:
        results = [self.qualify_one(L, use_llm=use_llm) for L in leads]
        # Hot first
        order = {"hot": 0, "warm": 1, "cold": 2, "disqualified": 3}
        results.sort(key=lambda q: (order.get(q.score.tier, 9), -q.score.score))
        return results

    def load_leads_file(self, path: str | Path) -> list[Lead]:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "leads" in data:
            data = data["leads"]
        if not isinstance(data, list):
            raise ValueError("Lead file must be a JSON list or {leads: [...]}")
        return [Lead.from_dict(x) for x in data]

    def ingest_gmail(self, *, max_messages: int | None = None) -> list[Lead]:
        return ingest_leads_from_gmail(self.cfg, max_messages=max_messages)

    def export_salesforce(self, qualified: list[QualifiedLead], stem: str | None = None) -> dict[str, str]:
        payloads = [q.salesforce_payload for q in qualified if q.score.tier != "disqualified"]
        return export_leads(payloads, self.cfg, stem=stem)

    def report(self, qualified: list[QualifiedLead]) -> str:
        lines = ["# Lead Qualifier Report", ""]
        if not qualified:
            lines.append("No leads processed.")
            return "\n".join(lines)

        tiers: dict[str, int] = {}
        for q in qualified:
            tiers[q.score.tier] = tiers.get(q.score.tier, 0) + 1
        lines.append(f"**Total:** {len(qualified)}")
        for t in ("hot", "warm", "cold", "disqualified"):
            if t in tiers:
                lines.append(f"- **{t}:** {tiers[t]}")
        lines.append("")

        for q in qualified:
            L = q.lead
            S = q.score
            E = q.enrichment
            lines.append(
                f"## {L.full_name or L.email} — {S.tier.upper()} ({S.score})"
            )
            lines.append(f"- **Email:** {L.email}")
            lines.append(f"- **Company:** {E.company or L.company or '—'}")
            lines.append(f"- **Title:** {L.title or '—'}")
            lines.append(f"- **Industry:** {E.industry or L.industry or '—'}")
            lines.append(f"- **Fit/Intent/Seniority/DQ:** {S.fit}/{S.intent}/{S.seniority}/{S.data_quality}")
            lines.append(f"- **Action:** {S.recommended_action}")
            if S.reasons:
                lines.append(f"- **Why:** {'; '.join(S.reasons[:5])}")
            if q.sequence:
                lines.append(f"- **Sequence:** {len(q.sequence)} touches")
                for t in q.sequence[:2]:
                    lines.append(f"  - Day {t.day}: {t.subject}")
            lines.append("")
        return "\n".join(lines)

    def run(
        self,
        action: str,
        *,
        leads: list[Lead | dict[str, Any]] | None = None,
        path: str | None = None,
        use_llm: bool = True,
        export: bool = True,
    ) -> dict[str, Any]:
        action = (action or "").lower().strip()
        if action in {"gmail", "ingest"}:
            leads = self.ingest_gmail()
        elif path:
            leads = self.load_leads_file(path)
        leads = leads or []

        if action in {"score", "qualify", "run", "gmail", "ingest"}:
            qualified = self.qualify_many(leads, use_llm=use_llm)
            out: dict[str, Any] = {
                "report": self.report(qualified),
                "results": [q.to_dict() for q in qualified],
            }
            if export and qualified:
                paths = self.export_salesforce(qualified)
                out["salesforce_export"] = paths
            return out
        if action == "sample":
            sample = Path(self.cfg["_paths"]["root"]) / "data" / "leads" / "sample_leads.json"
            return self.run("qualify", path=str(sample), use_llm=use_llm, export=export)
        raise ValueError(f"Unknown action {action!r}. Use: qualify | gmail | sample")

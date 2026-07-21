# Lead Qualifier (Matrixly.AI)

**Marketplace tile:** LEAD · **Domain:** Sales · **Status:** MVP pilot  
**Integrations:** Salesforce · Gmail

> Scores inbound leads, enriches contact data, and suggests personalized outreach sequences.

## What it does

| Step | Output |
|------|--------|
| **Score** | 0–1 score + tier (`hot` / `warm` / `cold` / `disqualified`) |
| **Enrich** | Company, industry, website, location signals (heuristic + optional Grok) |
| **Outreach** | 4-touch email sequence (days 0 / 2 / 5 / 9) — drafts only |
| **Salesforce** | Lead JSON + CSV for Data Loader / API import |

## Quick start

```powershell
cd C:\Users\anwar\projects\matrix-six\agents\lead-qualifier
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Demo with sample Houston pilot leads
python -m src.cli sample --no-llm

# Qualify a JSON file
python -m src.cli qualify -f data\leads\sample_leads.json

# Single lead
python -m src.cli score-one --email ops@acme.com --name "Priya Shah" --title "VP Sales" --company "Acme Logistics" --notes "Wants a pilot this month"

# Pull lead-like messages from Gmail (uses email-assistant .env App Password)
python -m src.cli gmail --no-llm
```

Optional `.env`:

```
XAI_API_KEY=...   # richer enrichment + outreach copy
```

## Salesforce export

Each run writes:

- `data/output/salesforce/leads-*.json` — API-shaped Lead records  
- `data/output/salesforce/leads-*.csv` — Data Loader friendly  

Fields include standard Lead columns plus optional customs:

- `Matrixly_Score__c`, `Matrixly_Tier__c`, `Matrixly_Fit__c`, `Matrixly_Intent__c`

Create those custom fields in Salesforce (or strip them from CSV) before import.

## Gmail

Uses the Email Assistant Gmail profile (`usmatrixbazaar@gmail.com` App Password in `../email-assistant/.env`). Filters subjects/bodies for demo/pricing/pilot/inquiry signals and converts senders into leads.

## Hermes

```powershell
hermes -s lead-qualifier -z "Qualify the sample leads and list hot prospects with first outreach touch"
```

Skill: `~/.hermes/skills/sales/lead-qualifier/SKILL.md`

## ICP defaults (pilot)

Houston SMEs · logistics / distribution / HVAC / import-export · owners & sales leaders · 5–200 employees.

Edit `config.yaml` → `icp` and `scoring.thresholds` per customer pilot.

## Roadmap

See **[ROADMAP.md](ROADMAP.md)** — P0/P1 product roadmap while keeping human-in-the-loop (drafts only; approve to send).

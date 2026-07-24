# Matrixly PipelineForge

**Marketplace tile:** PIPE · **Domain:** Sales / Revenue  
**Embeddable AI agent** that scores and prioritizes SMB sales pipelines: fit/engagement/behavior scoring, daily work lists, at-risk flags, CRM stage/task updates, and pipeline health insights — with **human oversight before CRM writes**.

## Pipeline (CrewAI / LangGraph-style)

```
Opportunities (JSON / CSV / HubSpot / Salesforce)
  → Scorer (fit · engagement · behavior · urgency)
  → Prioritizer (daily/weekly rep list)
  → Risk analyst (at-risk + next actions)
  → CRM mapper (stage / task / note)
  → Insights (health)
  → HITL → apply CRM
```

Stack: **Python + FastAPI**, optional Grok, configurable scoring in `config.yaml`, dark embeddable dashboard.

Default port: **8795**.

---

## Quick start

```powershell
cd agents/pipeline-forge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli demo
python -m src.cli serve
```

| URL | Purpose |
|-----|---------|
| http://localhost:8795/v1/health | Health |
| http://localhost:8795/static/dashboard/index.html | Pipeline dashboard |
| http://localhost:8795/docs | OpenAPI |

### `.env`

```env
PIPELINEFORGE_API_KEY=your-admin-secret
PIPELINEFORGE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=
CRM_BACKEND=local
HITL_AUTO_APPROVE=false
CORS_ORIGINS=http://localhost:8080,https://matrixly.world
```

---

## Scoring rules configuration

Edit **`config.yaml` → `scoring:`**:

```yaml
scoring:
  weights:
    fit: 0.35
    engagement: 0.30
    behavior: 0.25
    urgency: 0.10
  hot_min: 75
  warm_min: 50
  at_risk_score_max: 45
  stale_days: 14
  high_value_amount: 10000
  fit_signals:
    industries: [saas, ecommerce, logistics]
    titles: [ceo, founder, vp sales]
  engagement_boosts:
    demo_requested: 25
    meeting_booked: 30
    reply: 15
  behavior_penalties:
    no_activity_days_14: -18
```

Operator notes (persistent memory):

```powershell
# via API
# POST /v1/playbook/notes  { "note": "Healthcare deals need longer cycles" }
```

Stored under `data/memory/playbook_notes.json`.

---

## CRM connections

### Local JSON / CSV (default)

- Seed/read: `data/crm/opportunities.json`
- Writes log: `data/crm/writes.jsonl`
- Export: `data/crm/pending_updates.csv`
- Sample input: `samples/pipeline.json`

### HubSpot

```env
CRM_BACKEND=hubspot
HUBSPOT_ACCESS_TOKEN=
HUBSPOT_PIPELINE_ID=
```

Loads open deals via CRM search; stage updates via deal PATCH. Tasks/notes are stub-friendly for production wiring.

### Salesforce

```env
CRM_BACKEND=salesforce
SF_INSTANCE_URL=https://your-domain.my.salesforce.com
SF_ACCESS_TOKEN=
SF_API_VERSION=v59.0
```

Queries open Opportunities; supports StageName updates and Task creation.

---

## API (high level)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/analyze` | widget/API | Score + prioritize pipeline |
| POST | `/v1/demo` | widget/API | Sample pipeline run |
| GET | `/v1/runs` | API | List analysis runs |
| GET | `/v1/runs/{id}` | API | Run detail |
| GET | `/v1/priority` | API | Latest priority list |
| POST | `/v1/crm/apply` | API | Apply CRM updates (if not pending HITL) |
| GET | `/v1/scoring` | API | Active scoring config + playbook |
| GET | `/v1/admin/hitl` | API | Pending approvals |
| POST | `/v1/admin/hitl/{id}/approve` | API | Approve → apply CRM |
| GET | `/v1/admin/usage` | API | Usage / cost |
| GET | `/v1/admin/audit` | API | Audit trail |

Headers: `X-API-Key` or `X-Widget-Key`.

---

## CLI

```powershell
python -m src.cli status
python -m src.cli demo
python -m src.cli analyze samples/pipeline.json
python -m src.cli analyze --source crm
python -m src.cli priority
python -m src.cli pending
python -m src.cli approve --id hitl_…
python -m src.cli apply-crm --id run_…
python -m src.cli serve --port 8795
```

---

## Embed code

```html
<iframe
  src="https://YOUR_PIPELINEFORGE_HOST/static/dashboard/index.html"
  title="PipelineForge"
  style="width:100%;min-height:800px;border:1px solid #1e2a3a;border-radius:12px;"
></iframe>

<script
  src="https://YOUR_PIPELINEFORGE_HOST/static/widget/embed.js"
  data-api="https://YOUR_PIPELINEFORGE_HOST"
  async>
</script>
```

---

## Deployment

```powershell
cd agents/pipeline-forge
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8795
```

### Docker

```bash
docker build -t pipeline-forge .
docker run -d -p 8795:8795 --env-file .env -v $PWD/data:/app/data pipeline-forge
```

### Production checklist

- [ ] Tune scoring weights for your ICP  
- [ ] Keep HITL on for stage changes  
- [ ] Store CRM tokens in a secret manager  
- [ ] Back up `data/audit` and `data/pipeline`  
- [ ] Restrict CORS to trusted origins  

---

## Project structure

```
agents/pipeline-forge/
  config.yaml              # scoring rules + CRM
  samples/pipeline.json
  prompts/                 # scorer, prioritizer, risk, crm_mapper, insights
  src/
    agents/
    api/
    integrations/crm.py    # local · hubspot · salesforce
    memory/playbook.py
    services/              # audit, usage, hitl, store
    orchestrator.py
    main.py
    cli.py
  static/dashboard/
  static/widget/embed.js
  scripts/smoke_test.py
  README.md
```

Product page: **`/pipeline-forge`**.

---

## Safety

CRM stage changes and task writes default to **HITL approval**. Publishing CRM updates while `pending_review` is blocked unless approved. Local backend never calls external CRM APIs without credentials.

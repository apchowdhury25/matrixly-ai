# Matrixly MeetWise

**Marketplace tile:** MEET · **Domain:** Meetings / Sales / Ops  
**Embeddable AI agent** that captures meeting outcomes: summaries, decisions, action items, CRM updates, recap emails, and follow-up flags.

## Pipeline

```
Transcript upload (Zoom / Teams / Meet export)
  → Summarizer (decisions + discussion)
  → Action extractor (owners + deadlines)
  → CRM mapper (Salesforce-shaped tasks / notes / opportunity)
  → Recap email draft
  → HITL review → apply CRM + log/send email
```

Stack: **Python + FastAPI**, optional Grok, local CRM JSON/CSV, dark Matrixly dashboard.

---

## Quick start

```powershell
cd agents/meet-wise
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
| http://localhost:8793/v1/health | Health |
| http://localhost:8793/static/dashboard/index.html | Meeting dashboard |
| http://localhost:8793/docs | OpenAPI |

Default port: **8793**.

### `.env`

```env
MEETWISE_API_KEY=your-admin-secret
MEETWISE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=                 # optional smarter extraction
MEETING_BACKEND=upload
CRM_BACKEND=local
EMAIL_BACKEND=log
CORS_ORIGINS=http://localhost:8080,https://matrixly.world
```

---

## CRM mapping instructions

Edit **`config.yaml`** → `crm:`:

```yaml
crm:
  backend: local
  opportunity_default_stage: "Qualification"
  task_status: "Not Started"
  task_priority: "Normal"
  owner_map:
    Alex: "alex@yourco.com"
    Jordan: "jordan@acme.com"
    Sam: "sam@acme.com"
  opportunity_keywords:
    - deal
    - proposal
    - pilot
    - contract
```

### What gets written (local backend)

| File | Contents |
|------|----------|
| `data/crm/opportunities.json` | Salesforce-shaped opportunity fields |
| `data/crm/tasks.json` | Tasks from action items |
| `data/crm/notes.json` | Meeting notes |
| `data/crm/tasks.csv` | Spreadsheet-friendly task export |

Approve HITL to apply CRM writes. Exports also land in `data/exports/<meeting_id>/`.

---

## Transcript inputs

### Upload (recommended MVP)

- Paste text in the dashboard, or  
- Upload `.txt` / `.md` / `.vtt` / `.srt`, or  
- `python -m src.cli process path/to/transcript.txt`

### Zoom / Teams / Google

Config stubs in `.env` (`ZOOM_*`, `TEAMS_*`, `GOOGLE_*`). Production OAuth is optional; for day-to-day use **export transcript → upload**. See `src/integrations/transcripts.py`.

---

## Recap emails

- Default `EMAIL_BACKEND=log` writes `data/emails/<id>_recap.json`  
- Set `EMAIL_BACKEND=smtp` + SMTP env vars to send for real  

HITL approval applies CRM **and** finalizes recap send/log.

---

## Embed on matrixly.world

```html
<iframe
  src="https://YOUR_MEETWISE_HOST/static/dashboard/index.html"
  title="MeetWise"
  style="width:100%;min-height:800px;border:1px solid #1e2a3a;border-radius:12px;">
</iframe>

<script
  src="https://YOUR_MEETWISE_HOST/static/widget/embed.js"
  data-api="https://YOUR_MEETWISE_HOST"
  async>
</script>
```

---

## CLI

```text
python -m src.cli status
python -m src.cli demo
python -m src.cli process samples/demo_transcript.txt
python -m src.cli list
python -m src.cli pending
python -m src.cli approve --id hitl_...
python -m src.cli usage
python -m src.cli serve --port 8793
```

---

## Deployment (VPS)

```bash
cd agents/meet-wise
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --host 127.0.0.1 --port 8793
```

**Docker:**

```bash
docker build -t meet-wise .
docker run -d -p 8793:8793 --env-file .env -v $PWD/data:/app/data meet-wise
```

---

## Project layout

```
agents/meet-wise/
├── config.yaml              # CRM owner_map, HITL, backends
├── samples/demo_transcript.txt
├── prompts/                 # summarizer, actions, crm, recap
├── static/dashboard/        # embeddable UI
├── scripts/smoke_test.py
└── src/
    ├── main.py
    ├── orchestrator.py
    ├── agents/
    ├── integrations/        # transcripts, crm, email
    ├── services/
    └── api/
```

Product page: **`/meet-wise`** (`meet-wise/index.html`).

---

## License

Same as parent Matrixly repository (MIT).

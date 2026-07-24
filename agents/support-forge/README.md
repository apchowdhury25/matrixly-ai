# Matrixly SupportForge

**Marketplace tile:** SUPP · **Domain:** Customer Support / Ops  
**Embeddable AI agent** for end-to-end SMB support: chat widget, email & form ingest, knowledge-grounded answers, human-in-the-loop, tickets, audit, and usage/cost tracking.

SupportForge runs a multi-agent pipeline:

1. **Triage Agent** — urgency, sentiment, topic, PII flags  
2. **Knowledge Retriever** — answers from *your* docs (markdown, Notion sync, uploads)  
3. **Responder** — professional drafts / auto-resolve common queries  
4. **Escalation Manager** — full-context handoff + HITL queue  

Stack: **Python + FastAPI**, Grok (xAI) optional, local TF-IDF knowledge index (no GPU), dark neon embed widget.

---

## What you get

| Capability | Details |
|------------|---------|
| Channels | Website chat widget, form webhook, email webhook / IMAP poll |
| Knowledge | Drop files in `knowledge/`, Notion sync, or admin upload |
| HITL | Approve/reject external actions (send email, publish reply) |
| Tickets | Local Zendesk-style JSON store + optional Zendesk API |
| CRM-lite | Auto contact JSON/CSV on ticket create |
| Audit | JSONL event log with light secret redaction |
| Billing prep | Token + estimated USD cost per turn |
| Admin UI | `/static/admin/index.html` escalations & approvals |
| Demo mode | Works **without** `XAI_API_KEY` using FAQ retrieval |

---

## Quick start

### 1. Environment

```powershell
cd agents/support-forge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

```env
SUPPORTFORGE_API_KEY=your-admin-secret
SUPPORTFORGE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=          # optional — enables smarter triage/replies
CORS_ORIGINS=http://localhost:8080,http://localhost:8787,https://matrixbazaar.com,https://www.matrixbazaar.com
```

### 2. Index knowledge & smoke test

```powershell
python -m src.cli seed
python scripts/smoke_test.py
python -m src.cli demo
```

### 3. Run the API

```powershell
python -m src.cli serve
# → http://0.0.0.0:8787
```

| URL | Purpose |
|-----|---------|
| http://localhost:8787/v1/health | Health check |
| http://localhost:8787/static/admin/index.html | Admin dashboard |
| http://localhost:8787/static/widget/embed.js | Widget loader |
| http://localhost:8787/docs | OpenAPI (FastAPI) |

Admin login uses `SUPPORTFORGE_API_KEY` (header `X-API-Key`, or the login form).

---

## Connect a business knowledge base

### Option A — Files (easiest for non-technical owners)

1. Open the `knowledge/` folder  
2. Add or edit `.md` / `.txt` files (pricing, hours, policies, FAQ, troubleshooting)  
3. Run:

```powershell
python -m src.cli seed
```

### Option B — Admin upload API

```bash
curl -X POST http://localhost:8787/v1/kb/upload \
  -H "X-API-Key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Returns\",\"content\":\"Refunds within 14 days...\",\"source\":\"upload\"}"
```

### Option C — Notion

1. Create an internal Notion integration and share your KB database  
2. Set in `.env`:

```env
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
```

3. Sync + reindex:

```bash
curl -X POST http://localhost:8787/v1/kb/notion-sync -H "X-API-Key: your-admin-secret"
```

Or export Notion pages as Markdown into `knowledge/` and `seed`.

### Option D — Website / PDF content

- Paste key website copy into markdown under `knowledge/`  
- For PDFs: convert to text/markdown first (Phase 2 can add PDF extractors)

Tune thresholds in `config.yaml`:

```yaml
thresholds:
  auto_resolve: 0.75
  draft_for_approval: 0.45
```

---

## Embed on matrixbazaar.com (or any site)

### Script embed (recommended)

Replace `YOUR_SUPPORTFORGE_HOST` and the widget key with production values.

```html
<!-- Matrixly SupportForge — place before </body> on matrixbazaar.com -->
<script
  src="https://YOUR_SUPPORTFORGE_HOST/static/widget/embed.js"
  data-api="https://YOUR_SUPPORTFORGE_HOST"
  data-key="pk_live_your-site-key"
  data-title="Support"
  async>
</script>
```

**Local test example:**

```html
<script
  src="http://localhost:8787/static/widget/embed.js"
  data-api="http://localhost:8787"
  data-key="pk_live_change-me"
  data-title="Support"
  async>
</script>
```

Ensure `CORS_ORIGINS` includes `https://matrixbazaar.com` and `https://www.matrixbazaar.com`.

### Iframe embed

```html
<iframe
  src="https://YOUR_SUPPORTFORGE_HOST/static/widget/chat-panel.html?api=https://YOUR_SUPPORTFORGE_HOST&key=pk_live_your-site-key&title=Support"
  title="Support chat"
  style="position:fixed;right:16px;bottom:16px;width:400px;height:560px;border:0;z-index:9999;">
</iframe>
```

---

## Integrations

### Website form → webhook

```bash
curl -X POST http://localhost:8787/v1/webhooks/form \
  -H "X-API-Key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Alex\",\"email\":\"alex@acme.com\",\"subject\":\"Pricing\",\"message\":\"What does Growth plan cost?\"}"
```

### Email webhook (Gmail Apps Script / forwarder)

POST normalized JSON to `/v1/webhooks/email`:

```json
{
  "from_email": "customer@example.com",
  "from_name": "Customer",
  "subject": "Where is my order?",
  "body": "Order ORD-12345 still not shipped."
}
```

### IMAP poll (Hostinger / Gmail app password)

```env
EMAIL_BACKEND=imap
EMAIL_IMAP_HOST=imap.hostinger.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_USER=support@yourdomain.com
EMAIL_IMAP_PASSWORD=********
```

```powershell
python -m src.cli ingest-email
# or
python scripts/ingest_email_once.py
```

### Tickets

- **Default:** JSON files under `data/tickets/` (Zendesk-shaped fields)  
- **CRM export:** `data/crm/contacts.json` + `contacts.csv`  
- **Zendesk (optional):** set `ZENDESK_SUBDOMAIN`, `ZENDESK_EMAIL`, `ZENDESK_API_TOKEN` — tickets are also pushed via REST when configured  

### Follow-ups

Escalations with a customer email schedule a 24h follow-up file. Process due items:

```powershell
python -m src.cli followups
```

---

## CLI reference

```text
python -m src.cli status
python -m src.cli seed
python -m src.cli demo
python -m src.cli chat "What are your hours?"
python -m src.cli pending
python -m src.cli approve --id hitl_...
python -m src.cli reject --id hitl_...
python -m src.cli usage
python -m src.cli followups
python -m src.cli ingest-email
python -m src.cli serve --port 8787
```

---

## Decision rules (defaults)

| Condition | Action |
|-----------|--------|
| confidence ≥ 0.75, topic allowlisted, chat | Auto-reply |
| 0.45 ≤ confidence < 0.75 | Draft → HITL |
| confidence < 0.45, critical urgency, or legal/fraud keywords | Escalate |
| Email send / external writes | HITL unless `HITL_MODE=off` (demo only) |

Every turn writes **audit** events and **usage** (tokens + estimated USD).

---

## Deployment

> The Matrixly **marketing site** is static (Hostinger). SupportForge is a **separate Python service** (VPS recommended).

### VPS (production path)

```bash
cd agents/support-forge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill secrets
python -m src.cli seed
# run under process manager
uvicorn src.main:app --host 0.0.0.0 --port 8787
```

**systemd unit (example):**

```ini
[Unit]
Description=Matrixly SupportForge
After=network.target

[Service]
WorkingDirectory=/opt/support-forge
EnvironmentFile=/opt/support-forge/.env
ExecStart=/opt/support-forge/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8787
Restart=always

[Install]
WantedBy=multi-user.target
```

Put **Caddy** or **nginx** in front with TLS, reverse-proxy to `127.0.0.1:8787`. Point the matrixbazaar.com embed `data-api` at that HTTPS host.

### Docker (optional)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8787
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8787"]
```

```bash
docker build -t support-forge .
docker run -d -p 8787:8787 --env-file .env -v $PWD/data:/app/data -v $PWD/knowledge:/app/knowledge support-forge
```

### Serverless note

Session files + local vector index fit a **VPS** better. For AWS Lambda / Cloud Run without disks, move `data/` to S3/Postgres and use a managed vector DB (Phase 2).

---

## Security checklist (SMB)

- [ ] Change default `SUPPORTFORGE_API_KEY` and `SUPPORTFORGE_WIDGET_KEY`  
- [ ] Never commit `.env`  
- [ ] Restrict `CORS_ORIGINS` to your real domains  
- [ ] Expose only HTTPS publicly; keep admin key off the widget  
- [ ] Widget key is **semi-public** (chat only) — rotate if abused  
- [ ] Keep `HITL_MODE=external_only` (or `always`) in production  
- [ ] Review escalations daily in admin UI  

---

## Project layout

```
agents/support-forge/
├── config.yaml          # Business knobs
├── knowledge/           # Your FAQs & policies
├── prompts/             # Sub-agent prompts
├── static/widget/       # embed.js + CSS
├── static/admin/        # Dashboard
├── scripts/             # seed, smoke, demo, email
└── src/
    ├── main.py          # FastAPI app
    ├── orchestrator.py  # Pipeline
    ├── agents/          # Triage, Knowledge, Responder, Escalation
    ├── memory/          # Sessions + vector index
    ├── integrations/    # Tickets, email, Notion, forms
    ├── services/        # Audit, usage, HITL, follow-ups
    └── api/             # HTTP routes
```

---

## Product page

Marketing / deploy docs on the Matrixly site: **`support-forge.html`** (repo root). Catalog card on **`agents.html`**.

---

## License

Same as parent Matrixly repository (MIT).

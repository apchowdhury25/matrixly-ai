# Matrixly Starter Pack

**Support · Bookings · Invoices — three production agents, one dashboard.**

The Starter Pack is Matrixly’s SMB-ready bundle for day-one operations:

| Agent | Role |
|--------|------|
| **[SupportForge](../support-forge/)** | Customer support triage, knowledge answers, HITL escalation |
| **[BookWise](../book-wise/)** | Appointment booking, calendar sync, reminders |
| **[InvoiceForge](../invoice-forge/)** | Invoice OCR/extract, AR posting, exceptions, reminders |
| **Starter Dashboard** | Unified overview, toggles, activity, analytics, embed codes |

Each agent remains a modular FastAPI service (Crew/LangGraph-style crews inside) so you can scale or sell them independently. This pack **orchestrates** them: health, enable/disable, unified logs, analytics hooks, and a professional control plane for non-technical owners.

Default dashboard port: **8800**.

---

## Value for SMBs

- One login surface for support, scheduling, and invoices  
- Human approval on sensitive actions (emails, calendar writes, accounting posts)  
- Audit trails + usage hooks for future SaaS billing  
- Embed chat/booking widgets on your website in minutes  
- Docker Compose to run the full stack on a VPS  

---

## Project structure

```
agents/
  support-forge/          # Agent 1 (port 8787)
  book-wise/              # Agent 2 (port 8790)
  invoice-forge/          # Agent 3 (port 8791)
  starter-pack/           # Unified gateway + dashboard (port 8800)
    src/
      adapters/           # HTTP + local-data adapters
      api/                # Pack REST API
      pack.py             # Registry & overview
      services/           # settings, audit, usage
    static/dashboard/     # Starter UI
    static/widget/        # Pack embed launcher
    docker-compose.yml    # Full stack
    README.md
starter-pack/index.html   # Marketing product page (site)
```

---

## Quick start (local)

### 1) Install each agent (once)

```powershell
# SupportForge
cd agents/support-forge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/seed_kb.py   # if available
python scripts/smoke_test.py

# BookWise
cd ..\book-wise
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py

# InvoiceForge
cd ..\invoice-forge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
```

### 2) Start the three agents (3 terminals)

```powershell
cd agents/support-forge ; .\.venv\Scripts\Activate.ps1 ; python -m src.cli serve
# → http://127.0.0.1:8787

cd agents/book-wise ; .\.venv\Scripts\Activate.ps1 ; python -m src.cli serve
# → http://127.0.0.1:8790

cd agents/invoice-forge ; .\.venv\Scripts\Activate.ps1 ; python -m src.cli serve
# → http://127.0.0.1:8791
```

### 3) Start the Starter Pack dashboard

```powershell
cd agents/starter-pack
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Open **http://localhost:8800** (dashboard).  
Default admin key: `change-me-admin-key` (from `.env` → `STARTER_API_KEY`).

> **Offline demo:** If an agent process is down, the pack still reads sibling `agents/*/data` folders for metrics and activity (`LOCAL_DATA_FALLBACK=true`).

---

## Docker Compose (recommended for production VPS)

From `agents/starter-pack`:

```bash
# Create .env files for each agent + pack first
cp .env.example .env
cp ../support-forge/.env.example ../support-forge/.env
cp ../book-wise/.env.example ../book-wise/.env
cp ../invoice-forge/.env.example ../invoice-forge/.env

docker compose up --build -d
```

| Service | URL |
|---------|-----|
| Starter Dashboard | http://localhost:8800 |
| SupportForge | http://localhost:8787 |
| BookWise | http://localhost:8790 |
| InvoiceForge | http://localhost:8791 |

Put Caddy or nginx TLS in front of 8800 (and optionally only expose the pack + widgets).

---

## Configure each agent

### SupportForge — knowledge & channels

1. Edit `agents/support-forge/knowledge/*.md` (FAQ, hours, policies, pricing).  
2. Or upload via SupportForge admin / KB API.  
3. Optional Notion: set Notion token in SupportForge `.env`.  
4. Email: configure IMAP / webhook ingest (see SupportForge README).  
5. HITL: leave `HITL_MODE=external_only` so external replies need approval.

### BookWise — calendar & booking rules

1. Set timezone and buffers in `agents/book-wise/config.yaml`.  
2. Calendar backend: local busy file, Google Calendar credentials, or Outlook.  
3. Confirmations/reminders: email backend in BookWise `.env`.  
4. Embed the booking widget on your site (snippet below).

### InvoiceForge — inbox & accounting

1. Drop invoices into `agents/invoice-forge/data/uploads` or watch email.  
2. Set `ACCOUNTING_BACKEND=local|quickbooks|xero` in InvoiceForge `.env`.  
3. Review exceptions in InvoiceForge dashboard HITL queue.  
4. Aging report via InvoiceForge admin API.

### Starter Pack — connections panel

Use **Connections** in the dashboard to store *notes* for your team (which mailbox, which QB company). **Secrets stay in each agent’s `.env`**, not in the browser.

---

## Dashboard features

- **Overview** — online/offline, KPIs, enable/disable  
- **Agents** — metrics, HITL count, deep links to each panel  
- **Activity** — unified audit stream  
- **Analytics** — tickets, bookings, invoices, pending reviews  
- **Connections** — Gmail, calendar, QuickBooks, knowledge notes  
- **Embed** — copy-paste widget code  

API: `GET /v1/overview` with header `X-API-Key`.

---

## Embed codes

Replace hosts/keys for production.

### SupportForge chat widget

```html
<script
  src="http://127.0.0.1:8787/static/widget/embed.js"
  data-api="http://127.0.0.1:8787"
  data-key="pk_live_your-site-key"
  async>
</script>
```

### BookWise booking widget

```html
<script
  src="http://127.0.0.1:8790/static/widget/embed.js"
  data-api="http://127.0.0.1:8790"
  data-key="pk_live_your-site-key"
  async>
</script>
```

### InvoiceForge panel (iframe)

```html
<iframe
  src="http://127.0.0.1:8791/static/dashboard/index.html"
  title="InvoiceForge"
  style="width:100%;min-height:700px;border:1px solid #1e2a3a;border-radius:12px;">
</iframe>
```

### Starter Pack dashboard / launcher

```html
<iframe
  src="http://127.0.0.1:8800/static/dashboard/index.html"
  title="Matrixly Starter Pack"
  style="width:100%;min-height:800px;border:1px solid #1e2a3a;border-radius:12px;">
</iframe>

<script
  src="http://127.0.0.1:8800/static/widget/embed-pack.js"
  data-api="http://127.0.0.1:8800"
  async>
</script>
```

Live snippets also available from `GET /v1/embed-snippets` (authenticated).

---

## Adding a future agent to the pack

1. Ship the new agent as `agents/<name>/` with `/v1/health`, `/v1/admin/status`, `/v1/admin/audit`, `/v1/admin/usage`, `/v1/admin/hitl`.  
2. Add an adapter under `starter-pack/src/adapters/`.  
3. Register it in `config.yaml` → `agents:` and `.env` runtime URL.  
4. Wire it in `pack.py` registry.  
5. Optionally add Docker Compose service.  

No need to rewrite the dashboard — cards are driven by the overview API.

---

## Security & privacy

- Separate API keys per agent + pack  
- Widget keys for public embed surfaces only  
- HITL for external side effects  
- Append-only audit logs; redact secrets in agent audit helpers  
- Do not commit `.env`; use secret manager in production  
- Prefer private Docker network; expose only dashboard + widget ports  
- Customer data stays in each agent’s `data/` volume  

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| All agents “offline” | Start each `python -m src.cli serve`; check ports 8787/8790/8791 |
| Metrics empty | Run smoke tests once to seed data; enable `LOCAL_DATA_FALLBACK` |
| 401 on dashboard | Set `STARTER_API_KEY` and paste into the key field |
| Widget CORS errors | Add site origin to each agent’s `CORS_ORIGINS` |
| Compose DNS issues | Use service names (`http://support-forge:8787`) inside Compose network |

### Scaling notes

- Scale agents independently (more replicas behind a load balancer).  
- Keep the pack as a thin control plane (no heavy AI in the pack process).  
- Move JSONL storage to Postgres/S3 when multi-tenant SaaS billing goes live (usage hooks already emit events).  

---

## CLI

```powershell
python -m src.cli status
python -m src.cli overview
python -m src.cli serve --port 8800
```

---

## Product page

Site page: **`/starter-pack`** · Catalog: Agents marketplace.

Deep docs for each agent:

- [SupportForge README](../support-forge/README.md)  
- [BookWise README](../book-wise/README.md)  
- [InvoiceForge README](../invoice-forge/README.md)  

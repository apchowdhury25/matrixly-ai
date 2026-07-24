# Matrixly BookWise

**Marketplace tile:** BOOK · **Domain:** Scheduling / Ops  
**Embeddable AI agent** that fully manages appointment booking for SMBs: chat/email/form intake, real-time availability, confirmations, reminders, reschedule/cancel, calendar sync, and HITL for edge cases.

## Multi-agent pipeline

1. **Intent Agent** — book / availability / reschedule / cancel / status  
2. **Availability Agent** — business hours, buffers, timezone, optimal slots  
3. **Booking Agent** — intake, confirm, calendar write, CRM-lite  
4. **Reminder service** — smart 24h + 2h reminders to reduce no-shows  
5. **HITL** — VIP / legal / after-hours / group bookings need human approve  

Stack: **Python + FastAPI**, optional Grok (xAI), local calendar (default) + Google Calendar / Calendly-style hooks.

---

## Quick start

```powershell
cd agents/book-wise
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
| http://localhost:8790/v1/health | Health |
| http://localhost:8790/static/admin/index.html | Admin (API key) |
| http://localhost:8790/static/widget/embed.js | Widget loader |
| http://localhost:8790/docs | OpenAPI |

Default port: **8790** (SupportForge uses 8787).

### `.env` essentials

```env
BOOKWISE_API_KEY=your-admin-secret
BOOKWISE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=          # optional
CORS_ORIGINS=http://localhost:8080,https://matrixly.world,https://www.matrixly.world
CALENDAR_BACKEND=local
TIMEZONE=America/Chicago
```

---

## Configure business hours & rules

Edit **`config.yaml`** (non-technical friendly):

```yaml
business_hours:
  monday: { start: "09:00", end: "17:00" }
  # ... set null for closed days

booking:
  default_duration_minutes: 30
  buffer_before_minutes: 10
  buffer_after_minutes: 10
  min_notice_hours: 2
  max_days_ahead: 14

services:
  - id: consult
    name: Consultation
    duration_minutes: 30

reminders:
  hours_before: [24, 2]
```

Then restart the server. No reindex step required.

---

## Calendar integrations

| Backend | How |
|---------|-----|
| **local** (default) | JSON busy blocks + booking store — works offline, production-ready for single location |
| **google** | Set `CALENDAR_BACKEND=google`, place OAuth `token.json` (and optional `credentials.json`). FreeBusy + event create/delete when libraries installed |
| **calendly** | Set `CALENDLY_API_TOKEN` + `CALENDLY_EVENT_TYPE_URI` for Calendly-style API checks |

Optional packages for live Google:

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

CRM-lite: every booking upserts `data/crm/contacts.json` + `contacts.csv`.

---

## Embed on matrixly.world

```html
<!-- Matrixly BookWise — place before </body> on matrixly.world -->
<script
  src="https://YOUR_BOOKWISE_HOST/static/widget/embed.js"
  data-api="https://YOUR_BOOKWISE_HOST"
  data-key="pk_live_your-site-key"
  data-title="Book with us"
  async>
</script>
```

**Local test:**

```html
<script
  src="http://localhost:8790/static/widget/embed.js"
  data-api="http://localhost:8790"
  data-key="pk_live_change-me"
  data-title="Book with us"
  async>
</script>
```

**Iframe:**

```html
<iframe
  src="https://YOUR_BOOKWISE_HOST/static/widget/chat-panel.html?api=https://YOUR_BOOKWISE_HOST&key=pk_live_your-site-key"
  title="Booking chat"
  style="position:fixed;right:16px;bottom:16px;width:400px;height:580px;border:0;z-index:9999;">
</iframe>
```

Ensure `CORS_ORIGINS` includes `https://matrixly.world` and `https://www.matrixly.world`.

---

## Channels

### Chat widget
Primary path — proposes clickable slots, books with name/email intake.

### Form webhook

```bash
curl -X POST http://localhost:8790/v1/webhooks/form \
  -H "X-API-Key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Alex\",\"email\":\"alex@acme.com\",\"message\":\"Need a consultation next week\"}"
```

### Email webhook

```bash
curl -X POST http://localhost:8790/v1/webhooks/email \
  -H "X-API-Key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d "{\"from_email\":\"alex@acme.com\",\"subject\":\"Book me\",\"body\":\"Friday afternoon consult please\"}"
```

### Structured API

- `GET /v1/availability?service_id=consult`
- `POST /v1/bookings`
- `POST /v1/bookings/reschedule`
- `POST /v1/bookings/cancel`

---

## CLI

```text
python -m src.cli status
python -m src.cli availability
python -m src.cli demo
python -m src.cli chat "Book a demo tomorrow morning"
python -m src.cli upcoming
python -m src.cli pending
python -m src.cli reminders
python -m src.cli usage
python -m src.cli serve --port 8790
```

Process due reminders (cron every 15 min):

```bash
python -m src.cli reminders
```

---

## Deployment (VPS)

```bash
cd agents/book-wise
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --host 127.0.0.1 --port 8790
```

TLS reverse proxy (Caddy/nginx) → public HTTPS host used in embed `data-api`.

**Docker:**

```bash
docker build -t book-wise .
docker run -d -p 8790:8790 --env-file .env -v $PWD/data:/app/data book-wise
```

Marketing site stays static; BookWise API runs on a VPS (same pattern as SupportForge).

---

## Security checklist

- [ ] Change `BOOKWISE_API_KEY` and `BOOKWISE_WIDGET_KEY`
- [ ] Never commit `.env` / OAuth tokens
- [ ] Restrict `CORS_ORIGINS` to real domains
- [ ] Keep HITL on for edge cases in production
- [ ] Widget key is chat-only (semi-public)

---

## Project layout

```
agents/book-wise/
├── config.yaml
├── prompts/
├── static/widget/     # embed.js + CSS
├── static/admin/      # upcoming bookings dashboard
├── scripts/smoke_test.py
└── src/
    ├── main.py
    ├── orchestrator.py
    ├── agents/        # intent, availability, booking
    ├── integrations/  # calendar (local/google/calendly)
    ├── services/      # bookings, reminders, HITL, audit, usage
    └── api/
```

Product page: **`book-wise.html`** (repo root).

---

## License

Same as parent Matrixly repository (MIT).

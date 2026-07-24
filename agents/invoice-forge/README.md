# Matrixly InvoiceForge

**Marketplace tile:** INVC · **Domain:** Finance / AP / AR  
**Invoice processing & accounts receivable agent** for SMBs: watch inbox/uploads, extract with vision or parsers, validate, post to QuickBooks/Xero/CSV, flag exceptions (HITL), send AR reminders, and generate aging reports.

## Workflow

```
Watch inbox / uploads / API
        ↓
  Extract (vision OCR + LLM / rules)
        ↓
  Validate (totals, duplicates, PO, confidence)
        ↓
   ┌─ Exception? → HITL queue → approve/reject
   └─ OK → Post to CSV | QuickBooks | Xero
        ↓
  Schedule AR reminders + usage/audit logs
        ↓
  Dashboard review + AR reports
```

### Specialized agents (CrewAI/LangGraph-style)

| Agent | Role |
|-------|------|
| **Extract** | Vision model (Grok vision) or text LLM / regex OCR fallback |
| **Validate** | Business rules, duplicates, high-amount & keyword exceptions |
| **Post** | QuickBooks Online / Xero stubs or CSV export |
| **Remind** | AR follow-ups after due date |
| **Report** | Status counts + aging buckets |

Stack: **Python + FastAPI**, optional Grok text/vision, dark Matrixly dashboard UI.

---

## Quick start

```powershell
cd agents/invoice-forge
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
| http://localhost:8791/v1/health | Health |
| http://localhost:8791/static/dashboard/index.html | Review dashboard |
| http://localhost:8791/docs | OpenAPI |

Default port: **8791** (BookWise 8790, SupportForge 8787).

### `.env`

```env
INVOICEFORGE_API_KEY=your-admin-secret
INVOICEFORGE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=                 # optional — smarter extract + vision
XAI_VISION_MODEL=grok-2-vision-1212
ACCOUNTING_BACKEND=csv       # csv | quickbooks | xero
CORS_ORIGINS=http://localhost:8080,https://matrixly.world
```

---

## Configure rules

Edit **`config.yaml`**:

```yaml
validation:
  confidence_threshold: 0.75
  max_amount: 500000
  check_duplicates: true

exceptions:
  auto_flag_high_amount: 25000
  missing_po_is_exception: true
  keywords: [rush, legal, disputed, wire fraud]

ar:
  reminder_days_after_due: [1, 7, 14]

accounting:
  backend: csv
```

---

## Channels

### 1. Dashboard paste / upload
Open `/static/dashboard/index.html` — paste text or upload `.txt` / image (PNG/JPG) for vision extract when API key is set.

### 2. Watch uploads folder

```powershell
# Drop files into data/uploads/
python -m src.cli watch
# or POST /v1/watch/uploads
```

### 3. Email webhook / IMAP

```bash
curl -X POST http://localhost:8791/v1/webhooks/email \
  -H "X-API-Key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d "{\"from_email\":\"vendor@acme.com\",\"subject\":\"Invoice INV-1\",\"body\":\"...\"}"
```

Set `EMAIL_BACKEND=imap` for one-shot inbox poll via `watch`.

### 4. Process CLI

```powershell
python -m src.cli process samples\invoice_acme.txt
python -m src.cli process path\to\scan.png   # vision when XAI_API_KEY set
```

---

## Accounting backends

| Backend | Behavior |
|---------|----------|
| **csv** (default) | Appends `data/exports/invoices.csv` + per-invoice JSON — production-ready offline |
| **quickbooks** | Posts Bill via QBO API when tokens set; falls back to CSV |
| **xero** | Posts ACCPAY invoice when tokens set; falls back to CSV |

```env
ACCOUNTING_BACKEND=quickbooks
QBO_ACCESS_TOKEN=...
QBO_REALM_ID=...
```

---

## Embeddable dashboard (matrixly.world)

Full review UI (not a chat bubble) — open or iframe:

```html
<iframe
  src="https://YOUR_INVOICEFORGE_HOST/static/dashboard/index.html"
  title="InvoiceForge"
  style="width:100%;min-height:720px;border:1px solid #1e2a3a;border-radius:12px;">
</iframe>
```

Launcher button:

```html
<script
  src="https://YOUR_INVOICEFORGE_HOST/static/widget/embed.js"
  data-api="https://YOUR_INVOICEFORGE_HOST"
  async>
</script>
```

---

## CLI

```text
python -m src.cli status
python -m src.cli demo
python -m src.cli process <file>
python -m src.cli watch
python -m src.cli list
python -m src.cli exceptions
python -m src.cli pending
python -m src.cli approve --id hitl_...
python -m src.cli reject --id hitl_...
python -m src.cli reminders
python -m src.cli report
python -m src.cli usage
python -m src.cli serve --port 8791
```

Cron examples:

```bash
# Every 15 min: process uploads + due AR reminders
python -m src.cli watch
python -m src.cli reminders
```

---

## Deployment (VPS)

```bash
cd agents/invoice-forge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --host 127.0.0.1 --port 8791
```

**Docker:**

```bash
docker build -t invoice-forge .
docker run -d -p 8791:8791 --env-file .env \
  -v $PWD/data:/app/data -v $PWD/samples:/app/samples invoice-forge
```

TLS reverse proxy recommended. Marketing site stays static; InvoiceForge is a separate service.

---

## Security

- Change default API keys  
- Never commit `.env` or accounting tokens  
- Restrict CORS  
- Keep HITL for exceptions in production  
- Vision images stay on your server under `data/uploads/`  

---

## Project layout

```
agents/invoice-forge/
├── config.yaml
├── samples/                 # Demo invoices
├── prompts/extract.md
├── static/dashboard/        # Review UI
├── static/widget/embed.js
├── scripts/smoke_test.py
└── src/
    ├── main.py
    ├── orchestrator.py
    ├── agents/              # extract, validate, post, report
    ├── integrations/        # accounting, inbox
    ├── services/            # store, HITL, reminders, audit, usage
    └── api/
```

Product page: **`invoice-forge.html`** (repo root).

---

## License

Same as parent Matrixly repository (MIT).

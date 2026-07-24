# Matrixly DocForge

**Marketplace tile:** DOC · **Domain:** Sales / Legal / Ops  
**Embeddable AI agent** that drafts professional SMB business documents: proposals, quotes, contracts, and reports — with approved templates, brand/pricing/legal rules, versioned HITL approval, and multi-format export.

## Pipeline (CrewAI / LangGraph-style)

```
Client data (manual · form JSON · CRM)
  → Intake (normalize brief + line items)
  → Legal assembler (approved terms)
  → Drafter (template + brand fill)
  → Brand/compliance check
  → Export (MD · HTML · TXT · PDF)
  → HITL approval → send/status log
```

Stack: **Python + FastAPI**, optional Grok, markdown templates, dark document workspace UI.

Default port: **8796**.

---

## Quick start

```powershell
cd agents/doc-forge
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
| http://localhost:8796/v1/health | Health |
| http://localhost:8796/static/workspace/index.html | Document workspace |
| http://localhost:8796/docs | OpenAPI |

### `.env`

```env
DOCFORGE_API_KEY=your-admin-secret
DOCFORGE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=
HITL_AUTO_APPROVE=false
CRM_BACKEND=local
CORS_ORIGINS=http://localhost:8080,https://matrixly.world
```

---

## Template management

### Built-in templates

Located in `templates/`:

| File | Use |
|------|-----|
| `proposal.md` | Sales proposals |
| `quote.md` | Price quotations |
| `contract.md` | Simple service agreements |
| `report.md` | Client reports |

Placeholders: `{{title}}`, `{{client_name}}`, `{{pricing_table}}`, `{{legal_block}}`, `{{footer}}`, etc.

### Upload / replace a template

**CLI-less (API):**

```bash
curl -X POST "http://localhost:8796/v1/templates/my-proposal" \
  -H "X-API-Key: change-me-admin-key" \
  -F "content@./my-proposal.md"
```

Or drop a `.md` file into `templates/` and restart (or call list to confirm).

### Brand guidelines & clauses

| Path | Purpose |
|------|---------|
| `brand/guidelines.md` | Voice, structure, pricing rules |
| `data/memory/notes.json` | Operator notes (`POST /v1/brand/notes`) |
| `data/memory/clauses.json` | Approved legal clauses (`POST /v1/brand/clauses`) |
| `config.yaml` → `pricing.catalog` | SKU catalog + max discount |

---

## Export options

On each draft (and re-export), DocForge writes under `data/exports/<doc_id>/v<version>/`:

| Format | File |
|--------|------|
| Markdown | `*.md` (editable) |
| HTML | `*.html` (print-ready branding) |
| Text | `*.txt` |
| PDF | `*.pdf` (lightweight text PDF, no extra deps) |
| Meta | `meta.json` |

Send is logged locally (`exports/<id>/send/*.json`) after approval — wire SMTP later if needed.

---

## API (high level)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/draft` | widget/API | Generate document |
| POST | `/v1/demo` | widget/API | Sample proposal |
| GET | `/v1/documents` | API | List documents |
| GET | `/v1/documents/{id}` | API | Document detail |
| GET | `/v1/documents/{id}/versions` | API | Version history |
| POST | `/v1/documents/{id}/export` | API | Re-export formats |
| POST | `/v1/documents/{id}/send` | API | Log send (post-approval) |
| GET | `/v1/templates` | API | List templates |
| POST | `/v1/templates/{id}` | API | Upload template |
| GET | `/v1/admin/hitl` | API | Pending approvals |
| POST | `/v1/admin/hitl/{id}/approve` | API | Approve |

Headers: `X-API-Key` or `X-Widget-Key`.

---

## CLI

```powershell
python -m src.cli status
python -m src.cli demo
python -m src.cli draft samples/client_brief.json
python -m src.cli templates
python -m src.cli pending
python -m src.cli approve --id hitl_…
python -m src.cli export --id doc_… --formats md,html,pdf
python -m src.cli send --id doc_…
python -m src.cli serve --port 8796
```

---

## Embed code

```html
<iframe
  src="https://YOUR_DOCFORGE_HOST/static/workspace/index.html"
  title="DocForge"
  style="width:100%;min-height:800px;border:1px solid #1e2a3a;border-radius:12px;"
></iframe>

<script
  src="https://YOUR_DOCFORGE_HOST/static/widget/embed.js"
  data-api="https://YOUR_DOCFORGE_HOST"
  async>
</script>
```

---

## Deployment

```powershell
cd agents/doc-forge
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8796
```

### Docker

```bash
docker build -t doc-forge .
docker run -d -p 8796:8796 --env-file .env -v $PWD/data:/app/data -v $PWD/templates:/app/templates doc-forge
```

### Production checklist

- [ ] Review `brand/guidelines.md` and legal defaults in `config.yaml`  
- [ ] Keep HITL on for customer-facing documents  
- [ ] Version templates under git or secure storage  
- [ ] Restrict CORS; rotate API keys  
- [ ] Back up `data/docs`, `data/versions`, `data/audit`  

---

## Project structure

```
agents/doc-forge/
  brand/guidelines.md
  templates/           # proposal, quote, contract, report
  config.yaml
  samples/client_brief.json
  prompts/             # intake, drafter, brand_check, legal
  src/
    agents/
    api/
    integrations/      # export + CRM client lookup
    memory/
    services/          # audit, usage, hitl, store, templates
    orchestrator.py
    main.py
    cli.py
  static/workspace/
  static/widget/embed.js
  scripts/smoke_test.py
  README.md
```

Product page: **`/doc-forge`**.

---

## Safety

Documents default to **pending_approval**. Sending while pending HITL is blocked. Pricing discounts above `pricing.default_discount_max_pct` are flagged for human review. Legal language is a commercial template — not a substitute for counsel on complex deals.

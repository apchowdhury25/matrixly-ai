# Matrixly – Agentic AI Automation Agency

**Matrixly** is the agentic AI marketplace for SMBs — ready-to-deploy agents that market, sell, ship, and run operations with human-in-the-loop controls.

This repository contains the public marketing site, agent catalog, integration directory, and **18 Python agent packages** under `agents/`.

## Short description

A production-facing static website plus local agent runtimes for:

| Agent | Purpose | Default port |
|--------|---------|----------------|
| **Lead Qualifier** | Score leads, enrich contacts, draft outreach sequences | CLI |
| **Email Assistant** | Inbox triage, drafts, urgent flags, daily brief | CLI |
| **CRM Assistant** | Contact updates, activities, pipeline hygiene (approve-to-write) | CLI |
| **Shipping Assistant** | ShipStation hub — track, exceptions, WISMO drafts | CLI |
| **SupportForge** | Embeddable AI support — chat widget, KB answers, HITL, tickets | **8787** |
| **BookWise** | Embeddable AI booking — availability, confirmations, reminders | **8790** |
| **InvoiceForge** | Invoice processing & AR — extract, validate, post, reminders | **8791** |
| **ContentForge** | Content creation & repurposing — SEO blogs, social, newsletters, ads | **8792** |
| **MeetWise** | Meeting outcomes — summaries, actions, CRM, recap emails | **8793** |
| **SocialForge** | Social content & engagement — posts, schedule, inbox, insights | **8794** |
| **PipelineForge** | Pipeline scoring & prioritization — fit, risk, CRM, health | **8795** |
| **DocForge** | Business documents — proposals, quotes, contracts, reports | **8796** |
| **ETF Analyzer** | Live free-market ETF analysis — yield, NAV, tax, Notion | **8797** |
| **SEOForge** | SEO & brand marketing for US SMBs — local SEO, content, keywords, ROI + HITL | **8798** |
| **Invoice Processor** | Pydantic AI multi-agent AP — extract, PO match, discrepancies, HITL | **8799** |
| **Starter Pack** | SupportForge + BookWise + InvoiceForge + unified dashboard | **8800** |
| **SEO-Bespoke** | Higher-tier SEO: business quiz → SEO profile → **custom agent code** (parallel graph) | **8801** |
| **Voice Receptionist** | Grok Voice (xAI Realtime) smoke harness; telephony next | CLI / smoke |

## Tech stack

| Layer | Technology |
|--------|------------|
| Site | HTML5, Tailwind CSS (CDN), vanilla JavaScript |
| Fonts | Open Sans (Google Fonts) |
| Agents | Python 3, FastAPI + CLI, optional Grok (xAI) |
| Voice | xAI Grok Voice / Realtime WebSocket (Voice Receptionist) |
| Runtime | Hermes Agent skills (optional) |
| Integrations | Gmail / Hostinger IMAP, ShipStation, Salesforce-shaped exports, Notion |
| Deploy | Static hosting (e.g. **Hostinger**) via `dist/` + `deploy` branch |

## How to run locally

### Website

```bash
# From the repo root
npm run build && npm start
# or (dev only)
python -m http.server 8080
```

Open (clean URLs — no `.html` in the path):

- Landing: http://localhost:8080/  
- Agents catalog: http://localhost:8080/agents  
- Integrations: http://localhost:8080/integrations  
- Pricing: http://localhost:8080/pricing  
- SEO-Bespoke product page: http://localhost:8080/seo-bespoke  

### Generic agent pattern

```powershell
cd agents/<agent-folder>
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # macOS / Linux
pip install -r requirements.txt
copy .env.example .env         # never commit .env
python scripts/smoke_test.py   # where present
python -m src.cli serve        # or demo / other CLI commands
```

Copy each agent’s `.env.example` to `.env` for live credentials. Put API keys only in `.env` — never in `.env.example` or commits.

### Shipping Assistant (example pilot)

```bash
cd agents/shipping-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.cli demo
```

## Deployment (Hostinger)

CI/CD publishes a clean `dist/` tree to the **`deploy`** branch (and optionally FTP).

```bash
npm run lint
npm run build
# GitHub Actions on main → deploy branch → Hostinger Git auto-deploy
```

Full guide: **[DEPLOYMENT.md](DEPLOYMENT.md)** (secrets, hPanel steps, manual deploy).

Agent CLIs and FastAPI dashboards run on an operator machine or secured VPS — **not** on static Hostinger hosting.

## Project layout (clean folder URLs)

```
├── index.html                 # https://matrixly.world/
├── .htaccess                  # HTTPS + old .html → clean 301s
├── agents/index.html          # /agents  (marketplace; coexists with Python packages below)
├── products/index.html        # /products
├── integrations/index.html    # /integrations
├── pricing/index.html         # /pricing
├── lead-qualifier/index.html
├── email-assistant/index.html
├── crm-assistant/index.html
├── shipping-assistant/index.html
├── shipping-assistant-guide/index.html
├── support-forge/index.html
├── book-wise/index.html
├── invoice-forge/index.html
├── invoice-processor/index.html
├── content-forge/index.html
├── seo-forge/index.html
├── seo-bespoke/index.html     # SEO-Bespoke product page
├── meet-wise/index.html
├── social-forge/index.html
├── pipeline-forge/index.html
├── doc-forge/index.html
├── starter-pack/index.html
├── etf-analyzer/index.html
├── admin/index.html           # /admin (QA console)
├── assets/
├── agents/                    # Python agent backends (not published to Hostinger)
│   ├── lead-qualifier/
│   ├── email-assistant/
│   ├── crm-assistant/
│   ├── shipping-assistant/
│   ├── support-forge/         # :8787
│   ├── book-wise/             # :8790
│   ├── invoice-forge/         # :8791
│   ├── content-forge/         # :8792
│   ├── meet-wise/             # :8793
│   ├── social-forge/          # :8794
│   ├── pipeline-forge/        # :8795
│   ├── doc-forge/             # :8796
│   ├── etf-analyzer/          # :8797
│   ├── seo-forge/             # SEOForge :8798
│   ├── invoice-processor/     # Pydantic AI AP :8799
│   ├── starter-pack/          # Unified gateway :8800
│   ├── seo-bespoke/           # SEO-Bespoke factory :8801
│   └── voice-receptionist/    # Grok Voice smoke test
└── docs/
```

---

## Agent quick starts

### SupportForge (embeddable support)

```bash
cd agents/support-forge
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m src.cli seed
python -m src.cli serve
```

Product page: [/support-forge](support-forge/). Full setup: [agents/support-forge/README.md](agents/support-forge/README.md).

### BookWise (embeddable booking)

```bash
cd agents/book-wise
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/book-wise](book-wise/). Full setup: [agents/book-wise/README.md](agents/book-wise/README.md).

### InvoiceForge (invoice processing & AR)

```bash
cd agents/invoice-forge
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/invoice-forge](invoice-forge/). Full setup: [agents/invoice-forge/README.md](agents/invoice-forge/README.md).

### Invoice Processor (Pydantic AI multi-agent AP)

```bash
cd agents/invoice-processor
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python scripts/run_example.py
python -m src.cli serve
```

Default port **8799**. Product page: [/invoice-processor](invoice-processor/). Full setup: [agents/invoice-processor/README.md](agents/invoice-processor/README.md).

### ContentForge (content creation & repurposing)

```bash
cd agents/content-forge
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/content-forge](content-forge/). Full setup: [agents/content-forge/README.md](agents/content-forge/README.md).

### SEOForge (SEO & brand marketing for US SMBs)

```bash
cd agents/seo-forge
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Default port **8798**. Product page: [/seo-forge](seo-forge/). Full setup: [agents/seo-forge/README.md](agents/seo-forge/README.md).

### SEO-Bespoke (custom SEO agent factory — higher tier)

Quiz → Business SEO Profile Summary → specialized Python agent package (20-node parallel graph). Companion to SEOForge, not a replacement.

```bash
cd agents/seo-bespoke
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli demo
python -m src.cli serve
```

Default port **8801** (avoids Invoice Processor on 8799).  
Dashboard: http://localhost:8801/  
Product page: [/seo-bespoke](seo-bespoke/). Full setup: [agents/seo-bespoke/README.md](agents/seo-bespoke/README.md).

### MeetWise (meeting outcomes)

```bash
cd agents/meet-wise
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/meet-wise](meet-wise/). Full setup: [agents/meet-wise/README.md](agents/meet-wise/README.md).

### SocialForge (social content & engagement)

```bash
cd agents/social-forge
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/social-forge](social-forge/). Full setup: [agents/social-forge/README.md](agents/social-forge/README.md).

### PipelineForge (pipeline scoring & prioritization)

```bash
cd agents/pipeline-forge
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/pipeline-forge](pipeline-forge/). Full setup: [agents/pipeline-forge/README.md](agents/pipeline-forge/README.md).

### DocForge (business documents)

```bash
cd agents/doc-forge
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/doc-forge](doc-forge/). Full setup: [agents/doc-forge/README.md](agents/doc-forge/README.md).

### Starter Pack (Support + Book + Invoice + dashboard)

```bash
cd agents/starter-pack
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Also run support-forge :8787, book-wise :8790, invoice-forge :8791
python scripts/smoke_test.py
python -m src.cli serve
```

Default port **8800**. Product page: [/starter-pack](starter-pack/). Full setup: [agents/starter-pack/README.md](agents/starter-pack/README.md).  
Docker: `cd agents/starter-pack && docker compose up --build`.

### ETF Portfolio Analyzer

```bash
cd agents/etf-analyzer
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/etf-analyzer](etf-analyzer/). Full setup: [agents/etf-analyzer/README.md](agents/etf-analyzer/README.md).

### Voice Receptionist (Grok Voice smoke test)

```bash
cd agents/voice-receptionist
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Set XAI_API_KEY in .env
python scripts/smoke_test.py
```

Full setup: [agents/voice-receptionist/README.md](agents/voice-receptionist/README.md).

### CLI-first pilots

| Agent | Folder | Typical commands |
|-------|--------|------------------|
| Lead Qualifier | `agents/lead-qualifier` | `python -m src.cli` (see README) |
| Email Assistant | `agents/email-assistant` | triage / draft / summary scripts |
| CRM Assistant | `agents/crm-assistant` | extract / hygiene / export |
| Shipping Assistant | `agents/shipping-assistant` | `demo`, `pending`, `approve` |

---

## UI QA (developers)

**QA Admin:** [/admin](admin/) — passphrase-authorized console (linked in footer).  
Automation: **[qa/](qa/)** — Python **Selenium**, **Playwright**, **pytest-bdd** (Cucumber-style), GitHub Actions [`.github/workflows/ui-qa.yml`](.github/workflows/ui-qa.yml).

```bash
npm run build && npm start
cd qa && pip install -r requirements.txt && playwright install chromium
pytest -v --site-url=http://127.0.0.1:8080
```

See [qa/README.md](qa/README.md) for the default Admin passphrase and suite details.

## Troubleshooting

Common site, signup, agent, and deploy issues: **[docs/troubleshooting.md](docs/troubleshooting.md)**.

## License

MIT License — see [LICENSE](LICENSE).

## Contact

- **Product:** Matrixly  
- **Site:** marketing pages in this repo (static Hostinger deploy)  

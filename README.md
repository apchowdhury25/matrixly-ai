# Matrixly – Agentic AI Automation Agency

**Matrixly** is the agentic AI marketplace for SMBs — ready-to-deploy agents that market, sell, ship, and run operations with human-in-the-loop controls.

This repository contains the public marketing site, agent catalog, integration directory, and Python pilot agents (Email, Lead Qualifier, CRM, Shipping).

## Short description

A production-facing static website plus local agent runtimes for:

| Agent | Purpose |
|--------|---------|
| **Lead Qualifier** | Score leads, enrich contacts, draft outreach sequences |
| **Email Assistant** | Inbox triage, drafts, urgent flags, daily brief |
| **CRM Assistant** | Contact updates, activities, pipeline hygiene (approve-to-write) |
| **Shipping Assistant** | ShipStation hub — track, exceptions, WISMO drafts |
| **SupportForge** | Embeddable AI support — chat widget, KB answers, HITL, tickets |
| **BookWise** | Embeddable AI booking — availability, confirmations, reminders, calendar sync |
| **InvoiceForge** | Invoice processing & AR — vision extract, validate, post, reminders, reports |
| **ContentForge** | Content creation & repurposing — SEO blogs, social, newsletters, ads |
| **MeetWise** | Meeting outcomes — summaries, actions, CRM, recap emails |
| **SocialForge** | Social content & engagement — posts, schedule, inbox, insights |
| **PipelineForge** | Pipeline scoring & prioritization — fit, risk, CRM, health |
| **DocForge** | Business documents — proposals, quotes, contracts, reports |
| **Starter Pack** | SupportForge + BookWise + InvoiceForge + unified dashboard |
| **ETF Analyzer** | Live free-market ETF analysis — yield, NAV, tax, Notion |

## Tech stack

| Layer | Technology |
|--------|------------|
| Site | HTML5, Tailwind CSS (CDN), vanilla JavaScript |
| Fonts | Open Sans (Google Fonts) |
| Agents | Python 3, CLI tools, optional Grok (xAI) |
| Runtime | Hermes Agent skills (optional) |
| Integrations | Gmail / Hostinger IMAP, ShipStation, Salesforce-shaped exports |
| Deploy | Static hosting (e.g. **Hostinger**) |

## How to run locally

### Website

```bash
# From the repo root
python -m http.server 8080
# or
npx serve .
```

Open (clean URLs — no `.html` in the path):

- Landing: http://localhost:8080/  
- Agents catalog: http://localhost:8080/agents  
- Integrations: http://localhost:8080/integrations  
- Pricing: http://localhost:8080/pricing  


### Shipping Assistant (example pilot agent)

```bash
cd agents/shipping-assistant
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
python -m src.cli demo
```

Other agents follow the same pattern under `agents/*/`. Copy each agent’s `.env.example` to `.env` for live credentials (never commit `.env`).

## Deployment (Hostinger)

CI/CD publishes a clean `dist/` tree to the **`deploy`** branch (and optionally FTP).

```bash
npm run lint
npm run build
# GitHub Actions on main → deploy branch → Hostinger Git auto-deploy
```

Full guide: **[DEPLOYMENT.md](DEPLOYMENT.md)** (secrets, hPanel steps, manual deploy).

Agent CLIs run on an operator machine or secured VPS — not on static Hostinger hosting.

## Project layout (clean folder URLs)

```
├── index.html                 # https://matrixly.world/
├── .htaccess                  # HTTPS + old .html → clean 301s
├── agents/index.html          # /agents  (marketplace; coexists with Python packages below)
├── products/index.html        # /products
├── integrations/index.html    # /integrations
├── pricing/index.html         # /pricing
├── lead-qualifier/index.html  # /lead-qualifier
├── email-assistant/index.html
├── crm-assistant/index.html
├── shipping-assistant/index.html
├── shipping-assistant-guide/index.html
├── support-forge/index.html
├── book-wise/index.html
├── invoice-forge/index.html
├── content-forge/index.html
├── meet-wise/index.html
├── social-forge/index.html
├── pipeline-forge/index.html
├── doc-forge/index.html
├── starter-pack/index.html
├── etf-analyzer/index.html
├── admin/index.html           # /admin (QA console)
├── assets/
├── agents/                    # Python agent backends (not published to Hostinger)
│   ├── email-assistant/
│   ├── lead-qualifier/
│   ├── crm-assistant/
│   ├── shipping-assistant/
│   ├── support-forge/
│   ├── book-wise/
│   ├── invoice-forge/
│   ├── content-forge/
│   ├── meet-wise/
│   ├── social-forge/
│   ├── pipeline-forge/
│   ├── doc-forge/
│   ├── starter-pack/          # Unified gateway + dashboard (port 8800)
│   └── etf-analyzer/          # ETF Portfolio Analyzer (port 8797)
└── docs/
```

### SupportForge (embeddable support)

```bash
cd agents/support-forge
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m src.cli seed
python -m src.cli serve
```

Product page: [/support-forge](support-forge/). Full setup & embed: [agents/support-forge/README.md](agents/support-forge/README.md).

### BookWise (embeddable booking)

```bash
cd agents/book-wise
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/book-wise](book-wise/). Full setup & embed: [agents/book-wise/README.md](agents/book-wise/README.md).

### InvoiceForge (invoice processing & AR)

```bash
cd agents/invoice-forge
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/invoice-forge](invoice-forge/). Full setup: [agents/invoice-forge/README.md](agents/invoice-forge/README.md).

### ContentForge (content creation & repurposing)

```bash
cd agents/content-forge
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/content-forge](content-forge/). Full setup: [agents/content-forge/README.md](agents/content-forge/README.md).

### MeetWise (meeting outcomes)

```bash
cd agents/meet-wise
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/meet-wise](meet-wise/). Full setup: [agents/meet-wise/README.md](agents/meet-wise/README.md).

### SocialForge (social content & engagement)

```bash
cd agents/social-forge
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/social-forge](social-forge/). Full setup: [agents/social-forge/README.md](agents/social-forge/README.md).

### PipelineForge (pipeline scoring & prioritization)

```bash
cd agents/pipeline-forge
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/pipeline-forge](pipeline-forge/). Full setup: [agents/pipeline-forge/README.md](agents/pipeline-forge/README.md).

### DocForge (business documents)

```bash
cd agents/doc-forge
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/doc-forge](doc-forge/). Full setup: [agents/doc-forge/README.md](agents/doc-forge/README.md).

### Starter Pack (Support + Book + Invoice + dashboard)

```bash
cd agents/starter-pack
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
# Also run support-forge :8787, book-wise :8790, invoice-forge :8791
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/starter-pack](starter-pack/). Full setup: [agents/starter-pack/README.md](agents/starter-pack/README.md).  
Docker: `cd agents/starter-pack && docker compose up --build`.

### ETF Portfolio Analyzer

```bash
cd agents/etf-analyzer
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

Product page: [/etf-analyzer](etf-analyzer/). Full setup: [agents/etf-analyzer/README.md](agents/etf-analyzer/README.md).

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

Common site, signup, agent, and deploy issues: **[docs/troubleshooting.md](docs/troubleshooting.md)**  
(structure similar to agent-platform help centers such as Relevance AI’s troubleshooting guides).

## License

MIT License — see [LICENSE](LICENSE).

## Contact

- **Product:** Matrixly  
- **Site:** marketing pages in this repo (static Hostinger deploy)  

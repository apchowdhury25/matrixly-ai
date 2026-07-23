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

Open:

- Landing: http://localhost:8080/index.html  
- Agents catalog: http://localhost:8080/agents.html  
- Integrations: http://localhost:8080/integrations.html  

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

## Project layout

```
├── index.html                 # Landing page
├── agents.html                # Featured AI Agents catalog
├── products.html              # Product suite
├── integrations.html          # Integration directory
├── *-assistant.html           # Per-agent deploy pages
├── shipping-assistant-guide.html
├── agents/
│   ├── email-assistant/
│   ├── lead-qualifier/
│   ├── crm-assistant/
│   └── shipping-assistant/
└── docs/                      # Optional internal notes (session archives gitignored)
```

## License

MIT License — see [LICENSE](LICENSE).

## Contact

- **Product:** Matrixly  
- **Site:** marketing pages in this repo (static Hostinger deploy)  

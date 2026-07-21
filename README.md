# Matrixly.ai – Agentic AI Automation Agency

**Matrixly.AI** is the agentic AI marketplace for SMBs — ready-to-deploy agents that market, sell, ship, and run operations with human-in-the-loop controls.

This repository contains the public marketing site, agent catalog, integration directory, and Python pilot agents (Email, Lead Qualifier, CRM, Shipping).

## Short description

A production-facing static website plus local agent runtimes for:

| Agent | Purpose |
|--------|---------|
| **Lead Qualifier** | Score leads, enrich contacts, draft outreach sequences |
| **Email Assistant** | Inbox triage, drafts, urgent flags, daily brief |
| **CRM Assistant** | Contact updates, activities, pipeline hygiene (approve-to-write) |
| **Shipping Assistant** | ShipStation hub — track, exceptions, WISMO drafts |

Built by **Matrix Bazaar LLC** (Houston, TX).

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

## Deployment note (Hostinger)

1. Build is **static** — upload the site root HTML/assets (or connect Git deploy if enabled).
2. Do **not** upload `.env`, `.venv/`, or local `data/output/` folders.
3. Point the domain document root at this project’s public HTML files.
4. Agent CLIs typically run on an operator machine or a secured VPS, not inside static web hosting.

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

- **Matrix Bazaar LLC** · Houston, TX  
- **Email:** anwar.chowdhury@matrixbazaar.com  

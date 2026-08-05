# Matrixly Troubleshooting

> Identify and resolve common issues with the Matrixly website, Get Started Free signup, marketplace agents, and pilot runtimes.

When something isn’t working as expected, start with the section that matches your symptom. Each guide lists **common causes**, **checks to run**, and **fixes**. If you’re still stuck, see [Still need help?](#still-need-help).

---

## Contents

1. [Browser and site issues](#1-browser-and-site-issues)
2. [Get Started Free / signup & login](#2-get-started-free--signup--login)
3. [Agents not working](#3-agents-not-working)
4. [Agent-specific pilots](#4-agent-specific-pilots)
5. [Deploy, Hostinger, and CI/CD](#5-deploy-hostinger-and-cicd)
6. [UI QA Admin console](#6-ui-qa-admin-console)
7. [Still need help?](#still-need-help)

---

## 1. Browser and site issues

The Matrixly marketing site is a **static** site (HTML + Tailwind CDN + vanilla JS). Most “site broken” reports are browser, cache, or network related—similar.

### Supported browsers

Use a current desktop browser:

- **Chrome**
- **Firefox**
- **Safari**
- **Edge**

Mobile browsers can view the marketing site, but agent pilot CLIs and admin dashboards are designed for **desktop**.

### Basic steps (try in order)

#### 1. Update your browser

Outdated browsers may not support CSS variables, modern JS, or the auth modal.

#### 2. Disable extensions

Extensions (ad blockers, privacy tools, script blockers) can break theme toggle, modals, or forms.

1. Open an **Incognito / Private** window  
2. Open `https://matrixly.world` (or your staging URL)  
3. Retest  

If it works in private mode, re-enable extensions one by one to find the culprit.

#### 3. Clear cache

- **Chrome / Edge / Firefox (Windows):** `Ctrl+Shift+Delete`  
- **Mac:** `Cmd+Shift+Delete`  
- **Safari:** Safari → Clear History…  

Hard-refresh the page: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac).

#### 4. Try another browser or network

Rules out browser-specific bugs and captive Wi‑Fi / corporate proxies.

#### 5. Check the console

1. Open DevTools → **Console**  
   - Chrome/Edge: `F12` or `Ctrl+Shift+J`  
   - Firefox: `Ctrl+Shift+K`  
   - Safari: enable Develop menu, then `Cmd+Opt+C`  
2. Note red errors (CORS, failed scripts, blocked third parties).  
3. Screenshot or copy errors when contacting support.

### Common site symptoms

| Symptom | Likely cause | Fix |
|--------|----------------|-----|
| Blank or unstyled page | CDN / network / ad blocker | Incognito; allow `cdn.tailwindcss.com` and Google Fonts |
| Theme stuck light/dark | `localStorage` corruption | Clear site data for the domain; toggle theme again |
| Nav links 404 | Old Hostinger deploy / wrong branch | Confirm **deploy** branch latest; see [§5](#5-deploy-hostinger-and-cicd) |
| Images missing | Missing `assets/` in publish tree | Rebuild with `npm run build`; ensure `dist/assets` ships |
| Layout broken on agents cards | Cached old HTML | Hard refresh; verify Shipping “Deploy Now” alignment on `/agents` |

---

## 2. Get Started Free / signup & login

Matrixly’s **Get Started Free** flow opens an **auth modal** with:

- Continue with **Google**  
- Continue with **Microsoft**  
- Continue with **SSO**  
- Continue with **email**  
- **Already have an account? Log in**

### Modal doesn’t open

1. Confirm you clicked a control with **Get Started Free** / **Get Started** (nav, pricing Explore, final CTA).  
2. Disable popup blockers and extensions.  
3. Check the console for JS errors.  
4. Hard-refresh after a new deploy—older pages only had a mailto or demo form.  
5. If you only scrolled to `#final-cta` without clicking the button, the modal does **not** auto-open (by design).

### Google / Microsoft “Continue” doesn’t finish OAuth

**Expected in demo mode:** the UI records intent and shows a success path; live OAuth requires a connected Matrixly backend.

| Check | Action |
|-------|--------|
| Third-party cookies blocked | Allow cookies for auth providers, or use email path |
| Corporate SSO only | Use **Continue with SSO** and your work domain |
| Production OAuth not configured | Contact Matrixly to enable Google/Microsoft apps |

### Email signup or login fails

1. Use a valid work email format.  
2. Password must meet the form’s minimum length (signup).  
3. After success, intent is stored in browser `localStorage` (`matrixly-auth-intent`) for follow-up—clearing site data removes it.  
4. For production accounts, password reset and identity will be handled by the Matrixly auth service once fully live.

### SSO issues

1. Enter a **work** email (company domain).  
2. If your org has not configured SAML/OIDC with Matrixly, SSO will not complete—use email or contact sales.  
3. Ask your IT admin for the correct IdP and allowed domains.

### “Already have an account? Log in”

Opens the **Log in** panel in the same modal. If you meant to create an account, choose **Get started free** / back to the chooser.

---

## 3. Agents not working

Modeled after common agent-platform troubleshooting guide): credits/API, tools, configuration, integrations.

### 3.1 Missing API keys or “rule-only” mode

Many Matrixly pilots run **without** an LLM key (heuristics / FAQ), but quality drops or features stay limited.

| Agent | Typical key / env |
|-------|-------------------|
| SupportForge, BookWise, InvoiceForge, ContentForge, MeetWise, SocialForge, PipelineForge, DocForge, SEOForge, SEO-Bespoke, ETF Analyzer, Invoice Processor | `XAI_API_KEY` (Grok) — optional for offline/rule demos where noted |
| Email Assistant, Lead Qualifier, CRM | `XAI_API_KEY` optional; mailbox / CRM credentials required for live paths |
| Shipping Assistant | ShipStation API key/secret for live mode |
| Voice Receptionist | `XAI_API_KEY` required for Grok Voice Realtime smoke test |
| Starter Pack | Sibling agent ports + optional pack API keys |

**Checks**

1. Copy `.env.example` → `.env` under the agent folder.  
2. Never commit `.env`.  
3. Restart the process after editing env (`python -m src.cli serve` or CLI command).  
4. Confirm key is non-empty: `python -m src.cli status` (where available).

### 3.2 Tool / integration failures

If an agent “runs” but external steps fail:

1. **Test the integration alone** (IMAP login, ShipStation status, calendar list, CSV export).  
2. Verify **scopes and permissions** (Gmail, Google Calendar OAuth, Zendesk/QBO/Xero tokens).  
3. Watch for **rate limits** and expired tokens.  
4. Read agent logs / `data/audit` JSONL where present (SupportForge, BookWise, InvoiceForge).

### 3.3 Configuration and HITL

Human-in-the-loop can look like “nothing happened” if actions are waiting for approval.

1. Open the agent’s **admin** UI (if any) or run `python -m src.cli pending`.  
2. Check `HITL_MODE` / `config.yaml` thresholds (auto-resolve, confidence).  
3. Approve or reject queued actions; re-run the customer flow.

### 3.4 Knowledge / retrieval empty

**SupportForge / knowledge agents**

1. Ensure files exist under `knowledge/` (or re-run Notion sync).  
2. `python -m src.cli seed` (or `POST /v1/kb/reindex`).  
3. Ask a question that clearly matches FAQ/pricing/hours sample docs.  
4. Low confidence → draft/escalate by design—not necessarily a crash.

### 3.5 Agent behavior not what you expected

Agents reason and route; they are not rigid scripts.

- Tighten prompts under `prompts/`.  
- Set clearer business hours, thresholds, and allowlists in `config.yaml`.  
- Provide sample inputs (order IDs, emails) in the message.  
- Prefer a stronger model only when `XAI_API_KEY` and model id are set.

---

## 4. Agent-specific pilots

### Email Assistant

| Issue | Fix |
|-------|-----|
| Can’t connect mailbox | Confirm `EMAIL_BACKEND=imap` or `gmail`; Hostinger IMAP/SSL settings; app password if required |
| No labels / triage empty | Run `python -m src.cli triage`; check folder names (INBOX) |
| Drafts not created | Drafts folder path; never auto-sends by design |

See `agents/email-assistant/README.md`.

### Shipping Assistant

| Issue | Fix |
|-------|-----|
| Always demo mode | Set ShipStation key + secret in `.env`; `python -m src.cli status` → live |
| Pending actions stuck | `python -m src.cli pending` then `approve` / `reject` |

### SupportForge

| Issue | Fix |
|-------|-----|
| Widget not loading | CORS_ORIGINS must include the host page; correct `data-api` + `data-key` |
| 401 on chat | Check `SUPPORTFORGE_WIDGET_KEY` |
| Admin locked | Use `SUPPORTFORGE_API_KEY` in the admin login |

### BookWise

| Issue | Fix |
|-------|-----|
| No slots | Business hours / timezone in `config.yaml`; min notice / buffers |
| Port conflict | Default **8790**; change `server.port` |

### InvoiceForge

| Issue | Fix |
|-------|-----|
| Vision extract fails | Set `XAI_API_KEY` + vision model; or use text `.txt` samples |
| Always pending HITL | High amount / keywords / missing PO rules in `config.yaml` |
| CSV not updating | Confirm `ACCOUNTING_BACKEND=csv` and write access to `data/exports/` |

### Lead Qualifier / CRM Assistant

| Issue | Fix |
|-------|-----|
| Empty scores / exports | Provide sample JSON under `data/`; run CLI with demo files |
| Grok not used | Set `XAI_API_KEY` |

### SEOForge

| Issue | Fix |
|-------|-----|
| Dashboard not loading | Serve on default port **8798**: `python -m src.cli serve` |
| Content stuck pending | Approve/reject in HITL queue (`python -m src.cli pending`) |
| Need a custom client agent | Use **SEO-Bespoke** (port **8801**), not SEOForge |

### SEO-Bespoke

| Issue | Fix |
|-------|-----|
| `UnicodeEncodeError` on serve (Windows) | Update to latest CLI (ASCII messages); or set `$env:PYTHONIOENCODING='utf-8'` |
| Port conflict with Invoice Processor | SEO-Bespoke uses **8801**; Invoice Processor uses **8799** |
| Not on Agents page | Marketing card is `/seo-bespoke`; live quiz still needs `python -m src.cli serve` |
| Smoke / package fails | Run `python scripts/smoke_test.py`; packages under `data/packages/` |

### Invoice Processor

| Issue | Fix |
|-------|-----|
| Port in use | Default **8799** — stop conflicting process or change `config.yaml` |
| No XAI key | Offline rule extraction still works for samples; set `XAI_API_KEY` for LLM path |

### ConnectForge (Twilio)

| Issue | Fix |
|-------|-----|
| Cannot send SMS | Set `TWILIO_*` env vars; in Test Mode destination must be in `TWILIO_VERIFIED_NUMBERS` |
| Trial / unverified error | Verify handset in Twilio Console; keep `CONNECTFORGE_TEST_MODE=true` |
| Inbound not firing | Webhook POST → `/v1/webhooks/sms`; tunnel with ngrok; set `PUBLIC_BASE_URL` |
| Stuck pending | Approve HITL in dashboard or `python -m src.cli approve --id hitl_...` |

### Voice Receptionist

| Issue | Fix |
|-------|-----|
| Smoke fails immediately | Set `XAI_API_KEY` in `.env`; confirm network to xAI Realtime API |
| No audio file | Transcript-only success is OK; PCM written when the session returns audio |

### Default local ports (FastAPI agents)

| Port | Agent |
|------|--------|
| 8787 | SupportForge |
| 8790 | BookWise |
| 8791 | InvoiceForge |
| 8792 | ContentForge |
| 8793 | MeetWise |
| 8794 | SocialForge |
| 8795 | PipelineForge |
| 8796 | DocForge |
| 8797 | ETF Analyzer |
| 8798 | SEOForge |
| 8799 | Invoice Processor |
| 8800 | Starter Pack |
| 8801 | SEO-Bespoke |
| 8802 | ConnectForge (Twilio) |

---

## 5. Deploy, Hostinger, and CI/CD

### Site didn’t update after push

1. Confirm GitHub Action **CI-CD** succeeded on `main`.  
2. Hostinger Git deploy must track the **`deploy`** branch (not only `main`).  
3. Clear CDN/browser cache.  
4. Local check: `npm run build` and inspect `dist/`.

### Build fails

```bash
npm run lint
npm run build
```

- Missing page in `scripts/ci-build.mjs` `SITE_PAGES` → add `folder/index.html`.  
- Agent compile failures in CI → fix Python syntax under `agents/*/src`.

### UI QA workflow fails

```bash
npm run build && npm start
cd qa
pip install -r requirements.txt
playwright install chromium
pytest -v --site-url=http://127.0.0.1:8080
```

See `qa/README.md` and `.github/workflows/ui-qa.yml`.

### Secrets

Never put production passwords or API keys in HTML, commits, or public issues. Use Hostinger/GitHub **secrets** and agent `.env` files (gitignored).

---

## 6. UI QA Admin console

**URL:** `/admin` (also linked as **QA Admin** in site footer).

| Issue | Fix |
|-------|-----|
| Can’t unlock | Use the authorization passphrase (default for local: see `qa/README.md`); hash is in `admin/index.html` |
| Tools empty after login | Sign-in only unlocks the console; run automated suites from your machine or CI |
| Link probe fails cross-origin | Run against same-origin `dist/` via `npm start` |
| Observability cards all red | Start stack: `cd infra/observability && docker compose up -d`; see full table in `qa/README.md` |
| Grafana iframe blank | Expected when Grafana blocks framing; use **Open Dashboard** |
| Need stack compose / LogQL | `infra/observability/` and **Observability Stack** section in `qa/README.md` |

Rotate the production passphrase by replacing `PASS_HASH` (SHA-256 hex of the new phrase).

**Observability & infrastructure (self-hosted):** Crawl4AI, Prometheus, Grafana, Loki — documented end-to-end under [qa/README.md — Observability Stack](../qa/README.md#observability-stack-self-hosted).

---

## Still need help?

If you’ve worked through the relevant section and the issue remains, contact Matrixly support and include:

1. **What you were trying to do** (site page, agent name, CLI command)  
2. **Expected vs actual result**  
3. **Steps already tried** (from this doc)  
4. **Environment:** browser + version, OS, URL or agent folder  
5. **Errors:** console messages, CLI stderr, audit log snippets (redact secrets)  
6. **Optional:** short screen recording ([Loom](https://www.loom.com) / similar)

### Contact channels

| Channel | Use for |
|---------|---------|
| **Email** | `anwar@matrixly.world` — product interest, pilots, account help |
| **Get Started Free** | Account signup / login chooser on the website |
| **GitHub** | Open an issue on [matrixly-ai](https://github.com/apchowdhury25/matrixly-ai) for repo/docs bugs |
| **QA Admin** | Internal UI checklist and runner docs (`/admin`) |

### Related docs in this repo

| Doc | Path |
|-----|------|
| Site deployment | [DEPLOYMENT.md](../DEPLOYMENT.md) |
| Hostinger walkthrough | [matrixbazaar-hostinger-deploy-walkthrough.md](./matrixbazaar-hostinger-deploy-walkthrough.md) |
| UI QA framework | [qa/README.md](../qa/README.md) |
| SupportForge | [agents/support-forge/README.md](../agents/support-forge/README.md) |
| BookWise | [agents/book-wise/README.md](../agents/book-wise/README.md) |
| InvoiceForge | [agents/invoice-forge/README.md](../agents/invoice-forge/README.md) |
| Invoice Processor | [agents/invoice-processor/README.md](../agents/invoice-processor/README.md) |
| ContentForge | [agents/content-forge/README.md](../agents/content-forge/README.md) |
| SEOForge | [agents/seo-forge/README.md](../agents/seo-forge/README.md) |
| SEO-Bespoke | [agents/seo-bespoke/README.md](../agents/seo-bespoke/README.md) |
| MeetWise | [agents/meet-wise/README.md](../agents/meet-wise/README.md) |
| SocialForge | [agents/social-forge/README.md](../agents/social-forge/README.md) |
| PipelineForge | [agents/pipeline-forge/README.md](../agents/pipeline-forge/README.md) |
| DocForge | [agents/doc-forge/README.md](../agents/doc-forge/README.md) |
| Starter Pack | [agents/starter-pack/README.md](../agents/starter-pack/README.md) |
| ETF Analyzer | [agents/etf-analyzer/README.md](../agents/etf-analyzer/README.md) |
| ConnectForge | [agents/connect-forge/README.md](../agents/connect-forge/README.md) |
| Voice Receptionist | [agents/voice-receptionist/README.md](../agents/voice-receptionist/README.md) |
| Email Assistant | [agents/email-assistant/README.md](../agents/email-assistant/README.md) |
| Shipping Assistant | [agents/shipping-assistant/README.md](../agents/shipping-assistant/README.md) |
| Lead Qualifier | [agents/lead-qualifier/README.md](../agents/lead-qualifier/README.md) |
| CRM Assistant | [agents/crm-assistant/README.md](../agents/crm-assistant/README.md) |
| Root catalog | [README.md](../README.md) |

---

*Last updated: 2026-08-03 · Matrixly troubleshooting guide.*

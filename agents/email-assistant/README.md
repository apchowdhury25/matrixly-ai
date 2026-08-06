# Email Assistant (Matrixly.AI)

**Marketplace tile:** MAIL · **Domain:** Sales / Ops  
**Best for:** US small-business owners (home services, ecommerce, professional services, contractors)

Connect **Gmail** (recommended) or **Hostinger / Outlook IMAP**, then triage the inbox, draft replies (**never auto-send**), flag urgent items, and email yourself a daily brief.

> **Privacy:** Your emails never leave your control. We do not train on them. You can revoke access any time in your Google account.

---

## What the SMB owner sees (demo walkthrough)

1. **Integrations page** → Gmail card → **Connect Gmail**  
2. Modal explains triage, drafts-only, daily brief + privacy line  
3. Optional **Test Mode** (sample emails, no login)  
4. **Connect with Google** → terminal `connect-gmail` → browser consent (~2 min)  
5. Success → **Open Email Assistant** → first triage + **24-hour impact report** (screenshot-ready)

---

## What it does

| Command | Action |
|---------|--------|
| `connect-gmail` | Browser OAuth for Gmail API (recommended) |
| `auth` / `profile` | Login check for current backend |
| `test-mode` | Sample inbox demo (no real mail) |
| `triage` | Score mail, apply `Matrixly/*` labels, write impact report |
| `urgent` | Same pipeline, urgent items only |
| `draft --message-id ID` | Create a **draft** reply (never auto-sends) |
| `summary` | Daily brief → markdown + email to yourself |
| `impact` | “Your first 24-hour impact report” |
| `token-status` | Verify Gmail token / refresh (no secrets printed) |

### Labels created automatically

- `Matrixly/Urgent`
- `Matrixly/Needs Reply`
- `Matrixly/FYI`
- `Matrixly/Waiting`
- `Matrixly/Newsletter`
- `Matrixly/Automated`

---

## Gmail (recommended for most SMBs)

Uses official **Google OAuth2 + Gmail API**.

**Scopes (plain English):**

| Scope | Why |
|-------|-----|
| `gmail.readonly` | Read inbox to triage |
| `gmail.modify` | Apply labels; manage messages for organization |
| `gmail.labels` | Create `Matrixly/*` labels |
| `gmail.send` | Email the **daily brief to you only** (not customer auto-replies) |

### 1. Python env

```powershell
cd agents\email-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### 2. Google Cloud one-time setup

Follow the copy-paste guide: **[scripts/setup_oauth.md](scripts/setup_oauth.md)**  
Save the Desktop OAuth client JSON as `data/credentials.json` (gitignored).

### 3. Connect Gmail (~2 minutes)

```powershell
# .env
EMAIL_BACKEND=gmail
EMAIL_PROFILE=gmail

python -m src.cli connect-gmail
```

Browser opens → sign in → Allow. You should see **Success — Gmail connected**.

### 4. Run the agent

```powershell
python -m src.cli profile
python -m src.cli triage
python -m src.cli draft --message-id "<id from triage --json>"
python -m src.cli summary          # emails brief to yourself
python -m src.cli summary --no-send
python -m src.cli impact
python -m src.cli token-status
```

### 5. Full OAuth testing guide

See **[scripts/test_oauth.md](scripts/test_oauth.md)** — pre-flight, happy path, failures, expected output, quick verification.

---

## Hostinger / IMAP

Same Thunderbird-style settings many SMBs already use:

| Setting | Hostinger example |
|---------|-------------------|
| IMAP | `imap.hostinger.com:993` SSL |
| SMTP | `smtp.hostinger.com:465` SSL |
| Drafts | `INBOX.Drafts` |
| Sent | `INBOX.Sent` |

```powershell
# .env
EMAIL_BACKEND=imap
EMAIL_PROFILE=hostinger
EMAIL_HOSTINGER_USER=you@yourdomain.com
EMAIL_HOSTINGER_PASSWORD=********

python -m src.cli auth
python -m src.cli profile
python -m src.cli triage
python -m src.cli draft --message-id "INBOX:123"
python -m src.cli summary
```

**Outlook / other IMAP:** set `EMAIL_IMAP_HOST`, `EMAIL_IMAP_PORT`, `EMAIL_IMAP_USER`, `EMAIL_IMAP_PASSWORD`, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT` (see `.env.example`).

**Gmail via App Password (IMAP, not OAuth):** `EMAIL_BACKEND=imap`, `EMAIL_PROFILE=gmail`, App Password in `EMAIL_GMAIL_PASSWORD`.

---

## Test Mode (try before connecting real email)

```powershell
python -m src.cli test-mode
python -m src.cli triage --test --no-llm
python -m src.cli draft --test --message-id sample-quote-request
python -m src.cli impact --test
```

Sample messages live in memory only. Impact report is written under `data/summaries/impact-first-24h-latest.md` for screenshots.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `EMAIL_BACKEND` | `gmail` \| `imap` \| `test` |
| `EMAIL_PROFILE` | `gmail` \| `hostinger` |
| `GMAIL_CREDENTIALS_FILE` | Default `data/credentials.json` |
| `GMAIL_TOKEN_FILE` | Default `data/token.json` (refreshable; gitignored) |
| `GMAIL_SCOPES` | Optional comma-separated scope override |
| `EMAIL_GMAIL_USER` / `EMAIL_GMAIL_PASSWORD` | IMAP App Password path |
| `EMAIL_HOSTINGER_USER` / `EMAIL_HOSTINGER_PASSWORD` | Hostinger IMAP |
| `EMAIL_IMAP_*` / `EMAIL_SMTP_*` | Generic IMAP/SMTP |
| `EMAIL_SUMMARY_TO` | Daily brief recipient (default: your mailbox) |
| `XAI_API_KEY` | Optional Grok for smarter triage/drafts |

Never commit `.env`, `data/credentials.json`, or `data/token.json`.

---

## Safety (human-in-the-loop)

- **Customer replies:** drafts only. `draft.auto_send` is forced **false**.
- **Daily brief:** may send to `summary.deliver_to` (your own address).
- **Revoke:** [Google Account → Security → Third-party access](https://myaccount.google.com/permissions)
- Re-auth: `python -m src.cli connect-gmail --force`

---

## Hermes integration

Skill path (if installed):

`%USERPROFILE%\.hermes\skills\email\email-assistant\SKILL.md`

```powershell
hermes cron create "0 8 * * *" --name "email-daily-brief" --skill email-assistant --workdir "<repo>\agents\email-assistant" "python scripts/run_daily_summary.py"
hermes cron create "0 7 * * 1-5" --name "email-morning-triage" --skill email-assistant --workdir "<repo>\agents\email-assistant" "python scripts/run_triage.py"
```

---

## Project layout

```
email-assistant/
  config.yaml
  requirements.txt
  .env.example
  src/           # gmail_client, imap_client, test_mode, triage, draft, impact, cli
  scripts/       # setup_oauth.md, test_oauth.md, cron helpers
  prompts/
  data/          # credentials, token, summaries (local, gitignored)
```

---

## Pattern for future integrations

After Gmail, use the same pattern for other SMB tools:

| Integration | Owner value | Connect pattern |
|-------------|-------------|-----------------|
| **QuickBooks** | Invoices, cash view | OAuth → `connect-quickbooks` CLI + Integrations modal |
| **HubSpot** | Leads / pipeline | OAuth → CRM Assistant |
| **Shopify** | Orders / WISMO | OAuth or private app token → Shipping / Support |
| **Google Business Profile** | Reviews / posts | OAuth → SEO / Social agents |
| **ShipStation** | Labels / exceptions | API key → Shipping Assistant (already partly live) |

**Shared UX contract for every “Connect X” button:**

1. Plain-language modal (what agent does + privacy + scopes in English)  
2. Primary OAuth / API connect path under 2 minutes  
3. Fallback path (CSV, IMAP, manual API key)  
4. Test Mode with sample data before live credentials  
5. Success state → deep link into the agent product page  
6. Tokens only in gitignored local/secret store; refresh handled in client  
7. HITL for anything external (drafts, pending actions — never silent send)

---

## Marketplace copy

> Triage inbox, draft replies, and flag urgent items so operators stop living in email.  
> Gmail OAuth · IMAP fallback · Test Mode · Daily executive brief · Human approval always

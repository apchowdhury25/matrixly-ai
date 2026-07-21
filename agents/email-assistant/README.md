# Email Assistant (Matrixly.AI)

**Marketplace tile:** MAIL · **Domain:** Sales / Ops  
**Mailbox:** `anwar.chowdhury@matrixbazaar.com`  
**Server:** Hostinger IMAP/SMTP (same as Thunderbird)  
**Optional backend:** Gmail API OAuth

Triage the inbox, draft replies, flag urgent items, and email a daily executive brief — IMAP by default + optional Grok (xAI) + Hermes runtime.

## What it does

| Command | Action |
|---------|--------|
| `triage` | Score unread/inbox mail, apply `Matrixly/*` labels |
| `urgent` | Same pipeline, report only urgent items |
| `draft --message-id ID` | Create a **Gmail draft** reply (never auto-sends) |
| `summary` | Daily brief → markdown + email to yourself |
| `auth` / `profile` | OAuth login and mailbox identity check |

### Labels created

- `Matrixly/Urgent`
- `Matrixly/Needs Reply`
- `Matrixly/FYI`
- `Matrixly/Waiting`
- `Matrixly/Newsletter`
- `Matrixly/Automated`

## Quick start (Thunderbird / Hostinger — recommended)

Settings match your Thunderbird profile:

| Setting | Value |
|---------|--------|
| IMAP | `imap.hostinger.com:993` SSL |
| SMTP | `smtp.hostinger.com:465` SSL |
| User | `anwar.chowdhury@matrixbazaar.com` |
| Drafts | `INBOX/Drafts` |
| Sent | `INBOX/Sent` |

### 1. Python env

```powershell
cd C:\Users\anwar\projects\matrix-six\agents\email-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### 2. Put mailbox password in `.env` only

Edit `agents/email-assistant/.env` (do **not** paste the password into chat):

```
EMAIL_BACKEND=imap
EMAIL_IMAP_USER=anwar.chowdhury@matrixbazaar.com
EMAIL_IMAP_PASSWORD=********
```

Optional: `XAI_API_KEY=...` for smarter triage/drafts.

### 3. Connect and run

```powershell
python -m src.cli auth
python -m src.cli profile
python -m src.cli triage
python -m src.cli urgent
python -m src.cli draft --message-id "INBOX:123"
python -m src.cli summary          # emails brief to yourself
python -m src.cli summary --no-send
```

### Alternate: Gmail API OAuth

If you later move the domain to Google Workspace, set `EMAIL_BACKEND=gmail` and follow [scripts/setup_oauth.md](scripts/setup_oauth.md).

## Hermes integration

### Skill

Installed at:

`C:\Users\anwar\.hermes\skills\email\email-assistant\SKILL.md`

Preload in a session:

```powershell
hermes -s email-assistant -z "Triage my unread Gmail and list anything urgent"
```

### Daily summary cron

After OAuth works:

```powershell
hermes cron create "0 8 * * *" --name "email-daily-brief" --skill email-assistant --workdir "C:\Users\anwar\projects\matrix-six\agents\email-assistant" "Run the Email Assistant daily summary for my Gmail: triage last 24h, flag urgent, and send me the executive brief. Prefer the local CLI: python scripts/run_daily_summary.py"
```

Morning triage (weekdays 7am):

```powershell
hermes cron create "0 7 * * 1-5" --name "email-morning-triage" --skill email-assistant --workdir "C:\Users\anwar\projects\matrix-six\agents\email-assistant" "Run morning inbox triage with labels via: python scripts/run_triage.py"
```

Ensure Hermes cron scheduler is running (`hermes cron status` / gateway).

### Optional: Gmail MCP (Hermes tools)

Community auto-auth MCP (alternative to the Python client):

```powershell
hermes mcp add gmail --command npx --args -y @gongrzhe/server-gmail-autoauth-mcp
```

Official Google remote MCP requires a GCP OAuth web client — see Google Workspace MCP docs.

## Configuration

Edit `config.yaml`:

- `account.primary_email` / `domains`
- `urgency.keywords` and `vip_*`
- `summary.deliver_to` and cron-friendly lookback
- `draft.signature` / `auto_send` (keep `false` for pilots)

## Safety

- **Human-in-the-loop** for outbound mail: only **drafts** are created for replies.
- Daily brief is sent only to `summary.deliver_to` (defaults to your own address).
- Tokens and OAuth client secrets are gitignored under `data/`.

## Project layout

```
email-assistant/
  config.yaml
  requirements.txt
  src/           # gmail_client, triage, draft, urgent, summary, agent, cli
  scripts/       # oauth guide + cron entrypoints
  prompts/       # system persona
  data/          # credentials, token, summaries (local)
```

## Marketplace copy

> Triage inbox, draft replies, and flag urgent items so operators stop living in email.  
> Gmail workflows · Hermes skills + memory context · Daily executive brief

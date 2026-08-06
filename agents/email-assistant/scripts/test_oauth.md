# Testing the OAuth Flow

Step-by-step verification for **Gmail API OAuth** on Email Assistant.  
Use this after any code change that touches auth, scopes, or mail backends.

**Working directory:**

```powershell
cd agents\email-assistant
.\.venv\Scripts\Activate.ps1   # if not already active
```

---

## A. Pre-flight checklist

### Google Cloud

- [ ] Project exists; **Gmail API** enabled  
- [ ] OAuth consent screen configured (External → you are a **Test user**, or Internal)  
- [ ] OAuth client type: **Desktop app**  
- [ ] JSON downloaded as `data/credentials.json`  

### Required scopes

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.labels
```

### `.env` variables that must be present

```
EMAIL_BACKEND=gmail
EMAIL_PROFILE=gmail
```

Optional overrides:

```
GMAIL_CREDENTIALS_FILE=data/credentials.json
GMAIL_TOKEN_FILE=data/token.json
EMAIL_SUMMARY_TO=you@yourbusiness.com
XAI_API_KEY=...          # optional smarter drafts
```

### Revoke previous tokens (clean slate)

```powershell
Remove-Item data\token.json -ErrorAction SilentlyContinue
# And/or in browser:
# https://myaccount.google.com/permissions → remove Matrixly Email Assistant
```

### Files that must NOT be committed

```
.env
data/credentials.json
data/token.json
```

---

## B. Happy-path test (your own account)

### 1. Start OAuth

```powershell
python -m src.cli connect-gmail
```

**Expected:** Panel “Connect your Gmail” → browser opens → consent screen lists read / labels / send-related permissions.

### 2. Complete browser consent

- Sign in with the mailbox you want managed  
- Click **Allow** (not Cancel)  
- Browser page: success message; return to terminal  

### 3. Verify token saved and refresh works

```powershell
python -m src.cli token-status
```

**Expected success (shape):**

```
{'credentials_file_exists': True, 'token_file_exists': True, 'valid': True,
 'has_refresh_token': True, ...}
Token is valid (refresh works if expired).
```

Force refresh path (optional): wait until near expiry, or re-run `token-status` after a successful connect — client refreshes expired tokens automatically on next API call.

### 4. Confirm connected mailbox

```powershell
python -m src.cli profile
```

**Expected:**

```
┌─ Mailbox profile ─┐
│ Email: you@...    │
│ Backend: gmail    │
│ Messages: N       │
└───────────────────┘
```

### 5. Triage real unread mail

```powershell
python -m src.cli triage --max 15
# or JSON for message ids:
python -m src.cli triage --max 15 --json
```

**Expected:** Markdown report with Urgent / Needs reply / Other; path to **impact report** printed.

### 6. Draft reply to a specific message

```powershell
python -m src.cli draft --message-id "PASTE_GMAIL_MESSAGE_ID"
```

**Expected:** Panel with draft body, `draft_id=...`, title includes **not sent**.  
In Gmail UI: **Drafts** contains the reply in the same thread.

### 7. Daily brief to yourself

```powershell
python -m src.cli summary --no-send     # markdown only first
python -m src.cli summary               # emails brief to EMAIL_SUMMARY_TO / you
```

**Expected:** Brief markdown; with send enabled, “Emailed brief to you@…”

### 8. Confirm Matrixly/* labels in Gmail

In Gmail left nav (or Settings → Labels), you should see:

- Matrixly/Urgent  
- Matrixly/Needs Reply  
- Matrixly/FYI  
- Matrixly/Waiting  
- Matrixly/Newsletter  
- Matrixly/Automated  

Created on `connect-gmail` and/or first `triage`.

---

## C. Failure / edge-case tests

### User denies consent

1. `Remove-Item data\token.json -ErrorAction SilentlyContinue`  
2. `python -m src.cli connect-gmail`  
3. On consent screen click **Cancel** / deny  

**Expected:** Terminal red error explaining decline; suggests `connect-gmail` again or `test-mode`. Exit code ≠ 0. No valid token.

### Token expires / revoked

```powershell
# Simulate revoke: remove access in Google Account, then:
python -m src.cli profile
```

**Expected:** Clear message to run `connect-gmail --force`.

```powershell
python -m src.cli connect-gmail --force
```

**Expected:** Fresh browser consent; success panel.

### Insufficient scopes

If an old token was granted with fewer scopes:

```powershell
python -m src.cli connect-gmail --force
```

Approve **all** permissions. Then:

```powershell
python -m src.cli token-status
python -m src.cli triage --max 5
```

If labels fail with 403: re-auth with full scopes; check Cloud Console scopes.

### Re-authenticate cleanly

```powershell
python -m src.cli connect-gmail --force
python -m src.cli profile
```

### Test Mode vs live mode

| | Test Mode | Live Gmail |
|--|-----------|------------|
| Command | `python -m src.cli test-mode` or `--test` | `EMAIL_BACKEND=gmail` + `connect-gmail` |
| Mail | Sample messages only | Real inbox |
| Labels | In-memory | Real Gmail labels |
| Drafts | In-memory draft ids | Real Gmail Drafts |
| Risk | None | HITL drafts only |

```powershell
python -m src.cli test-mode
python -m src.cli triage --test --no-llm
python -m src.cli draft --test --message-id sample-quote-request
```

---

## D. Expected output examples

### Success — connect-gmail

```
╭─ Matrixly Email Assistant ─╮
│ Connect your Gmail         │
│ ...                        │
╰────────────────────────────╯
Opening your browser to connect Gmail…
...
╭─ You're all set ─╮
│ Success — Gmail connected │
│ Mailbox: you@business.com │
│ Matrixly labels ready: ... │
╰────────────────────────────╯
```

### Success — triage (excerpt)

```
# Inbox Triage Report

**Total reviewed:** 8
**Urgent:** 2
**Needs reply:** 3

## Urgent
- **URGENT: ...** — customer@... (score 0.9, urgent)

Your first 24-hour impact report: ...\data\summaries\impact-first-24h-....md
```

### Failure — missing credentials.json

```
Setup needed:
Missing Google app credentials at:
  ...\data\credentials.json

For small business setup (about 5 minutes):
  1. Open scripts/setup_oauth.md ...
```

### Failure — consent denied

```
Could not connect Gmail:
You declined Google access — no problem.
Nothing was connected. When you are ready:
  python -m src.cli connect-gmail
Or try sample emails first:
  python -m src.cli test-mode
```

### Failure — expired / revoked token

```
Gmail auth:
Your Google login expired or was revoked.
Fix: run  python -m src.cli connect-gmail --force
```

---

## E. Quick verification commands (after any code change)

Run this sequence (~1 minute if already connected):

```powershell
cd agents\email-assistant
.\.venv\Scripts\Activate.ps1

# 1) Auth still works
python -m src.cli token-status
python -m src.cli profile

# 2) Test Mode still works offline
python -m src.cli test-mode --no-llm

# 3) Live path smoke (safe: no customer send)
python -m src.cli triage --max 5 --no-llm
python -m src.cli summary --no-send --no-llm
```

If `token-status` is invalid:

```powershell
python -m src.cli connect-gmail --force
```

---

## Exact commands checklist (copy once)

```powershell
cd agents\email-assistant
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# OAuth
python -m src.cli connect-gmail
python -m src.cli token-status
python -m src.cli profile
python -m src.cli triage --max 15
python -m src.cli draft --message-id "<ID>"
python -m src.cli summary --no-send
python -m src.cli summary
python -m src.cli impact

# Offline demo
python -m src.cli test-mode
```

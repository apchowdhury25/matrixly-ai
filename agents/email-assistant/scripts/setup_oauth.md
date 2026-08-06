# Gmail OAuth setup (copy-paste ready)

One-time setup so **Email Assistant** can connect Gmail for small-business owners.  
Takes about **5–10 minutes** the first time; reconnect later is under **2 minutes**.

> Your emails stay in your Google account. Matrixly does **not** train on them.  
> Revoke anytime: https://myaccount.google.com/permissions

---

## Prerequisites

- Google account used for business mail (Gmail or Google Workspace)
- Python 3.10+ on the machine that will run the agent
- This repo: `agents/email-assistant`

---

## 1. Create or select a Google Cloud project

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project named e.g. `matrixly-email-assistant` (or reuse one)

## 2. Enable the Gmail API

1. **APIs & Services → Library**
2. Search **Gmail API** → **Enable**

## 3. OAuth consent screen

1. **Google Auth Platform** / **APIs & Services → OAuth consent screen**
2. User type:
   - **Internal** if this is a Google Workspace you admin
   - **External** + add yourself as a **Test user** otherwise (required while app is in Testing)
3. App name: `Matrixly Email Assistant`
4. User support email: your address
5. Developer contact: your address

### Scopes to add

Add these scopes (or the app will request them at runtime):

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.labels
```

**Plain English for owners:**

| Scope | Meaning |
|-------|---------|
| readonly | See your mail to sort it |
| modify | Apply labels (Urgent, Needs Reply, …) |
| labels | Create Matrixly folders/labels |
| send | Email **you** the daily brief only — not auto-replies to customers |

## 4. Create Desktop OAuth client

1. **Clients → Create Client**
2. Application type: **Desktop app**
3. Name: `email-assistant-desktop`
4. **Download** the JSON

> Desktop clients use a local loopback redirect (`http://localhost:<port>/`).  
> You do **not** need a public website redirect URI for this CLI flow.

## 5. Install credentials (never commit)

```powershell
cd agents\email-assistant
# Save the downloaded file exactly as:
#   data\credentials.json
```

Confirm:

```powershell
Test-Path data\credentials.json   # should be True
```

## 6. Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

```
EMAIL_BACKEND=gmail
EMAIL_PROFILE=gmail
# optional:
# GMAIL_CREDENTIALS_FILE=data/credentials.json
# GMAIL_TOKEN_FILE=data/token.json
```

## 7. Connect

```powershell
python -m src.cli connect-gmail
```

- Browser opens Google sign-in  
- Choose the business mailbox  
- Click **Allow**  
- Terminal shows **Success — Gmail connected**  
- Token saved to `data/token.json` (gitignored; refreshable)

## 8. Smoke test

```powershell
python -m src.cli token-status
python -m src.cli profile
python -m src.cli triage --max 10
python -m src.cli summary --no-send
```

---

## Revoke / re-authenticate cleanly

```powershell
# Remove local token
Remove-Item data\token.json -ErrorAction SilentlyContinue

# Or force re-consent
python -m src.cli connect-gmail --force
```

Also revoke the app in Google:  
https://myaccount.google.com/permissions → Matrixly Email Assistant → Remove access

---

## Security checklist

- [ ] `data/credentials.json` and `data/token.json` are **not** in git  
- [ ] `draft.auto_send` stays **false** (customer replies = drafts only)  
- [ ] Daily brief only goes to `EMAIL_SUMMARY_TO` / your own address  
- [ ] Prefer Workspace admin-approved OAuth app for production pilots  

---

## Next

Full testing matrix (happy path, deny consent, expired token, insufficient scopes):  
**[test_oauth.md](test_oauth.md)**

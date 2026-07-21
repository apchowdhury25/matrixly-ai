# Gmail OAuth setup (one-time)

These steps connect **Email Assistant** to your Gmail / Google Workspace mailbox
(`anwar.chowdhury@matrixbazaar.com` on **matrixbazaar.com** / **usmatrixbazaar.com**).

## 1. Create or select a Google Cloud project

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project named e.g. `matrixly-email-assistant` (or reuse an existing one)

## 2. Enable the Gmail API

1. **APIs & Services → Library**
2. Search **Gmail API** → **Enable**

## 3. OAuth consent screen

1. **Google Auth Platform → Branding / Audience** (or **APIs & Services → OAuth consent screen**)
2. User type:
   - **Internal** if this is a Google Workspace org you admin
   - **External** + add yourself as a **Test user** otherwise
3. App name: `Matrixly Email Assistant`
4. Support email: your address
5. Scopes to add:
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/gmail.labels`

## 4. Create Desktop OAuth client

1. **Clients → Create Client**
2. Application type: **Desktop app**
3. Name: `email-assistant-desktop`
4. Download the JSON

## 5. Install credentials

```powershell
cd C:\Users\anwar\projects\matrix-six\agents\email-assistant
# Save the downloaded file as:
#   data\credentials.json
```

## 6. Install Python deps and authenticate

```powershell
cd C:\Users\anwar\projects\matrix-six\agents\email-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.cli auth
```

A browser window opens. Sign in with the **usmatrixbazaar.com / matrixbazaar.com**
account you want the agent to manage. Token is stored at `data/token.json` (gitignored).

## 7. Smoke test

```powershell
python -m src.cli profile
python -m src.cli triage --no-labels --max 10
python -m src.cli summary --no-send
```

## Security notes

- **Drafts only** for replies — the agent never auto-sends customer email unless you change `draft.auto_send` (default `false`). Daily brief *does* send to your own `deliver_to` address.
- Keep `data/credentials.json` and `data/token.json` off git and backups you share.
- Prefer a Workspace admin-approved OAuth app for production pilots.

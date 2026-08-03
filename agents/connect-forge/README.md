# Matrixly ConnectForge (Twilio Connect Agent)

**Marketplace tile:** TWIL / CONN · **Domain:** SMS & Voice  
**Twilio-powered agent** for Houston SMBs — outbound/inbound SMS, Conversations threads, basic voice test calls, HITL outbound approval, and Test Mode for trial accounts.

Built for home services, HVAC, contractors, real estate, and local retail (Katy, Energy Corridor, and Greater Houston).

---

## Capabilities (MVP)

| Feature | Description |
|---------|-------------|
| **Outbound SMS** | Send from your Twilio number via official Python SDK |
| **Inbound SMS** | Webhook receives messages; AI (Grok) or rule templates reply |
| **Conversations** | Twilio Conversations API for multi-message threads (+ local history) |
| **Voice stub** | Outbound call with TwiML `<Say>` (Conversation Relay expandable later) |
| **Dashboard** | Messages, conversation SIDs, connection status, HITL queue |
| **Test Mode** | Only allow sends to pre-verified numbers (trial-safe) |
| **HITL** | Optional human approval before any outbound SMS |

---

## Quick start

```powershell
cd agents/connect-forge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env — see Twilio trial steps below
python scripts/smoke_test.py
python -m src.cli demo
python -m src.cli serve
```

| URL | Purpose |
|-----|---------|
| http://localhost:8802/ | Dashboard / test panel |
| http://localhost:8802/v1/health | Health |
| http://localhost:8802/docs | OpenAPI |

Default port: **8802**.

---

## Twilio trial account — step-by-step test guide

### 1. Create Twilio account

1. Sign up at [twilio.com](https://www.twilio.com/try-twilio)  
2. Open **Console** → copy **Account SID** and **Auth Token**  
3. Buy or use a trial **Phone Number** with SMS (+ voice if testing calls)

### 2. Verify your personal mobile (trial requirement)

**Console → Phone Numbers → Manage → Verified Caller IDs**  
Add and verify the handset you will text during tests.

### 3. Configure `.env`

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1713xxxxxxx
TWILIO_VERIFIED_NUMBERS=+1yourverifiedmobile
CONNECTFORGE_TEST_MODE=true
HITL_REQUIRE_OUTBOUND=true
XAI_API_KEY=                 # optional — smarter inbound replies
PUBLIC_BASE_URL=https://YOUR_TUNNEL.example
CONNECTFORGE_API_KEY=change-me-admin-key
```

**Never commit `.env`.** Only `.env.example` (empty secrets) is in git.

### 4. Smoke without network (optional)

```powershell
python scripts/smoke_test.py
```

Runs mock Twilio when credentials are empty — verifies HITL, Test Mode, and local stores.

### 5. Live send (Test Mode)

```powershell
python -m src.cli send --to +1YOUR_VERIFIED --body "ConnectForge test from Matrixly"
python -m src.cli serve
```

If HITL is on, approve in the dashboard **Approval queue** or:

```powershell
python -m src.cli pending
python -m src.cli approve --id hitl_...
```

### 6. Inbound webhook (local)

```powershell
# terminal 1
python -m src.cli serve

# terminal 2 — example with ngrok
ngrok http 8802
```

Set Twilio Messaging webhook (POST) to:

```text
https://YOUR_NGROK/v1/webhooks/sms
```

Text your Twilio number from the verified handset. ConnectForge stores the inbound message and queues/sends an AI or template reply.

### 7. Voice test call

```powershell
python -m src.cli call --to +1YOUR_VERIFIED
```

Or use the dashboard **Place call** button. This is a short TwiML Say call — not full Conversation Relay yet.

### Trial limitations (expected)

| Behavior | Why |
|----------|-----|
| Can only SMS verified numbers | Twilio trial policy |
| Message may include trial prefix | Twilio trial branding |
| Conversations create may fail | Product not enabled / permissions |
| Auth errors | Wrong SID/token |

ConnectForge surfaces these as clear operator errors — never invent delivery success.

---

## CLI

```powershell
python -m src.cli status
python -m src.cli demo
python -m src.cli send --to +1... --body "Hello"
python -m src.cli conversation --to +1... --body "Hi, thanks for contacting us"
python -m src.cli messages
python -m src.cli pending
python -m src.cli approve --id hitl_...
python -m src.cli call --to +1...
python -m src.cli serve --port 8802
```

---

## Houston SMB use cases

- Instant lead response for HVAC / home services in **Katy / Energy Corridor**  
- Appointment confirmation + reminder SMS  
- Missed-call recovery via text  
- Simple **English / Spanish** replies (auto-detect on inbound)

---

## Docker

```powershell
cd agents/connect-forge
docker build -t connect-forge .
docker run -d -p 8802:8802 --env-file .env -v ${PWD}/data:/app/data connect-forge
```

---

## Layout

```
agents/connect-forge/
  brand/voice.md
  config.yaml
  prompts/system.md
  src/
    integrations/twilio_client.py
    api/connect.py
    services/          # messages, hitl, audit
    llm.py             # modular Grok + rule fallback
    orchestrator.py
  static/dashboard/    # Matrixly dark test panel
  scripts/smoke_test.py
```

---

## Safety

- Credentials only via environment variables  
- Test Mode default **on**  
- HITL for outbound default **on**  
- No invented delivery stats  
- Audit log never stores Auth Tokens  

Product page: **`/connect-forge`**. Marketplace: **`/agents`**.  
Root catalog: [README.md](../../README.md).

# Shipping Assistant â€” User Guide

**For operators using the Matrixly.AI marketplace SHIP agent.**

HTML version (landing-linked): [`shipping-assistant-guide.html`](../../shipping-assistant-guide.html)  
Deploy page: [`shipping-assistant.html`](../../shipping-assistant.html)

---

## From the landing page

1. Open **Agents** â†’ `agents.html`
2. Find **Shipping Assistant** (SHIP Â· Live)
3. **Deploy Now** â†’ deploy page  
4. **User Guide** â†’ this guide (HTML)  
5. **See full logistics flow** â†’ `#logistics`

## Install (demo)

```powershell
cd C:\Users\anwar\projects\matrix-six\agents\shipping-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.cli demo
```

## Live ShipStation

```env
SHIPSTATION_API_KEY=...
SHIPSTATION_API_SECRET=...
```

```powershell
python -m src.cli status   # mode: live
python -m src.cli list
```

## Daily commands

| Goal | Command |
|------|---------|
| Exceptions | `python -m src.cli exceptions` |
| Notify drafts | `python -m src.cli notify-drafts` |
| WISMO draft | `python -m src.cli wismo --order ORDER` |
| Track | `python -m src.cli track --order ORDER` |
| Cancel (HITL) | `python -m src.cli propose-cancel --order ORDER` then `pending` / `approve` |
| Export | `python -m src.cli export` |

## HITL

- **Auto:** list, track, exceptions, WISMO/notify drafts  
- **Approve required:** cancel, address change, create/void label  

## Hermes

```powershell
hermes -s shipping-assistant -z "Scan shipping exceptions and draft WISMO for the worst order"
```

## Safety

Customer emails are **drafts only**. Never put API secrets in chat or git.


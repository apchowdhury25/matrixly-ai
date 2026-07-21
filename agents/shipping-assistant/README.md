# Shipping Assistant (Matrixly.AI)

**Marketplace tile:** SHIP · **Domain:** Logistics · **Hub:** ShipStation  

> Track shipments, notify stakeholders, and handle exceptions for logistics and distribution SMEs.

## Design summary

See **[DESIGN.md](DESIGN.md)**.

| Focus | Approach |
|--------|----------|
| System of record | **ShipStation** (multi-carrier UPS/FedEx/USPS, multi-channel orders) |
| Agent jobs | Track · exceptions · WISMO drafts · stakeholder notify drafts |
| Safety | **HITL** on cancel / address / labels; no auto-email to customers |

## Website

- Deploy page: `shipping-assistant.html`
- **User guide (HTML):** `shipping-assistant-guide.html` — full operator guide from the landing page
- **User guide (MD):** [USER_GUIDE.md](USER_GUIDE.md)
- Marketplace card: **Deploy Now** · **User guide** · **See full logistics flow**

## Capabilities (MVP)

| Command | What it does |
|---------|----------------|
| `list` / `demo` | List shipments (live API or demo data) |
| `track --order` / `--tracking` | Lookup one shipment |
| `exceptions` | Late / carrier exception scan |
| `wismo --order` | Customer WISMO reply **draft** |
| `notify-drafts` | Internal + customer notify drafts for exceptions |
| `propose-cancel --order` | Queue cancel (HITL) |
| `pending` / `approve` / `reject` | HITL queue |
| `export` | Snapshot JSON |

## Quick start

```powershell
cd C:\Users\anwar\projects\matrix-six\agents\shipping-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Works with zero ShipStation keys (demo mode)
python -m src.cli demo
python -m src.cli exceptions
python -m src.cli wismo --order MB-10418
python -m src.cli notify-drafts
python -m src.cli propose-cancel --order MB-10418
python -m src.cli pending
```

### Live ShipStation

1. ShipStation → Settings → Account → API Settings → generate Key + Secret  
2. Copy `.env.example` → `.env`  
3. Set `SHIPSTATION_API_KEY` and `SHIPSTATION_API_SECRET`  
4. `python -m src.cli status` → mode `live`

## HITL

Auto-allowed: list, track, exception scan, WISMO drafts.  
Requires approval: cancel, address update, create/void label (handlers stubbed until approved for live mutate).

## Hermes

```powershell
hermes -s shipping-assistant -z "Scan shipping exceptions and draft WISMO for the worst one"
```

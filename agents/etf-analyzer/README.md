# ETF Portfolio Analyzer

**Matrixly Finance Productivity Agent** · Status: **Live** · Port **8797**

Clear, data-driven, tax-aware ETF analysis using **free public market data** (Yahoo Finance primary). Default sample: **QQQI** (NEOS Nasdaq-100 High Income ETF). Optional Notion knowledge-layer save.

## Analysis framework

1. **Live Snapshot** — price, change, volume, 52w range, AUM, expense ratio  
2. **Yield Projections** — TTM yield, distribution estimate, annualized context  
3. **NAV Risk** — NAV, premium/discount, structural notes  
4. **Tax-Aware Strategies** — distribution character, efficiency, account framing (educational)  
5. **Notion** — offer to save structured report  

No paid API keys required for market data.

## Quick start

```powershell
cd agents/etf-analyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli serve
```

| URL | Purpose |
|-----|---------|
| http://localhost:8797 | Dashboard (auto-runs QQQI) |
| http://localhost:8797/v1/health | Health |
| http://localhost:8797/docs | OpenAPI |

### CLI

```powershell
python -m src.cli analyze          # default QQQI
python -m src.cli analyze SPY
python -m src.cli chat --message "analyze JEPI"
python -m src.cli analyze QQQI --notion
```

### Optional Notion

```env
NOTION_API_KEY=secret_...
NOTION_PARENT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Without Notion, “save” writes to `data/notion/` locally.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/analyze` | `{ "ticker": "QQQI", "save_to_notion": false }` |
| POST | `/v1/chat` | Conversational analyze / save |
| POST | `/v1/reports/{id}/notion` | Save existing report |
| GET | `/v1/admin/status` | Admin status |

Headers: `X-Widget-Key` or `X-API-Key`.

## Embed

```html
<script
  src="http://127.0.0.1:8797/static/widget/embed.js"
  data-api="http://127.0.0.1:8797"
  async>
</script>
```

## Disclaimer

Educational information only — not personalized investment, tax, or legal advice.

Product page: **`/etf-analyzer`**.

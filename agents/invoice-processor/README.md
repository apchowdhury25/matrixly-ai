# Matrixly Invoice Processor

**Marketplace tile:** INV · **Domain:** Finance / AP  
**Pydantic AI multi-agent system** that extracts invoice data from PDFs/email, matches Purchase Orders, flags discrepancies, and recommends Approve / Needs Review / Reject with human-in-the-loop.

> Complements **InvoiceForge** (inbox watch + AR + dashboard). Invoice Processor is the typed multi-agent core for PO matching and payment readiness.

---

## Multi-agent architecture

```
                 ┌──────────────────────────┐
                 │   InvoiceOrchestrator    │
                 │  (pipeline or AI agent)  │
                 └────────────┬─────────────┘
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
 ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
 │ ExtractorAgent  │ │  MatcherAgent   │ │  ReviewerAgent  │
 │ PDF/email→data  │ │  PO + rules     │ │  Approve/HITL   │
 └─────────────────┘ └─────────────────┘ └─────────────────┘
```

| Agent | Responsibility | Output |
|-------|----------------|--------|
| **InvoiceExtractorAgent** | Structured extraction from PDF / email / text | `InvoiceData` |
| **InvoiceMatcherAgent** | PO lookup + discrepancy rules | `MatchingResult` |
| **InvoiceReviewerAgent** | Final recommendation + HITL flags | `ReviewDecision` |
| **InvoiceOrchestrator** | Sequences specialists (tools or pipeline) | `InvoiceProcessingResult` |

### Design decisions

1. **Specialists own domain logic; orchestrator only sequences** — extract/match/review can be unit-tested alone.
2. **Deterministic pipeline is the production default** — fixed Extract→Match→Review order, audit-friendly.
3. **Pydantic AI agent tools wrap the same stages** — for conversational AP desk UIs.
4. **Rule engines under tools** — amount/vendor/qty checks are code, not vibes; LLM explains, rules decide baseline.
5. **Dependency injection** — `InvoiceProcessorDeps` holds PO store, PDF, email, accounting connectors. Swap stubs for Gmail / QuickBooks / NetSuite without touching agents.
6. **Offline-first demos** — without `XAI_API_KEY`, rule extraction + rule matching still produce full results (CI smoke).

---

## Quick start

```powershell
cd agents/invoice-processor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python scripts/run_example.py
python -m src.cli demo
python -m src.cli serve
```

| URL | Purpose |
|-----|---------|
| http://localhost:8799/v1/health | Health |
| http://localhost:8799/docs | OpenAPI |
| POST /v1/process | Run pipeline |

Default port: **8799**.

### `.env`

```env
XAI_API_KEY=
INVOICE_PROCESSOR_MODEL=xai:grok-4.5
INVOICE_PROCESSOR_MODEL_FALLBACK=xai:grok-4-1-fast-reasoning
AMOUNT_REVIEW_THRESHOLD=10000
```

---

## End-to-end example

```python
import asyncio
from src.deps import InvoiceProcessorDeps
from src.models import InvoiceInput, SourceType
from src.pipeline import process_invoice

async def main():
    deps = InvoiceProcessorDeps.create()
    payload = InvoiceInput(
        text=open("samples/invoice_acme_match.txt").read(),
        source_type=SourceType.text,
    )
    result = await process_invoice(deps, payload)
    print(result.review.action, result.requires_human)
    print(result.matching.discrepancies)

asyncio.run(main())
```

### Workflow

1. Orchestrator / pipeline receives invoice (PDF path, email id, or text)
2. **Extractor** → `InvoiceData`
3. **Matcher** → `MatchingResult` + `Discrepancy[]`
4. **Reviewer** → `ReviewDecision` (approve / needs_review / reject)
5. Returns `InvoiceProcessingResult` (+ optional accounting prep stub)

---

## Core models

- `InvoiceLineItem`, `InvoiceData`
- `PurchaseOrder`, `PurchaseOrderLine`
- `Discrepancy` (type, severity, field, description)
- `MatchingResult`
- `ReviewDecision`
- `InvoiceProcessingResult`

---

## Extending connectors

| Interface | Stub today | Later |
|-----------|------------|--------|
| `EmailClient` | `StubEmailClient` | Gmail API (message + attachments) |
| `PdfExtractor` | pypdf text | Vision OCR via Grok |
| `PurchaseOrderStore` | JSON files in `data/pos/` | NetSuite / QBO PO APIs |
| `AccountingConnector` | JSON payment prep | QuickBooks Bill / NetSuite vendor bill |

Implement the same Protocol methods and inject via `InvoiceProcessorDeps.create(...)`.

---

## Layout

```
agents/invoice-processor/
  config.yaml
  samples/
  scripts/smoke_test.py
  scripts/run_example.py
  src/
    models.py              # strong types
    deps.py                # DI container
    pipeline.py            # Extract → Match → Review
    agents/
      extractor.py
      matcher.py
      reviewer.py
      orchestrator.py
    tools/                 # PDF, PO store, rule engines
    connectors/            # email + accounting stubs
    cli.py
    main.py                # FastAPI
```

Product page: **`/invoice-processor`**.

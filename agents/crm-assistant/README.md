# CRM Assistant (Matrixly.AI)

**Marketplace tile:** CRM · **Domain:** Sales · **Status:** MVP pilot  

> Update contacts, log activities, and keep pipeline hygiene automated across your sales stack.

## Design decision

See **[DESIGN.md](DESIGN.md)**.

| Principle | Implementation |
|-----------|----------------|
| Extract from notes/meetings | Heuristic + optional Grok |
| Structured CRM objects | Contact / Company / Deal / Activity |
| Safe automation | **HITL approval queue** + Salesforce-shaped export |

## Capabilities (MVP)

| Capability | Command |
|------------|---------|
| Process meeting/email note → proposed writes | `note` |
| List pending CRM writes | `pending` |
| Approve / reject writes | `approve` / `reject` / `approve-all` |
| Pipeline hygiene report | `hygiene` |
| Salesforce JSON/CSV export | `export` |
| Direct contact / activity | `contact` / `activity` |
| Demo seed + sample meeting | `demo` |

## Quick start

```powershell
cd C:\Users\anwar\projects\matrix-six\agents\crm-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m src.cli demo --no-llm
python -m src.cli pending
python -m src.cli approve-all
python -m src.cli hygiene
python -m src.cli export
```

Process a free-text note:

```powershell
python -m src.cli note -t "Called Priya Shah ops@transocean-freight.com. Next step: send pilot SOW." --no-llm
python -m src.cli pending
python -m src.cli approve --id wrt_xxxxx
```

## HITL policy

- Default: **queue** all CRM mutations  
- `--apply` or `approve` applies to local store  
- Salesforce live API optional later; export always available  

## Multi-agent

| Upstream | Handoff |
|----------|---------|
| Lead Qualifier | Hot leads → contacts/deals |
| Email Assistant | Log email activities from triage |

## Hermes

```powershell
hermes -s crm-assistant -z "Run CRM demo hygiene and list pending writes"
```

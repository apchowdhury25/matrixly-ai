# CRM Assistant — Design Notes

## Product goals

| Capability | Matrixly MVP |
|------------|--------------|
| Extract contact fields from notes/meetings/emails | Yes |
| Update CRM contact/company records | Export + local store; optional API later |
| Log activities (call/email/meeting) | Yes |
| Flag missing/inconsistent data (don’t invent) | Yes (HITL) |
| Pipeline hygiene | Stale deals, missing owner, missing next step |
| Multi-system shape | Salesforce-shaped JSON/CSV; HubSpot-compatible later |

## Design principles

1. **Extract** from free text (heuristic + optional Grok)  
2. **Structure** as Contact / Company / Deal / Activity  
3. **Human-in-the-loop** — queue writes; approve before apply  
4. **Orchestrate** with Lead Qualifier (inbound) and Email Assistant (mailbox)  

## Positioning

> Matrixly **proposes** contact, activity, and deal updates — you **approve** before CRM records change.

## MVP scope

1. Update contacts (upsert by email)  
2. Log activities  
3. Pipeline hygiene report  
4. Salesforce-shaped export + local JSON store  
5. HITL approve/reject proposed writes  
6. Sample notes + free-text “after call” ingest  

# Lead Qualifier — Product Roadmap

**Goal:** Deepen Matrixly Lead Qualifier for credible SMB pilots **without** auto-sending outreach.

**North star differentiator (do not dilute):**

| Always true | Meaning |
|-------------|---------|
| **Human-in-the-loop for outbound** | Sequences are drafts; send requires explicit approval |
| **Transparent scoring** | Reasons + scores visible; ICP weights editable |
| **Operator ownership** | Runs on customer stack (Hermes / local / pilot deploy) |
| **SMB / pilot honesty** | No unmeasured conversion claims until proven |

**Capability areas to expand (selectively):**

- Always-on inbound capture  
- Deeper enrichment  
- Live CRM write-back  
- Smart routing / SLA  
- First-touch personalization + meeting booking **with approval**  
- Lightweight funnel analytics  

---

## Priority legend

| Priority | Definition | Horizon |
|----------|------------|---------|
| **P0** | Must have for pilot credibility | 2–4 weeks |
| **P1** | Differentiated parity for Growth tier | 4–10 weeks |
| **P2** | Later (nice; avoid scope creep) | Backlog |

---

## P0 — Pilot-ready (keep HITL)

### P0.1 — Approval queue for outreach

**What:** Every sequence touch lands in an **Approval Queue**, never auto-send.

| Field | Spec |
|-------|------|
| States | `drafted` → `approved` → `sent` / `rejected` / `edited` |
| Actions | Approve, edit body/subject, reject, snooze |
| Channels | CLI + simple HTML/dashboard or Hermes chat |
| Audit | Who approved, when, final text |

**HITL guard:** `outreach.auto_send` stays `false`.

### P0.2 — Live Salesforce write-back (optional path)

Modes: `export` (default JSON/CSV) | `api` (upsert Lead). Dry-run flag required.

### P0.3 — Always-on Gmail inbound watcher

Hermes cron; auto-**qualify** OK; auto-**reply** not OK.

### P0.4 — Form / webhook inbound

`POST /leads` for website Contact / Demo forms.

### P0.5 — Operator dashboard (thin)

New/hot leads, pending approvals, last SF export.

### P0.6 — Enrichment upgrade

Pluggable providers with confidence labels; never invent revenue or named execs.

---

## P1 — Competitive depth (still HITL)

| Item | HITL lock |
|------|-----------|
| **P1.1** Smart routing (hot→AE, warm→SDR) | Assignment automated; first commercial email gated |
| **P1.2** SLA alerts | Nudge **operator**, not prospect |
| **P1.3** Pre-approved template allowlist | Semi-auto touch 1 **off by default** |
| **P1.4** Meeting booking links in CTA | Human still sends the email |
| **P1.5** Dedup + CRM hygiene | Match by email |
| **P1.6** Funnel mini-analytics | Real pilot metrics only |
| **P1.7** Multi-agent handoff | Email Assistant / CRM Assistant |

---

## P2 — Backlog

Chat widget live qualifier, voice, predictive ML scoring, unbounded nurture, browser computer-use agents.

---

## Explicit non-goals

| Do **not** | Why |
|------------|-----|
| Default auto-send sequences | Undermines trust for SMB pilots |
| Opaque scores without reasons | Matrixly sells transparency |
| Claiming full SDR replacement | Sell **copilot for sales** |

**Positioning line:**

> Matrixly **co-pilots** the SDR: score, enrich, draft, route — humans approve the send.

---

## Success metrics (30-day pilot)

| Metric | Target |
|--------|--------|
| Time-to-first-score (inbound) | &lt; 5 min |
| % hot leads with draft ready | 100% |
| % outbound with human approval | **100%** (or ≥95% if semi-auto opt-in) |
| SF records without manual CSV | ≥ 80% of qualified |
| False hot rate (rep feedback) | &lt; 25% |

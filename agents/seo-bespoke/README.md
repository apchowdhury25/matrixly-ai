# Matrixly SEO-Bespoke

**Marketplace tile:** SEO (Higher-tier) · **Domain:** Marketing / Custom SEO Agents  
**Custom SEO agent factory** for US SMBs: interactive business quiz → **Business SEO Profile Summary** → **fully specialized Python agent package**.

Sits **alongside** [SEOForge](../seo-forge) — do not confuse the two:

| | **SEOForge** | **SEO-Bespoke** |
|--|--------------|-----------------|
| Role | Ready-to-run SEO crew | Builds a *new* agent for one business |
| Input | Brief / chat | Multi-step quiz |
| Output | Content, plans, local packs | Profile + **custom agent source code** |
| Port | 8798 | **8799** |

Designed for non-technical owners who want something that feels built *for their HVAC / dental / legal / retail business* — not a thin generic wrapper.

---

## Parallel graph (20 nodes max)

```
N1  Quiz Orchestrator
     │ fan-out (parallel)
     ├─ N2 Domain  N3 Industry  N4 Business  N5 Customers  N6 Location  N7 Goals
     │ converge
N8  Profile Synthesizer
     ├─ N9 Summary Verifier          ← isolated context (no chat history)
     └─► N10 Code Architect
              │ fan-out (parallel)
              ├─ N11 Research  N12 Brand  N13 Local  N14 Content  N15 Tracking  N16 ROI
              │ converge
         N17 Code Assembler + Config Writer
              ├─ N18 Safety & HITL Verifier  ← isolated
              └─► N19 Deployment Package Builder
                       └─► N20 Final Integration & Smoke-Test
```

**Principles:** real data-dependency edges only · width over depth · verifiers get clean isolated inputs · never invent stats/reviews/rankings · HITL before package deploy.

---

## Capabilities

| Area | What SEO-Bespoke does |
|------|------------------------|
| **Interactive quiz** | Domain, industry, business, customers, location, goals (web + CLI) |
| **Profile summary** | Professional Markdown + JSON Business SEO Profile |
| **Codegen** | Specialized FastAPI agent modules for *that* business |
| **HITL** | Approval queue before treating package as deploy-ready |
| **Keywords** | Tracker with **owner-supplied** ranks only |
| **ROI** | Hours / leads / revenue cards (owner-reported) |
| **Re-run** | Quiz again or regenerate from saved profile |

---

## Quick start

```powershell
cd agents/seo-bespoke
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m src.cli demo
python -m src.cli serve
```

| URL | Purpose |
|-----|---------|
| http://localhost:8799/v1/health | Health |
| http://localhost:8799/static/dashboard/index.html | Interactive dashboard |
| http://localhost:8799/docs | OpenAPI |

Default port: **8799**.

### `.env`

```env
SEOBESPOKE_API_KEY=your-admin-secret
SEOBESPOKE_WIDGET_KEY=pk_live-your-site-key
XAI_API_KEY=                 # optional — smarter synthesis when set
HITL_MODE=external_only
CORS_ORIGINS=http://localhost:8080,https://matrixly.world
```

---

## Dashboard tabs

1. **Home** — product overview + live graph waves  
2. **Quiz** — 6-step wizard → generate custom agent  
3. **Profile** — Business SEO Profile Summary (Markdown)  
4. **Package** — generated agent paths under `data/packages/`  
5. **Approval** — HITL gate before deploy  
6. **Keywords** — tracker (no invented ranks)  
7. **ROI** — hours / leads / revenue  
8. **Chat** — plain-English owner assistant  

---

## CLI

```powershell
python -m src.cli status
python -m src.cli graph
python -m src.cli demo
python -m src.cli quiz                    # interactive CLI quiz
python -m src.cli generate samples/quiz_answers.json
python -m src.cli regenerate --id prof_...
python -m src.cli profiles
python -m src.cli packages
python -m src.cli pending
python -m src.cli approve --id hitl_...
python -m src.cli keywords
python -m src.cli roi
python -m src.cli chat --text "show profile"
python -m src.cli serve --port 8799
```

---

## Using a generated package

After a successful run (and HITL approve):

```powershell
cd data/packages/pkg_<id>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/smoke_test.py
python -m agent.cli status
python -m agent.cli research
python -m agent.cli local
python -m agent.cli content --topic "AC repair"
python -m agent.cli serve
```

The package includes specialized modules:

- `agent/modules/research_planner.py`
- `agent/modules/brand_voice.py`
- `agent/modules/local_seo.py`
- `agent/modules/content_engine.py`
- `agent/modules/keyword_tracker.py`
- `agent/modules/roi_cards.py`
- `brand/voice.md` + `profile/business_seo_profile.md`

---

## Guardrails

- Never invent statistics, reviews, rankings, credentials, or guarantees  
- Never claim #1 or specific traffic numbers without owner data  
- HITL required before package is treated as deploy-ready  
- Keyword ranks are **owner-supplied only**  
- Client data stays local under `data/`  

---

## Docker

```powershell
cd agents/seo-bespoke
docker build -t seo-bespoke .
docker run -d -p 8799:8799 --env-file .env -v ${PWD}/data:/app/data -v ${PWD}/brand:/app/brand seo-bespoke
```

---

## Layout

```
agents/seo-bespoke/
  brand/voice.md
  config.yaml
  prompts/              # system, synthesizer, verifier
  samples/quiz_answers.json
  scripts/smoke_test.py
  src/
    graph/              # topology, executor, 20 node handlers
    codegen/            # package assembler
    api/                # FastAPI routes
    services/           # runs, profiles, packages, hitl, keywords, roi
    memory/             # brand voice
    orchestrator.py
  static/dashboard/     # dark Matrixly UI
  data/packages/        # generated custom agents land here
```

---

## Embed on matrixly.world

```html
<iframe
  src="https://YOUR_SEOBESPOKE_HOST/static/dashboard/index.html"
  title="SEO-Bespoke"
  style="width:100%;min-height:900px;border:1px solid #1e2a3a;border-radius:12px;"
></iframe>

<script
  src="https://YOUR_SEOBESPOKE_HOST/static/widget/embed.js"
  data-api="https://YOUR_SEOBESPOKE_HOST"
  data-key="pk_live_your-site-key"
  async>
</script>
```

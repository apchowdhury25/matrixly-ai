# Matrixly SEOForge

**Marketplace tile:** SEO · **Domain:** Marketing / Local SEO  
**Agentic SEO & brand marketing agent** for US SMBs: research → strategy → brand-voice content → local SEO → HITL approval → measure ROI.

Designed for non-technical owners (HVAC, contractors, Shopify, pro services, dental, legal, local retail) who want organic + “near me” growth without hiring an agency.

## Capabilities

| Area | What SEOForge does |
|------|--------------------|
| **Research & strategy** | Local intent, keyword gaps, 30-day prioritized plans |
| **Content** | Service pages, blogs, location pages, FAQs — title/meta/schema/social |
| **Local SEO** | GBP posts, Q&A, citations checklist, review response templates |
| **Optimization** | On-page audits owners can act on |
| **HITL publish** | Approval queue before WordPress draft / Buffer / local export |
| **ROI** | Hours saved, leads, revenue → Matrixly ROI dashboard feed |
| **Brand voice** | Trainable voice memory injected into every generation |

Stack: **Python + FastAPI**, optional Grok (xAI), dark Matrixly dashboard (chat, queue, keywords, brand, ROI).

---

## Quick start

```powershell
cd agents/seo-forge
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
| http://localhost:8798/v1/health | Health |
| http://localhost:8798/static/dashboard/index.html | Interactive dashboard |
| http://localhost:8798/docs | OpenAPI |

Default port: **8798**.

### `.env`

```env
SEOFORGE_API_KEY=your-admin-secret
SEOFORGE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=                 # optional — smarter writing & chat
PUBLISH_BACKEND=local        # local | buffer | hootsuite | wordpress
CORS_ORIGINS=http://localhost:8080,https://matrixly.world
```

---

## Dashboard tabs

1. **Chat** — conversational onboarding + goals; proposes 30-day plan  
2. **Content** — generate packages, local SEO, audits, demo  
3. **Approval queue** — HITL gate before publish  
4. **Keywords** — tracker with rank Δ  
5. **Brand voice** — train tone, avoid list, claims  
6. **ROI** — hours saved / leads / revenue cards  

---

## Pipeline

```
Business brief / chat
  → Researcher (keywords, gaps, near-me)
  → Strategist (30-day plan)  OR  Writer / Local SEO / Auditor
  → Export under data/outputs/<job_id>/
  → HITL review (content & local packages)
  → Schedule / Publish (local, Buffer, WordPress draft)
  → ROI snapshot → Matrixly dashboard feed
```

---

## Guardrails

- Never publish without human approval  
- Never invent statistics, reviews, credentials, or guarantees  
- Google-guideline aware; compliance-sensitive content escalates to review  
- Client data stays local to the agent workspace  

---

## Embed on matrixly.world

```html
<iframe
  src="https://YOUR_SEOFORGE_HOST/static/dashboard/index.html"
  title="SEOForge"
  style="width:100%;min-height:900px;border:1px solid #1e2a3a;border-radius:12px;"
></iframe>

<script
  src="https://YOUR_SEOFORGE_HOST/static/widget/embed.js"
  data-api="https://YOUR_SEOFORGE_HOST"
  data-key="pk_live_your-site-key"
  async>
</script>
```

---

## CLI

```powershell
python -m src.cli status
python -m src.cli plan samples/business_brief.txt
python -m src.cli generate samples/business_brief.txt --type service_page --keyword "AC repair Austin"
python -m src.cli chat --text "Help me rank for plumber near me in Dallas"
python -m src.cli pending
python -m src.cli approve --id hitl_...
python -m src.cli publish --id job_... --targets local
python -m src.cli serve --port 8798
```

---

## Docker

```powershell
cd agents/seo-forge
docker build -t seo-forge .
docker run -d -p 8798:8798 --env-file .env -v ${PWD}/data:/app/data -v ${PWD}/brand:/app/brand seo-forge
```

---

## Layout

```
agents/seo-forge/
  brand/voice.md
  config.yaml
  prompts/          # system, researcher, strategist, writer, local_seo, auditor
  src/
    agents/         # specialized crew
    api/            # FastAPI routes
    memory/         # brand voice + profile
    services/       # store, hitl, keywords, roi, sessions
    orchestrator.py
  static/dashboard/ # interactive UI
  scripts/smoke_test.py
```

Product page: **`/seo-forge`** (`seo-forge/index.html`).

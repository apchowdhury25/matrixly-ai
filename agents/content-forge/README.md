# Matrixly ContentForge

**Marketplace tile:** CONT · **Domain:** Marketing / Content  
**Embeddable AI agent** that creates and repurposes marketing content for SMBs: long-form in → SEO blog, social, newsletter, ads → HITL review → export/schedule/publish.

## Crew (specialized roles)

| Role | Responsibility |
|------|----------------|
| **Researcher** | Summary, audience, SEO keywords, angles, CTAs |
| **Writer** | Full SEO blog draft (title, meta, slug, body) |
| **Editor** | Brand voice, clarity, quality score |
| **Repurposer** | LinkedIn, X thread, Instagram, newsletter, ads, follow-on ideas |

Stack: **Python + FastAPI**, optional Grok (xAI), brand voice file, dark Matrixly workspace UI.

---

## Quick start

```powershell
cd agents/content-forge
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
| http://localhost:8792/v1/health | Health |
| http://localhost:8792/static/workspace/index.html | Content workspace |
| http://localhost:8792/docs | OpenAPI |

Default port: **8792**.

### `.env`

```env
CONTENTFORGE_API_KEY=your-admin-secret
CONTENTFORGE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=                 # optional — smarter writing
PUBLISH_BACKEND=local        # local | buffer | hootsuite | wordpress
CORS_ORIGINS=http://localhost:8080,https://matrixly.world
```

---

## Brand voice configuration

1. Edit **`brand/voice.md`** (tone, vocabulary, audience, principles).  
2. Optional knobs in **`config.yaml`** under `brand:` (tone list, avoid list, keywords).  
3. Restart the server after changes.

The brand file is injected into Researcher / Writer / Editor / Repurposer prompts (or used by rule-based fallbacks when no API key).

---

## Pipeline

```
Long-form source
  → Researcher
  → Writer (SEO blog)
  → Editor (quality + brand)
  → Repurposer (multi-channel)
  → Export files under data/outputs/<job_id>/
  → HITL review (default)
  → Schedule / Publish (local, Buffer, Hootsuite, WordPress)
```

---

## Integrations

| Backend | Behavior |
|---------|----------|
| **local** (default) | Markdown/JSON exports + publish manifest |
| **buffer** | Create updates via Buffer API when token + profile IDs set |
| **hootsuite** | Message create stub; falls back to local on failure |
| **wordpress** | Creates a **draft** post via REST + app password |

```env
PUBLISH_BACKEND=wordpress
WORDPRESS_SITE_URL=https://yourblog.com
WORDPRESS_USERNAME=editor
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## Embed on matrixly.world

### Workspace iframe

```html
<iframe
  src="https://YOUR_CONTENTFORGE_HOST/static/workspace/index.html"
  title="ContentForge"
  style="width:100%;min-height:800px;border:1px solid #1e2a3a;border-radius:12px;">
</iframe>
```

### Floating launcher

```html
<script
  src="https://YOUR_CONTENTFORGE_HOST/static/widget/embed.js"
  data-api="https://YOUR_CONTENTFORGE_HOST"
  async>
</script>
```

Unlock the workspace with `CONTENTFORGE_API_KEY` or `CONTENTFORGE_WIDGET_KEY`.

---

## CLI

```text
python -m src.cli status
python -m src.cli demo
python -m src.cli generate samples/source_blog.txt
python -m src.cli ideas --text "shipping automation for ecom"
python -m src.cli list
python -m src.cli pending
python -m src.cli approve --id hitl_...
python -m src.cli publish --id job_... --targets local
python -m src.cli usage
python -m src.cli serve --port 8792
```

---

## Deployment (VPS)

```bash
cd agents/content-forge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --host 127.0.0.1 --port 8792
```

**Docker:**

```bash
docker build -t content-forge .
docker run -d -p 8792:8792 --env-file .env -v $PWD/data:/app/data -v $PWD/brand:/app/brand content-forge
```

TLS reverse proxy recommended. Marketing site stays static; ContentForge is a separate service.

---

## Security

- Change default API/widget keys  
- Keep HITL on before publish in production  
- Never commit `.env` or CMS tokens  
- Restrict CORS to your domains  

---

## Project layout

```
agents/content-forge/
├── brand/voice.md
├── config.yaml
├── prompts/                 # researcher, writer, editor, repurposer
├── samples/
├── static/workspace/        # embeddable UI
├── static/widget/embed.js
├── scripts/smoke_test.py
└── src/
    ├── main.py
    ├── orchestrator.py
    ├── agents/
    ├── integrations/publish.py
    ├── services/
    └── api/
```

Product page: **`content-forge.html`** (repo root).

---

## License

Same as parent Matrixly repository (MIT).

# Matrixly SocialForge

**Marketplace tile:** SOCIAL · **Domain:** Marketing / Community  
**Embeddable AI agent** that manages social content and engagement for SMBs: multi-platform drafts, optimal scheduling, inbox monitoring, brand-voice replies, insights — with **human approval before posting**.

## Pipeline (CrewAI-style crew)

```
Idea / brief
  → Composer (LinkedIn, X, Instagram, Facebook, Threads)
  → Scheduler (optimal windows in brand timezone)
  → HITL review → publish (local | Buffer | Meta | LinkedIn)
  → Monitor inbox → Reply drafts (HITL) → Insights
```

Stack: **Python + FastAPI**, optional Grok, brand voice memory (`brand/voice.md` + notes), dark calendar/inbox UI.

Default port: **8794**.

---

## Quick start

```powershell
cd agents/social-forge
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
| http://localhost:8794/v1/health | Health |
| http://localhost:8794/static/calendar/index.html | Social calendar + inbox |
| http://localhost:8794/docs | OpenAPI |

### `.env`

```env
SOCIALFORGE_API_KEY=your-admin-secret
SOCIALFORGE_WIDGET_KEY=pk_live_your-site-key
XAI_API_KEY=                 # optional smarter composition
PUBLISH_BACKEND=local
HITL_AUTO_APPROVE=false
CORS_ORIGINS=http://localhost:8080,https://matrixly.world
```

---

## Account connections

### Local (default)

Posts and publish actions write JSON under `data/publish/` — safe for demos and smoke tests.

### Buffer

1. Create a Buffer app / access token.  
2. Set `BUFFER_ACCESS_TOKEN` and `BUFFER_PROFILE_IDS` (comma-separated).  
3. Set `PUBLISH_BACKEND=buffer` or pass `"backend": "buffer"` to `POST /v1/publish`.

### Meta (Facebook / Instagram Graph)

```env
META_ACCESS_TOKEN=
META_PAGE_ID=
META_IG_USER_ID=
PUBLISH_BACKEND=meta
```

Facebook Page feed posts use Graph `/feed`. Instagram live media requires the media-container flow; SocialForge logs captions when media is not attached.

### LinkedIn

```env
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_ORG_URN=urn:li:organization:…   # or LINKEDIN_PERSON_URN
PUBLISH_BACKEND=linkedin
```

Uses UGC Posts API for text shares. Company pages need the org URN and appropriate scopes.

### Brand voice memory

| File | Role |
|------|------|
| `brand/voice.md` | Primary voice guide (edit and restart) |
| `data/memory/notes.json` | Operator notes via `POST /v1/brand/notes` |

---

## API (high level)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/compose` | widget/API | Compose + schedule campaign |
| POST | `/v1/demo` | widget/API | Sample idea pipeline |
| GET | `/v1/campaigns` | API | List campaigns |
| GET | `/v1/calendar` | API | Scheduled slots |
| POST | `/v1/publish` | API | Publish approved campaign |
| POST | `/v1/monitor` | API | Classify inbox (demo seed if empty body) |
| POST | `/v1/replies` | API | Draft replies (+ HITL) |
| GET/POST | `/v1/insights` | API | Performance insights |
| GET | `/v1/admin/hitl` | API | Pending approvals |
| POST | `/v1/admin/hitl/{id}/approve` | API | Approve post/reply |
| GET | `/v1/admin/usage` | API | Usage / cost |
| GET | `/v1/admin/audit` | API | Audit trail |

Headers: `X-API-Key` (admin) or `X-Widget-Key` (compose/demo).

---

## CLI

```powershell
python -m src.cli status
python -m src.cli compose samples/idea.txt --platforms linkedin,x,instagram
python -m src.cli monitor
python -m src.cli replies
python -m src.cli insights
python -m src.cli pending
python -m src.cli approve --id hitl_…
python -m src.cli publish --id cmp_… --backend local
python -m src.cli serve --port 8794
```

---

## Embed code (matrixly.world)

```html
<iframe
  src="https://YOUR_SOCIALFORGE_HOST/static/calendar/index.html"
  title="SocialForge"
  style="width:100%;min-height:800px;border:1px solid #1e2a3a;border-radius:12px;"
></iframe>

<script
  src="https://YOUR_SOCIALFORGE_HOST/static/widget/embed.js"
  data-api="https://YOUR_SOCIALFORGE_HOST"
  data-key="pk_live_your-site-key"
  async>
</script>
```

---

## Deployment

### Local / VPS

```powershell
cd agents/social-forge
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8794
```

Put TLS termination (Caddy/nginx) in front. Restrict CORS to your site origins. Rotate `SOCIALFORGE_API_KEY`.

### Docker

```bash
docker build -t social-forge .
docker run -d -p 8794:8794 --env-file .env -v $PWD/data:/app/data social-forge
```

### Production checklist

- [ ] HITL left **on** (`HITL_AUTO_APPROVE=false`) for public posts  
- [ ] Brand voice reviewed in `brand/voice.md`  
- [ ] Publish backend credentials stored only in env / secret manager  
- [ ] Audit + usage directories backed up  
- [ ] Widget key used on public site; admin key never embedded in HTML  

---

## Project structure

```
agents/social-forge/
  brand/voice.md
  config.yaml
  prompts/           # composer, scheduler, monitor, reply, insights
  samples/idea.txt
  scripts/smoke_test.py
  src/
    agents/          # crew roles
    api/             # FastAPI routers
    integrations/    # Buffer / Meta / LinkedIn / local
    memory/          # brand voice + notes
    services/        # audit, usage, hitl, store
    orchestrator.py
    main.py
    cli.py
  static/
    calendar/index.html
    widget/embed.js
```

Product page: **`/social-forge`** (`social-forge/index.html`).

---

## Safety

Social posts and customer-facing replies default to **human review**. Publishing while `pending_review` is blocked. Local backend never hits external networks without credentials.

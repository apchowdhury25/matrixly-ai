# Matrixly UI QA Framework

UI quality assurance for the **Matrixly static marketing site** and the **self-hosted Observability & Crawl stack** used by agentic products (SEOForge, ContentForge, Lead Qualifier, SEO-Bespoke, PipelineForge, and related agents).

| Piece | Path |
|-------|------|
| QA Admin console (authorized) | [`../admin/`](../admin/) → `/admin` |
| Observability module (browser) | [`../js/admin-observability.js`](../js/admin-observability.js) |
| Self-hosted stack (Docker) | [`../infra/observability/`](../infra/observability/) |
| Python automation | this folder (`qa/`) |
| CI workflow | [`.github/workflows/ui-qa.yml`](../.github/workflows/ui-qa.yml) |

## Stack (Python equivalents of common enterprise tools)

| You asked for | Matrixly QA uses |
|---------------|------------------|
| **Selenium** | `selenium` + `webdriver-manager` |
| **Playwright** | `playwright` (Chromium in CI) |
| **Cucumber** | `pytest-bdd` + Gherkin `features/*.feature` |
| **TestNG** | `pytest` class suites + markers (`@pytest.mark.smoke`) |
| **Git / CI-CD** | GitHub Actions `ui-qa.yml` on PR + main |

> **TestNG** and classic **Cucumber-JVM** are Java. This repo is Python-first (agents + tooling), so we use the standard Python counterparts with the same structure: suite classes, feature files, and CI gates.

> **Admin UI stack note:** Matrixly.world is a **static HTML + vanilla JS** site (not React/Next.js). The QA Admin Observability section is implemented as modular browser JS (`js/admin-observability.js`) with the same card/panel UX you would build in React. A future Next.js admin can re-use the endpoint contracts and JSDoc types in that module.

---

## Admin console (authorized access)

- **URL (local):** `http://127.0.0.1:8080/admin`
- Linked from site footer as **QA Admin** (home, agents, products)
- **Passphrase gate** before tools unlock (SHA-256 hashed in page JS)
- Session unlock stored in `sessionStorage` until Sign out

**Default authorization passphrase** (change hash in `admin/index.html` for production):

```text
matrixly-qa-dev
```

To rotate: compute SHA-256 hex of your new passphrase and replace `PASS_HASH` in `admin/index.html`.

```powershell
python -c "import hashlib; print(hashlib.sha256(b'YOUR_NEW_PASS').hexdigest())"
```

The Admin console provides:

1. Manual page open checklist  
2. UI regression checklist (persisted in `localStorage`)  
3. Copy-paste commands for Selenium / Playwright / BDD  
4. In-browser link probe (same-origin)  
5. **Observability Stack (Self-Hosted)** — Crawl4AI, Playwright pool, Prometheus, Grafana, Loki status, compose viewer, and dashboard deep-links  

Static sites cannot fully protect secrets in the browser. Treat this as **operator authorization**, not enterprise IAM—use a strong passphrase and rotate it for production.

---

## Observability Stack (Self-Hosted)

### Why “own it”

Matrixly agents crawl and enrich the web for SEO, content, and lead workflows. Shipping those jobs through a **self-hosted** Crawl4AI + metrics/logs plane gives you:

| Goal | How this stack helps |
|------|----------------------|
| **Cost control** | No per-request SaaS crawl/monitoring bill for internal volume |
| **Privacy** | Page content and agent logs stay on your host / VPC |
| **Reliability** | You control browser pool size, restarts, and retention |
| **Agent fit** | SEOForge, ContentForge, Lead Qualifier, etc. point at one Crawl4AI base URL |

Default local ports:

| Service | URL |
|---------|-----|
| Crawl4AI | http://127.0.0.1:11235 |
| Crawl4AI playground | http://127.0.0.1:11235/playground |
| Crawl4AI monitor | http://127.0.0.1:11235/monitor |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 |
| Loki | http://127.0.0.1:3100 |

Dashboard UID: **`matrixly-crawl4ai`** — title *Matrixly Crawl4AI Monitoring*.

---

### Step-by-step: implement & run the stack

#### 1. Prerequisites

- Docker Engine + Docker Compose v2  
- ~4 GB free RAM recommended for Crawl4AI browser pool  
- Ports `11235`, `9090`, `3000`, `3100` free (or change bindings in compose)  
- Git checkout of this repo  

```powershell
docker version
docker compose version
```

#### 2. Configure environment

```powershell
cd infra/observability
copy .env.example .env
# Edit .env — set GRAFANA_ADMIN_PASSWORD and optional CRAWL4AI_API_TOKEN
```

| Variable | Purpose |
|----------|---------|
| `CRAWL4AI_API_TOKEN` | Optional API token for production Crawl4AI |
| `MAX_CONCURRENT_BROWSERS` | Cap Playwright browsers (default `4`) |
| `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` | Grafana login (change from defaults) |
| `GRAFANA_ROOT_URL` | Public URL if behind reverse proxy |

#### 3. Start the stack

```powershell
cd infra/observability
docker compose pull
docker compose up -d
docker compose ps
```

Expected containers: `matrixly-crawl4ai`, `matrixly-prometheus`, `matrixly-grafana`, `matrixly-loki`, `matrixly-promtail`.

#### 4. Verify health endpoints

```powershell
curl http://127.0.0.1:11235/health
curl http://127.0.0.1:9090/-/healthy
curl http://127.0.0.1:3000/api/health
curl http://127.0.0.1:3100/ready
```

#### 5. Open Grafana and confirm datasources

1. Browse to http://127.0.0.1:3000  
2. Sign in with `.env` admin credentials  
3. **Connections → Data sources** — Prometheus (default) and Loki should be provisioned  
4. Open folder **Matrixly** → dashboard **Matrixly Crawl4AI Monitoring**  
5. If panels are empty, wait for scrapes or generate crawl traffic (step 7)

#### 6. Wire the QA Admin console

```powershell
# repo root
npm run build
npm start
# → http://127.0.0.1:8080
```

1. Open http://127.0.0.1:8080/admin  
2. Unlock with the QA passphrase  
3. Scroll to **Observability Stack (Self-Hosted)** or use the header **Observability** link  
4. Click **Refresh Status**  
5. Expand **Endpoint configuration** if services are not on localhost defaults  
6. Use **Open Grafana**, **Open Crawl4AI Monitor**, **View Recent Logs**  

Admin UI components:

| Card / panel | What it shows |
|--------------|----------------|
| **Docker Compose** | Derived stack health, path, restart / full compose viewer with copy |
| **Crawl4AI** | Connection, playground + `/monitor` links, browser/request/success metrics |
| **Playwright** | Pool health (via Crawl4AI), version hint, memory when exposed |
| **Prometheus** | Healthy probe, scrape targets table, UI link |
| **Grafana** | Admin health, dashboard deep-link |
| **Loki** | Ready probe, recent ERROR count (when LogQL is reachable) |
| **Grafana Dashboard** | Metrics / Logs / Combined toggle, key KPI strip, iframe + open button |

#### 7. Point Matrixly agents at Crawl4AI

In each agent `.env` (or orchestration config) that needs crawling:

```env
CRAWL4AI_BASE_URL=http://127.0.0.1:11235
# If token enabled:
# CRAWL4AI_API_TOKEN=your-token
```

Typical consumers: **SEOForge**, **ContentForge**, **Lead Qualifier**, **SEO-Bespoke**, **PipelineForge**. Prefer the private Docker network hostname `http://crawl4ai:11235` when the agent also runs in Compose on `matrixly-observability`.

#### 8. Optional same-origin control plane (production)

Browser probes to `127.0.0.1` only work when the operator’s browser can reach those ports. For hosted QA Admin on matrixly.world, add a **server-side** proxy (not committed yet) with:

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/obs/status` | Aggregate health JSON (`ObsSnapshot`) |
| `GET` | `/api/obs/crawl4ai` | Crawl4AI metrics |
| `GET` | `/api/obs/prometheus` | Scrape targets |
| `GET` | `/api/obs/loki/errors` | Recent error count |
| `POST` | `/api/obs/stack/restart` | Host-only restart (auth required) |

Then set in the Admin console (or before load):

```js
window.MATRIXLY_OBS_ENDPOINTS = { controlPlane: "/api/obs" };
```

Shapes match JSDoc types in `js/admin-observability.js` (`ServiceStatus`, `CrawlMetrics`, `ObsSnapshot`).

#### 9. Restart / update

```powershell
cd infra/observability
docker compose pull
docker compose up -d
# single service
docker compose restart crawl4ai
```

Or use **Restart Stack** in QA Admin to copy the same commands (the browser cannot restart Docker by itself).

#### 10. Tear down

```powershell
cd infra/observability
docker compose down
# wipe volumes (destructive):
# docker compose down -v
```

---

### Troubleshooting guide

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| QA Admin shows all services **Unreachable** / **Failed to fetch** | Stack not running, or browser cannot reach host ports | `docker compose ps` in `infra/observability`; start stack; check firewall |
| Crawl4AI badge red; port free | Image still starting, healthcheck lag | `docker compose logs -f crawl4ai`; wait for healthy; increase `start_period` |
| Prometheus targets empty in Admin | CORS blocks `/api/v1/targets` from the marketing origin | Open Prometheus UI → **Status → Targets**; or add control-plane proxy |
| Grafana iframe blank in Admin | `X-Frame-Options` / CSP deny embed | Use **Open Dashboard** button (expected for many Grafana installs) |
| Grafana login fails | Wrong password / fresh volume | Reset via `.env` + `docker compose up -d grafana` after volume wipe only if acceptable |
| Dashboard panels show **No data** | Crawl4AI has no `/metrics` or scrapes failing | Check Prometheus target `crawl4ai`; generate traffic; adjust metric names in dashboard JSON |
| Loki ERROR count always **—** | LogQL CORS or no matching labels | Use **Grafana Explore (Loki)** with `{container=~".*crawl4ai.*"} \|= "ERROR"`; verify Promtail `docker.sock` mount (Linux host) |
| Promtail no logs on Docker Desktop (Windows/macOS) | Socket / path differences | Prefer Linux VM/host for Promtail docker_sd; or run Promtail with file scrape of exported logs |
| High memory / OOM on Crawl4AI | Too many browsers | Lower `MAX_CONCURRENT_BROWSERS`; add memory limits in compose |
| Playwright “pool” bad while Crawl4AI was fine earlier | Browser process leak after failed crawls | `docker compose restart crawl4ai` |
| Agent crawl timeouts | Network from agent container to host | Use `host.docker.internal:11235` (Desktop) or shared Compose network |
| **Restart Stack** does nothing visible | By design — only shows host commands | Copy commands and run on the server SSH session |
| Passphrase won’t unlock Admin | Wrong phrase or rotated hash | See [Admin console](#admin-console-authorized-access); recompute `PASS_HASH` |
| `/admin` 404 on production | `admin/index.html` not in deploy artifact | Ensure `npm run build` includes `admin/`; Hostinger deploy uses `dist/` |

**Useful log commands**

```powershell
cd infra/observability
docker compose logs -f --tail=200 crawl4ai
docker compose logs -f --tail=100 promtail
docker compose logs -f --tail=100 prometheus
```

**Useful LogQL (Grafana Explore → Loki)**

```logql
{container=~".*crawl4ai.*"} |= "ERROR"
{container=~".*crawl4ai.*"} |~ "(?i)timeout|failed|exception"
```

**Useful PromQL**

```promql
up{job="crawl4ai"}
rate(crawl4ai_requests_total[5m])
```

(Exact metric names depend on the Crawl4AI image version; adjust dashboard JSON if needed.)

---

### Reference links

| Resource | URL |
|----------|-----|
| Crawl4AI documentation | https://docs.crawl4ai.com/ |
| Crawl4AI GitHub | https://github.com/unclecode/crawl4ai |
| Playwright docs | https://playwright.dev/docs/intro |
| Prometheus docs | https://prometheus.io/docs/introduction/overview/ |
| Prometheus HTTP API | https://prometheus.io/docs/prometheus/latest/querying/api/ |
| Grafana docs | https://grafana.com/docs/grafana/latest/ |
| Grafana provisioning | https://grafana.com/docs/grafana/latest/administration/provisioning/ |
| Loki docs | https://grafana.com/docs/loki/latest/ |
| LogQL | https://grafana.com/docs/loki/latest/query/ |
| Promtail | https://grafana.com/docs/loki/latest/send-data/promtail/ |
| Docker Compose | https://docs.docker.com/compose/ |
| Matrixly site | https://matrixly.world |
| This repo UI QA CI | `.github/workflows/ui-qa.yml` |
| Stack compose (source of truth) | `infra/observability/docker-compose.yml` |
| Admin observability module | `js/admin-observability.js` |
| Grafana dashboard JSON | `infra/observability/grafana/dashboards/matrixly-crawl4ai.json` |
| Broader troubleshooting | [`../docs/troubleshooting.md`](../docs/troubleshooting.md) |

---

### File map (observability)

```
infra/observability/
├── docker-compose.yml          # Crawl4AI + Prometheus + Grafana + Loki + Promtail
├── .env.example
├── prometheus.yml
├── loki-config.yml
├── promtail-config.yml
└── grafana/
    ├── dashboards/
    │   └── matrixly-crawl4ai.json
    └── provisioning/
        ├── datasources/datasources.yml
        └── dashboards/dashboards.yml

js/admin-observability.js       # QA Admin probes + UI mount API
admin/index.html                # Gate + UI QA + #observability mount point
```

**Browser API (for tests or a future React port):**

```js
// After /js/admin-observability.js loads
MatrixlyObs.mount(document.getElementById("obsRoot"));
await MatrixlyObs.fetchSnapshot();
MatrixlyObs.setEndpoints({ grafana: "https://grafana.internal" });
```

---

## Quick start (UI tests)

### 1. Serve the site

```powershell
# repo root
npm run build
npm start
# → http://127.0.0.1:8080  (dist/)
```

### 2. Install QA tools

```powershell
cd qa
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

### 3. Run tests

```powershell
# Selenium
pytest tests/selenium -v --site-url=http://127.0.0.1:8080

# Playwright
pytest tests/playwright -v --site-url=http://127.0.0.1:8080

# BDD (Cucumber-style)
pytest tests/bdd -v --site-url=http://127.0.0.1:8080

# All + HTML report
pytest -v --site-url=http://127.0.0.1:8080 --html=reports/report.html --self-contained-html
```

---

## Layout

```
qa/
├── config.py              # pages under test, BASE_URL
├── conftest.py            # Selenium driver + --site-url
├── pages/                 # Page Object Model
├── features/              # Gherkin (Cucumber-style)
├── tests/
│   ├── selenium/          # WebDriver suites
│   ├── playwright/        # Playwright suites
│   └── bdd/               # pytest-bdd step defs
├── reports/               # HTML / artifacts (gitignored)
└── requirements.txt
```

---

## CI/CD (Git)

Workflow **UI QA** (`.github/workflows/ui-qa.yml`):

1. Checkout  
2. `npm run build`  
3. Serve `dist/` in background  
4. Install Python deps + Chromium  
5. Run Playwright smoke (fast, reliable in GHA)  
6. Optionally Selenium + BDD  

On PRs to `main`, UI smoke must pass.

Main site deploy remains in `.github/workflows/ci-cd.yml`.

---

## Writing new tests

**Selenium (TestNG-like class):**

```python
@pytest.mark.selenium
class TestCheckout:
    def test_cta(self, open_page):
        driver = open_page("")  # home /
        assert "Matrixly" in driver.title
```

**BDD feature:**

```gherkin
Scenario: Home loads
  Given I open the "agents" page
  Then the page title should contain "Matrixly"
```

---

## Security notes

- Do not put production secrets in `admin/index.html`  
- Prefer running UI QA against local `dist/` or staging  
- Rotate the Admin passphrase for production  
- `/admin` is linked from the site footer; tools stay locked until authorized  
- Never commit real `GRAFANA_ADMIN_PASSWORD` or `CRAWL4AI_API_TOKEN`  
- Bind observability ports to `127.0.0.1` (or private VPC) and put SSO/VPN in front of Grafana in production  
- Browser-side restart is intentionally disabled — only host operators with Docker access restart the stack  

---

## License

Same as parent Matrixly repository (MIT).

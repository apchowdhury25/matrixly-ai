# Deployment — Matrixly.ai → Hostinger

This document explains how the production site reaches **https://matrixly.ai** (Hostinger).

## Stack (what we deploy)

| Item | Reality |
|------|---------|
| Site type | **Static HTML** (no SSR) |
| CSS | Tailwind via CDN (`cdn.tailwindcss.com`) |
| JS | Vanilla, inline / page-level |
| Build tool | **None** (no Vite / React / Next / Astro) |
| CI “build” | Copies public pages into `dist/` + writes `.htaccess` |
| Not deployed | `agents/` (Python pilots), `.env`, docs, CI tooling |

There is **no** `next build` / `vite build`. Local preview:

```bash
npm run build
npm start
# → http://localhost:8080
```

Or without Node: `python -m http.server 8080` from the repo root (dev only).

---

## Pipeline overview

Workflow: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)

```
PR to main          push main / workflow_dispatch
      │                        │
      ▼                        ▼
   Lint ──► Build          Lint ──► Build ──► Deploy
      │                        │                │
      │                        │                ├─► (a) branch `deploy`  [primary]
      │                        │                └─► (b) FTP to Hostinger [optional]
      └─ artifact only         └─ artifact
```

| Job | What it does |
|-----|----------------|
| **Lint** | Node 22 · `npm run lint` (required pages, HTML basics, secret patterns) · Python compile of pilot agents |
| **Build** | `npm run build` → clean `dist/` (HTML only + `.htaccess` + `deploy-meta.json`) · upload artifact |
| **Deploy** | **Only** on `main` pushes and **Run workflow** — never on PRs |

### Why a `deploy` branch?

Hostinger Git deploy clones a branch into the site root. Publishing **only** `dist/` to `deploy` means:

- No Python agents, no secrets, no `.github` on the web root
- Hostinger always gets a minimal, production-ready tree
- `main` stays the full product monorepo

This is the **preferred** method for this project.

---

## GitHub Secrets / variables

### Always needed for deploy branch?

| Secret | Required? | Notes |
|--------|-----------|--------|
| *(none)* | — | `deploy` branch uses the default `GITHUB_TOKEN` with `contents: write` on the deploy job |

If the repo is private and Hostinger needs access, use a Hostinger-side deploy key / GitHub App token as Hostinger documents — that is **outside** this workflow.

### Optional FTP (method b)

Add these under **GitHub → Settings → Secrets and variables → Actions → New repository secret** only if you want CI to upload via FTP/FTPS as well (or instead of Git deploy).

| Secret | Example | Description |
|--------|---------|-------------|
| `FTP_SERVER` | `ftp.matrixly.ai` or Hostinger IP / hostname | FTP host from hPanel |
| `FTP_USERNAME` | `u123456789` | FTP user |
| `FTP_PASSWORD` | `••••••••` | FTP password |
| `FTP_PORT` | `21` | Optional — leave unset to use action default (`21`) |
| `FTP_SERVER_DIR` | `./public_html/` | Remote path under the FTP home (often `./public_html/` or `./`) |

Protocol is fixed to **FTPS** in the workflow (Hostinger-friendly).

Optional **repository variable** (Settings → Variables):

| Variable | Value | Effect |
|----------|-------|--------|
| `ENABLE_FTP` | `false` | Force-skip FTP even if secrets exist |

FTP steps run only when `FTP_SERVER` is non-empty and `ENABLE_FTP` is not `false`.

### How to fill FTP secrets from Hostinger hPanel

1. Log in to [hPanel](https://hpanel.hostinger.com).
2. Open **Websites → matrixly.ai → Files → FTP Accounts** (or **Hosting → FTP**).
3. Create or view an FTP account limited to the site (prefer a dedicated deploy user).
4. Copy **hostname**, **username**, **password**, **port**.
5. Prefer **FTPS** (`FTP_PROTOCOL=ftps`) when Hostinger offers it.
6. Confirm the remote directory is the domain document root (often `public_html/` or `domains/matrixly.ai/public_html/`).
7. Paste values into GitHub Actions secrets (never commit them).

### SSH / SCP

Not configured. Shared Hostinger plans usually favor **Git** or **FTP**. If you later enable SSH, we can add `appleboy/scp-action` as a third path.

---

## Hostinger setup (after first successful CI run)

### Option A — Git deployment (recommended)

1. In hPanel: **Websites → matrixly.ai → Advanced → Git** (wording may vary: *Git*, *Git version control*).
2. Connect the GitHub repo `apchowdhury25/matrixly-ai`.
3. Set **branch** to **`deploy`** (not `main`).
4. Set **install / document root** so the branch root maps to the domain public root (the `deploy` branch root *is* the site — no `dist/` subfolder on that branch).
5. Enable **auto-deploy on push** if available.
6. Trigger a first deploy (push to `main` or **Actions → CI/CD → Run workflow**).
7. Confirm https://matrixly.ai loads `index.html` and https://matrixly.ai/agents.html works.

### Option B — FTP only

1. Add the FTP secrets above.
2. Leave Hostinger Git disconnected (or ignore the `deploy` branch).
3. Push to `main` (or run workflow). CI uploads `dist/` → `FTP_SERVER_DIR`.
4. Hard-refresh the live site.

### Avoid double deploys

If both Hostinger Git (watching `deploy`) **and** FTP are active, every main push updates the site twice. Prefer **one** method:

- Git only → omit FTP secrets (or set `ENABLE_FTP=false`)
- FTP only → you can still keep the `deploy` branch as a clean artifact mirror, or remove the Git connection in hPanel

---

## Manual deploy

GitHub UI:

1. **Actions** → **CI/CD**
2. **Run workflow**
3. Branch: `main`
4. Optionally set **skip_ftp** = `true`

CLI:

```bash
gh workflow run "CI/CD" --ref main
# watch:
gh run watch
```

---

## Local commands

```bash
npm run lint    # quality gates
npm run build   # write dist/
npm start       # preview dist/ on :8080
```

---

## What is intentionally not on the live site

- `agents/**` Python runtimes and data
- `.env` / credentials
- `docs/`, `.github/`, `scripts/`, `package.json`
- Virtualenvs, `__pycache__`, local agent outputs

Agents run on an operator machine or a secured VPS — **not** inside Hostinger static hosting.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| PR checks green but site old | Deploy only runs on `main` / manual dispatch |
| `deploy` branch empty / missing | Open latest **CI/CD** run → Deploy job logs |
| Hostinger still shows monorepo files | Branch is set to `main` — switch to `deploy` |
| FTP auth failed | Host, user, password, port, FTPS vs FTP, IP allowlist |
| 403 / directory listing | Ensure `index.html` is at the document root; `.htaccess` Options -Indexes |
| Tailwind missing styles | CDN blocked — confirm `cdn.tailwindcss.com` loads in browser Network tab |

---

## Related files

| Path | Role |
|------|------|
| `.github/workflows/ci-cd.yml` | Lint → build → deploy |
| `scripts/ci-lint.mjs` | Lint implementation |
| `scripts/ci-build.mjs` | `dist/` assembly + `.htaccess` |
| `package.json` | `npm run lint` / `build` / `start` |

# Matrixly UI QA Framework

Developer-only quality assurance for the **Matrixly static marketing UI**.

| Piece | Path |
|-------|------|
| Hidden QA console | [`../Admin.html`](../Admin.html) |
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

---

## Hidden Admin.html (developer only)

- **URL (local):** `http://127.0.0.1:8080/Admin.html`
- **Not linked** from public nav/footer
- `noindex` meta + `robots.txt` disallow
- Passphrase gate (SHA-256 hashed in page JS)

**Default developer passphrase** (change hash in `Admin.html` for production deploys):

```text
matrixly-qa-dev
```

To rotate: compute SHA-256 hex of your new passphrase and replace `PASS_HASH` in `Admin.html`.

```powershell
python -c "import hashlib; print(hashlib.sha256(b'YOUR_NEW_PASS').hexdigest())"
```

The Admin console provides:

1. Manual page open checklist  
2. UI regression checklist (persisted in `localStorage`)  
3. Copy-paste commands for Selenium / Playwright / BDD  
4. In-browser link probe (same-origin)

This is **obscurity + access control for honest developers**, not a substitute for server auth on sensitive systems.

---

## Quick start

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
        driver = open_page("index.html")
        assert "Matrixly" in driver.title
```

**BDD feature:**

```gherkin
Scenario: Home loads
  Given I open the "index.html" page
  Then the page title should contain "Matrixly"
```

---

## Security notes

- Do not put production secrets in `Admin.html`  
- Prefer running UI QA against local `dist/` or staging  
- Rotate the Admin passphrase if the URL is shared  
- `Admin.html` is published to the deploy branch (so you can QA production), but stays unlinked + noindex  

---

## License

Same as parent Matrixly repository (MIT).

#!/usr/bin/env node
/**
 * Matrixly.ai CI lint — static site quality gates (no heavy toolchain).
 * Validates required pages, HTML basics, clean URLs, and secret-leak patterns.
 */
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, extname, relative } from "node:path";

const ROOT = process.cwd();
const errors = [];
const warnings = [];

const REQUIRED_PAGES = [
  "index.html",
  "agents/index.html",
  "products/index.html",
  "integrations/index.html",
  "pricing/index.html",
  "email-assistant/index.html",
  "lead-qualifier/index.html",
  "crm-assistant/index.html",
  "shipping-assistant/index.html",
  "shipping-assistant-guide/index.html",
  "support-forge/index.html",
  "book-wise/index.html",
  "invoice-forge/index.html",
  "invoice-processor/index.html",
  "content-forge/index.html",
  "seo-forge/index.html",
  "seo-bespoke/index.html",
  "connect-forge/index.html",
  "meet-wise/index.html",
  "social-forge/index.html",
  "pipeline-forge/index.html",
  "doc-forge/index.html",
  "starter-pack/index.html",
  "etf-analyzer/index.html",
  "admin/index.html",
  "for/hvac/index.html",
  "for/shopify/index.html",
  "for/professional-services/index.html",
  "for/contractors/index.html",
  "for/local-retail/index.html",
  "resources/index.html",
  "resources/7-day-setup/index.html",
  "resources/email-voice/index.html",
  "resources/local-seo-playbook/index.html",
  "resources/shipping-exceptions/index.html",
  "resources/lead-follow-up/index.html",
  ".htaccess",
  "README.md",
  "LICENSE",
];

const SECRET_PATTERNS = [
  { name: "AWS key", re: /AKIA[0-9A-Z]{16}/ },
  { name: "Private key block", re: /-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----/ },
  { name: "GitHub PAT", re: /gh[pousr]_[A-Za-z0-9_]{20,}/ },
  { name: "Generic API key assignment", re: /(?:api[_-]?key|secret|password|token)\s*[:=]\s*['"][^'']{12,}['"]/i },
];

function fail(msg) {
  errors.push(msg);
}

function warn(msg) {
  warnings.push(msg);
}

/** Walk site HTML only (not agent package dashboards under agents static folders). */
function walkSiteHtml(dir, out = [], depth = 0) {
  for (const name of readdirSync(dir)) {
    if (
      name === "node_modules" ||
      name === ".git" ||
      name === "dist" ||
      name === ".venv" ||
      name === "docs" ||
      name === "qa" ||
      name === "scripts"
    ) {
      continue;
    }
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) {
      // Skip Python agent package trees except the marketplace agents/index.html parent
      if (name === "agents") {
        const market = join(full, "index.html");
        if (existsSync(market)) out.push(market);
        continue;
      }
      // Site page folders: top-level product pages + nested for/* and resources/*
      if (existsSync(join(full, "index.html")) && depth === 0) {
        out.push(join(full, "index.html"));
        if (name === "for" || name === "resources") {
          walkSiteHtml(full, out, depth + 1);
        }
        continue;
      }
      if (existsSync(join(full, "index.html")) && depth >= 1 && depth <= 2) {
        out.push(join(full, "index.html"));
        if (depth < 2) walkSiteHtml(full, out, depth + 1);
        continue;
      }
      walkSiteHtml(full, out, depth + 1);
    } else if (extname(name).toLowerCase() === ".html" && depth === 0) {
      out.push(full);
    }
  }
  return out;
}

console.log("▸ Lint: Matrixly.ai static site (clean URLs)\n");

// --- Required pages ---
for (const file of REQUIRED_PAGES) {
  const path = join(ROOT, file);
  if (!existsSync(path)) fail(`Missing required file: ${file}`);
  else console.log(`  ✓ ${file}`);
}

// --- No root HTML except index.html ---
for (const name of readdirSync(ROOT)) {
  if (name.endsWith(".html") && name !== "index.html") {
    fail(`Root must not contain ${name} — use folder/index.html`);
  }
}

// --- HTML sanity ---
const htmlFiles = walkSiteHtml(ROOT);
if (htmlFiles.length === 0) fail("No site HTML files found");

for (const file of htmlFiles) {
  const rel = relative(ROOT, file).replaceAll("\\", "/");
  const raw = readFileSync(file, "utf8");
  const lower = raw.slice(0, 500).toLowerCase();

  if (!lower.includes("<!doctype html") && !lower.includes("<html")) {
    fail(`${rel}: missing DOCTYPE/html root`);
  }
  if (!/<html[^>]*\slang\s*=/i.test(raw)) {
    warn(`${rel}: missing lang= on <html> (a11y/SEO)`);
  }
  if (!/<meta[^>]+charset=/i.test(raw)) {
    warn(`${rel}: missing charset meta`);
  }
  if (!/<title>[^<]+<\/title>/i.test(raw)) {
    fail(`${rel}: missing <title>`);
  }
  if (!/cdn\.tailwindcss\.com/i.test(raw) && rel.endsWith(".html") && !rel.startsWith("admin/")) {
    warn(`${rel}: Tailwind CDN not detected (expected for this stack)`);
  }

  // No internal .html hrefs
  const hits = raw.match(/href=["'][^"']*\.html[^"']*["']/gi) || [];
  const internal = hits.filter((h) => !/https?:/i.test(h));
  if (internal.length) {
    fail(`${rel}: internal .html href(s): ${internal.slice(0, 3).join(", ")}`);
  }

  // Assets should be root-absolute when page is nested
  if (rel.includes("/") && /(?:src|href)=["']assets\//i.test(raw)) {
    fail(`${rel}: relative assets/ path will break — use /assets/`);
  }

  for (const { name, re } of SECRET_PATTERNS) {
    if (re.test(raw)) fail(`${rel}: possible secret leak (${name})`);
  }
}

// --- Ensure agents are not mixed into a bogus package lock issue ---
if (existsSync(join(ROOT, ".env"))) {
  warn(".env exists locally — confirm it is gitignored (never commit secrets)");
}

// --- Report ---
console.log(`\n  Scanned ${htmlFiles.length} HTML file(s)`);

if (warnings.length) {
  console.log("\nWarnings:");
  for (const w of warnings) console.log(`  ⚠ ${w}`);
}

if (errors.length) {
  console.log("\nErrors:");
  for (const e of errors) console.log(`  ✗ ${e}`);
  console.log(`\n✖ Lint failed with ${errors.length} error(s)\n`);
  process.exit(1);
}

console.log("\n✔ Lint passed\n");

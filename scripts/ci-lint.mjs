#!/usr/bin/env node
/**
 * Matrixly.ai CI lint — static site quality gates (no heavy toolchain).
 * Validates required pages, HTML basics, and secret-leak patterns.
 */
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, extname } from "node:path";

const ROOT = process.cwd();
const errors = [];
const warnings = [];

const REQUIRED_PAGES = [
  "index.html",
  "agents.html",
  "products.html",
  "integrations.html",
  "email-assistant.html",
  "lead-qualifier.html",
  "crm-assistant.html",
  "shipping-assistant.html",
  "shipping-assistant-guide.html",
  "README.md",
  "LICENSE",
];

const SECRET_PATTERNS = [
  { name: "AWS key", re: /AKIA[0-9A-Z]{16}/ },
  { name: "Private key block", re: /-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----/ },
  { name: "GitHub PAT", re: /gh[pousr]_[A-Za-z0-9_]{20,}/ },
  { name: "Generic API key assignment", re: /(?:api[_-]?key|secret|password|token)\s*[:=]\s*['"][^'"]{12,}['"]/i },
];

function fail(msg) {
  errors.push(msg);
}

function warn(msg) {
  warnings.push(msg);
}

function walkHtmlFiles(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === ".git" || name === "dist" || name === ".venv") continue;
    if (name === "agents" || name === "docs") continue; // product code / internal notes
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) walkHtmlFiles(full, out);
    else if (extname(name).toLowerCase() === ".html") out.push(full);
  }
  return out;
}

console.log("▸ Lint: Matrixly.ai static site\n");

// --- Required pages ---
for (const file of REQUIRED_PAGES) {
  const path = join(ROOT, file);
  if (!existsSync(path)) fail(`Missing required file: ${file}`);
  else console.log(`  ✓ ${file}`);
}

// --- HTML sanity ---
const htmlFiles = walkHtmlFiles(ROOT);
if (htmlFiles.length === 0) fail("No HTML files found at site root");

for (const file of htmlFiles) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
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
  if (!/cdn\.tailwindcss\.com/i.test(raw) && rel.endsWith(".html")) {
    warn(`${rel}: Tailwind CDN not detected (expected for this stack)`);
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

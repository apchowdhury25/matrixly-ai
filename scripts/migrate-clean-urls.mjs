#!/usr/bin/env node
/**
 * One-shot (idempotent-safe) migration: root *.html → folder/index.html clean URLs.
 * Also rewrites internal links + asset paths to absolute clean paths.
 */
import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  existsSync,
  unlinkSync,
  readdirSync,
  statSync,
} from "node:fs";
import { join, dirname } from "node:path";

const ROOT = process.cwd();

/** basename (no .html) → clean path segment; empty string = site root */
const PAGE_MAP = {
  index: "",
  agents: "agents",
  products: "products",
  integrations: "integrations",
  pricing: "pricing",
  "lead-qualifier": "lead-qualifier",
  "email-assistant": "email-assistant",
  "crm-assistant": "crm-assistant",
  "shipping-assistant": "shipping-assistant",
  "shipping-assistant-guide": "shipping-assistant-guide",
  "support-forge": "support-forge",
  "book-wise": "book-wise",
  "invoice-forge": "invoice-forge",
  "content-forge": "content-forge",
  "seo-forge": "seo-forge",
  "meet-wise": "meet-wise",
  Admin: "admin",
  admin: "admin",
};

const ROOT_HTML = [
  "index.html",
  "agents.html",
  "products.html",
  "integrations.html",
  "lead-qualifier.html",
  "email-assistant.html",
  "crm-assistant.html",
  "shipping-assistant.html",
  "shipping-assistant-guide.html",
  "support-forge.html",
  "book-wise.html",
  "invoice-forge.html",
  "content-forge.html",
  "meet-wise.html",
  "Admin.html",
];

function cleanPathForBasename(base) {
  if (PAGE_MAP[base] === "") return "/";
  if (PAGE_MAP[base]) return `/${PAGE_MAP[base]}`;
  // fallback: strip .html style names
  return `/${base.replace(/\.html$/i, "")}`;
}

function rewriteContent(html) {
  let out = html;

  // Absolute asset paths (required once pages live in subfolders)
  out = out.replace(/(href|src)=(["'])assets\//gi, "$1=$2/assets/");
  out = out.replace(/(href|src)=(["'])\.\/assets\//gi, "$1=$2/assets/");

  // index.html with optional hash/query → / or /#...
  out = out.replace(
    /href=(["'])index\.html(#[^"']*|[^"']*)?\1/gi,
    (_, q, rest) => {
      const r = rest || "";
      if (r.startsWith("#")) return `href=${q}/${r}${q}`;
      if (!r || r === "") return `href=${q}/${q}`;
      return `href=${q}/${r}${q}`;
    }
  );

  // Named pages: Foo.html / foo.html → /foo
  // Sort longer names first to avoid partial replacements
  const bases = Object.keys(PAGE_MAP)
    .filter((b) => b !== "index")
    .sort((a, b) => b.length - a.length);

  for (const base of bases) {
    const dest = cleanPathForBasename(base);
    // href="base.html" or href="base.html#hash"
    const re = new RegExp(
      `href=(["'])${escapeReg(base)}\\.html(#[^"']*)?\\1`,
      "gi"
    );
    out = out.replace(re, (_, q, hash) => `href=${q}${dest}${hash || ""}${q}`);
  }

  // Catch any remaining *.html internal hrefs that map cleanly
  out = out.replace(
    /href=(["'])([a-zA-Z0-9._-]+)\.html(#[^"']*)?\1/g,
    (full, q, name, hash) => {
      if (name.toLowerCase() === "index") {
        return `href=${q}/${hash || ""}${q}`;
      }
      const dest = cleanPathForBasename(name);
      if (dest) return `href=${q}${dest}${hash || ""}${q}`;
      return full;
    }
  );

  // Pricing nav: prefer /pricing over /#pricing when link text context is pricing-only
  // Already handled if we map index.html#pricing → /#pricing; rewrite those to /pricing
  out = out.replace(/href=(["'])\/#pricing\1/g, `href=$1/pricing$1`);

  // Guide prose that still names old files as link text is fine; fix remaining bare paths in text links
  out = out.replace(
    />shipping-assistant\.html</g,
    ">/shipping-assistant<"
  );
  out = out.replace(/>agents\.html</g, ">/agents<");
  out = out.replace(/>integrations\.html</g, ">/integrations<");

  return out;
}

function escapeReg(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function destPathForSource(filename) {
  const base = filename.replace(/\.html$/i, "");
  const seg = PAGE_MAP[base];
  if (seg === "") return join(ROOT, "index.html");
  if (seg === undefined) {
    return join(ROOT, base.toLowerCase(), "index.html");
  }
  return join(ROOT, seg, "index.html");
}

function ensureDir(filePath) {
  mkdirSync(dirname(filePath), { recursive: true });
}

// --- Build pricing page from products shell + homepage pricing block ---
function buildPricingPage(indexHtml, productsHtml) {
  const pricingMatch = indexHtml.match(
    /<!-- ========== 7\. PRICING ========== -->[\s\S]*?<section id="pricing"[\s\S]*?<\/section>/
  );
  let pricingSection = pricingMatch
    ? pricingMatch[0]
        .replace(/<!-- ========== 7\. PRICING ========== -->\s*/, "")
        .replace(/id="pricing"/, 'id="pricing"')
        .replace(/href="#final-cta"/g, 'href="/#final-cta"')
    : null;

  if (!pricingSection) {
    // Fallback: grab section#pricing only
    const m = indexHtml.match(/<section id="pricing"[\s\S]*?<\/section>/);
    pricingSection = m
      ? m[0].replace(/href="#final-cta"/g, 'href="/#final-cta"')
      : '<section id="pricing" class="relative py-20"><div class="max-w-7xl mx-auto px-4"><h1 class="text-matrix-cream">Pricing</h1></div></section>';
  }

  // Use products.html as chrome (nav/footer) and swap main content
  let page = productsHtml;
  page = page.replace(
    /<title>[^<]*<\/title>/,
    "<title>Pricing — Matrixly</title>"
  );
  page = page.replace(
    /content="[^"]*Products[^"]*"/i,
    'content="Matrixly pricing for SMBs, small teams, and contractors — Explore free, Starter $49, Pro $149."'
  );

  // Replace main content between header and footer if possible
  const mainRe =
    /(<main[\s\S]*?>)[\s\S]*?(<\/main>)/i;
  if (mainRe.test(page)) {
    page = page.replace(
      mainRe,
      `$1\n    <section class="pt-28 pb-8">\n      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">\n        <p class="font-mono text-sm text-matrix-green mb-3 tracking-wide">// PRICING</p>\n        <h1 class="text-3xl sm:text-4xl font-extrabold text-matrix-cream tracking-tight">Plans built for agentic scale</h1>\n      </div>\n    </section>\n    ${pricingSection}\n    <section class="pb-20">\n      <div class="max-w-3xl mx-auto px-4 text-center">\n        <a href="/#final-cta" class="btn-primary px-8 py-3.5 rounded-xl text-sm">Get started free</a>\n      </div>\n    </section>\n  $2`
    );
  } else {
    // Inject before footer
    page = page.replace(
      /<footer/i,
      `${pricingSection}\n  <footer`
    );
  }

  // Mark pricing nav current
  page = page.replace(
    /href="\/pricing" class="nav-link"/g,
    'href="/pricing" class="nav-link" aria-current="page"'
  );
  page = page.replace(
    /aria-current="page">Products/g,
    ">Products"
  );

  return rewriteContent(page);
}

console.log("▸ Migrate Matrixly site → clean folder URLs\n");

const sources = {};
for (const name of ROOT_HTML) {
  const p = join(ROOT, name);
  if (!existsSync(p)) {
    console.warn(`  ! missing source ${name}`);
    continue;
  }
  sources[name] = readFileSync(p, "utf8");
}

if (!sources["index.html"]) {
  console.error("index.html required");
  process.exit(1);
}

// First pass: write rewritten pages
const written = [];
for (const [name, raw] of Object.entries(sources)) {
  const dest = destPathForSource(name);
  const content = rewriteContent(raw);
  ensureDir(dest);
  // Avoid clobbering if we're reading and writing index in place carefully
  writeFileSync(dest, content, "utf8");
  written.push(dest.slice(ROOT.length + 1).replaceAll("\\", "/"));
  console.log(`  + ${dest.slice(ROOT.length + 1).replaceAll("\\", "/")}`);
}

// Pricing page (new)
const productsSrc =
  sources["products.html"] ||
  (existsSync(join(ROOT, "products", "index.html"))
    ? readFileSync(join(ROOT, "products", "index.html"), "utf8")
    : sources["agents.html"]);
const pricingDest = join(ROOT, "pricing", "index.html");
ensureDir(pricingDest);
const pricingHtml = buildPricingPage(
  sources["index.html"],
  rewriteContent(productsSrc)
);
writeFileSync(pricingDest, pricingHtml, "utf8");
written.push("pricing/index.html");
console.log("  + pricing/index.html");

// Delete old root HTML (except index.html which was rewritten in place)
for (const name of ROOT_HTML) {
  if (name === "index.html") continue;
  const p = join(ROOT, name);
  if (existsSync(p)) {
    // Only delete if destination is a different path
    const dest = destPathForSource(name);
    if (p !== dest && existsSync(dest)) {
      unlinkSync(p);
      console.log(`  − ${name}`);
    }
  }
}

// Verify no root html except index
const leftover = readdirSync(ROOT).filter(
  (n) => n.endsWith(".html") && n !== "index.html" && statSync(join(ROOT, n)).isFile()
);
if (leftover.length) {
  console.warn("  ! leftover root HTML:", leftover.join(", "));
}

// Spot-check for remaining .html hrefs in site pages
const siteFiles = [
  "index.html",
  ...written.filter((w) => w.endsWith("index.html")),
];
let bad = 0;
for (const rel of new Set(siteFiles)) {
  const p = join(ROOT, rel);
  if (!existsSync(p)) continue;
  const t = readFileSync(p, "utf8");
  const matches = t.match(/href=["'][^"']*\.html[^"']*["']/gi) || [];
  // allow external only — filter internal
  const internal = matches.filter(
    (m) => !/href=["']https?:/i.test(m) && !/href=["']\/\//.test(m)
  );
  if (internal.length) {
    bad += internal.length;
    console.warn(`  ! ${rel} still has .html hrefs:`, internal.slice(0, 5));
  }
}

console.log(`\n✔ Wrote ${written.length} pages. Remaining internal .html hrefs: ${bad}\n`);
if (bad > 0) process.exitCode = 1;

#!/usr/bin/env node
/**
 * Matrixly.ai CI build — assemble a clean static publish directory.
 *
 * Clean URL architecture: folder + index.html only (no .html in the bar).
 * Copies public site assets into dist/ so Hostinger never receives agents/
 * Python packages, .env, or tooling.
 */
import {
  cpSync,
  mkdirSync,
  rmSync,
  writeFileSync,
  readdirSync,
  existsSync,
  statSync,
  readFileSync,
} from "node:fs";
import { join, extname, dirname } from "node:path";

const ROOT = process.cwd();
const DIST = join(ROOT, "dist");

/** Site pages as clean folder paths (relative to repo root). index = root. */
const SITE_PAGES = [
  "index.html",
  "agents/index.html",
  "products/index.html",
  "integrations/index.html",
  "pricing/index.html",
  "lead-qualifier/index.html",
  "email-assistant/index.html",
  "crm-assistant/index.html",
  "shipping-assistant/index.html",
  "shipping-assistant-guide/index.html",
  "support-forge/index.html",
  "book-wise/index.html",
  "invoice-forge/index.html",
  "content-forge/index.html",
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
];

const ASSET_EXTS = new Set([
  ".css",
  ".js",
  ".mjs",
  ".map",
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".webp",
  ".svg",
  ".ico",
  ".woff",
  ".woff2",
  ".ttf",
  ".eot",
  ".txt",
  ".xml",
  ".json",
  ".webmanifest",
]);

const ASSET_DIRS = ["assets", "css", "js", "images", "img", "fonts", "static", "public"];

console.log("▸ Build: Matrixly.ai → dist/ (clean URLs)\n");

rmSync(DIST, { recursive: true, force: true });
mkdirSync(DIST, { recursive: true });

let copied = 0;

function copyFile(src, dest) {
  mkdirSync(dirname(dest), { recursive: true });
  cpSync(src, dest);
  copied += 1;
  console.log(`  + ${dest.slice(ROOT.length + 1).replaceAll("\\", "/")}`);
}

// Core site pages (folder/index.html)
for (const rel of SITE_PAGES) {
  const src = join(ROOT, rel);
  if (!existsSync(src)) {
    console.error(`  ✗ Missing page: ${rel}`);
    process.exit(1);
  }
  copyFile(src, join(DIST, rel));
}

// Root static assets (robots, favicon, sitemap, etc.)
const ROOT_SKIP = new Set([
  "package.json",
  "package-lock.json",
  "yarn.lock",
  "pnpm-lock.yaml",
  "deploy-meta.json",
  "index.html",
]);
for (const name of readdirSync(ROOT)) {
  if (ROOT_SKIP.has(name)) continue;
  if (name.startsWith(".")) continue;
  const src = join(ROOT, name);
  if (!statSync(src).isFile()) continue;
  const ext = extname(name).toLowerCase();
  if (
    ASSET_EXTS.has(ext) ||
    name === "robots.txt" ||
    name === "favicon.ico" ||
    name === "sitemap.xml"
  ) {
    copyFile(src, join(DIST, name));
  }
}

// Asset directories
for (const dir of ASSET_DIRS) {
  const src = join(ROOT, dir);
  if (existsSync(src) && statSync(src).isDirectory()) {
    const dest = join(DIST, dir);
    cpSync(src, dest, { recursive: true });
    console.log(`  + ${dir}/ (recursive)`);
    copied += 1;
  }
}

// Production .htaccess — prefer root file (source of truth)
const rootHt = join(ROOT, ".htaccess");
const htaccessBody = existsSync(rootHt)
  ? readFileSync(rootHt, "utf8")
  : `RewriteEngine On

# Force HTTPS
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# Redirect any old .html URL to the clean version (301)
RewriteCond %{THE_REQUEST} \\s/+(.+?)\\.html[\\s?] [NC]
RewriteRule ^ /%1 [R=301,L,NE]

# Serve clean folder URLs
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_FILENAME}.html -f
RewriteRule ^(.*)$ $1.html [L]
`;
writeFileSync(join(DIST, ".htaccess"), htaccessBody, "utf8");
console.log("  + dist/.htaccess");
copied += 1;

// Lightweight deploy stamp
const stamp = {
  site: "matrixly.world",
  builtAt: new Date().toISOString(),
  urlStyle: "clean-folder-index",
  pages: SITE_PAGES,
  node: process.version,
};
writeFileSync(join(DIST, "deploy-meta.json"), JSON.stringify(stamp, null, 2) + "\n", "utf8");
console.log("  + dist/deploy-meta.json");
copied += 1;

// Safety: never ship env files
for (const bad of [".env", ".env.local", ".env.production"]) {
  if (existsSync(join(DIST, bad))) {
    console.error(`  ✗ Refusing to publish ${bad}`);
    process.exit(1);
  }
}

// Verify index + no root .html except index
const index = readFileSync(join(DIST, "index.html"), "utf8");
if (!index.includes("Matrixly")) {
  console.error("  ✗ dist/index.html does not look like Matrixly site");
  process.exit(1);
}

const distRootHtml = readdirSync(DIST).filter(
  (n) => n.endsWith(".html") && n !== "index.html"
);
if (distRootHtml.length) {
  console.error("  ✗ Unexpected root HTML in dist:", distRootHtml.join(", "));
  process.exit(1);
}

// Fail if any published page still links to *.html (internal)
let badLinks = 0;
function walkHtml(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walkHtml(p);
    else if (name.endsWith(".html")) {
      const t = readFileSync(p, "utf8");
      const hits = t.match(/href=["'][^"']*\.html[^"']*["']/gi) || [];
      const internal = hits.filter((h) => !/https?:/i.test(h));
      if (internal.length) {
        badLinks += internal.length;
        console.error(
          `  ✗ ${p.slice(ROOT.length + 1)} has .html hrefs:`,
          internal.slice(0, 3)
        );
      }
    }
  }
}
walkHtml(DIST);

if (badLinks) {
  console.error(`  ✗ ${badLinks} internal .html link(s) in dist`);
  process.exit(1);
}

console.log(`\n✔ Build complete — ${copied} item(s) in dist/ (clean URLs)\n`);

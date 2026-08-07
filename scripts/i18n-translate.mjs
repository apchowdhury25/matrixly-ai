#!/usr/bin/env node
/**
 * Matrixly i18n translate / sync script
 *
 * Reads i18n/en.json as source of truth.
 * For each target language (es, fr, ar, bn, de, ms):
 *   - Fills missing keys
 *   - Optionally rewrites empty locale files
 *
 * Providers (optional env):
 *   DEEPL_API_KEY  — DeepL Free/Pro for es, fr, de
 *   OPENAI_API_KEY — GPT for ar, bn (owner tone)
 *   ANTHROPIC_API_KEY — Claude for ar, bn (preferred if set)
 *
 * Without keys: uses built-in high-quality seed catalogs if present,
 * or copies English with a console warning (never writes empty files).
 *
 * Usage:
 *   node scripts/i18n-translate.mjs
 *   node scripts/i18n-translate.mjs --dry-run
 *   node scripts/i18n-translate.mjs --force es,fr
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const I18N = path.join(ROOT, "i18n");

const TARGETS = {
  es: { provider: "deepl", deepl: "ES", name: "Spanish" },
  fr: { provider: "deepl", deepl: "FR", name: "French" },
  de: { provider: "deepl", deepl: "DE", name: "German" },
  ms: { provider: "llm", name: "Malay" },
  ar: { provider: "llm", name: "Arabic", dir: "rtl" },
  bn: { provider: "llm", name: "Bengali" },
};

const GLOSSARY = `
GLOSSARY / STYLE (Matrixly owner tone):
- Keep "Matrixly" untranslated.
- Product/agent brand names stay English: SocialForge, BookWise, SupportForge, Lead Qualifier, Email Assistant, CRM Assistant, Shipping Assistant, InvoiceForge, ContentForge, SEO Forge, MeetWise, PipelineForge, Starter Pack, DocForge, ConnectForge.
- "AI agents" → natural local equivalent that still feels modern and trustworthy (not corporate jargon).
- Emotional arc: overloaded owner → reclaim 20+ hours → no tech team needed.
- Practical, empathetic, time/revenue focused. Never overly formal or enterprise-salesy.
- Preserve placeholders, punctuation, and meaning of split keys (headline1/headline2, title/titleHighlight).
`.trim();

const dryRun = process.argv.includes("--dry-run");
const forceArg = process.argv.find((a) => a.startsWith("--force"));
const forceList = forceArg
  ? forceArg.replace("--force=", "").replace("--force", "").split(",").filter(Boolean)
  : process.argv.includes("--force")
    ? Object.keys(TARGETS)
    : [];

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function writeJson(file, data) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function isEmptyFile(file) {
  if (!fs.existsSync(file)) return true;
  const st = fs.statSync(file);
  if (st.size === 0) return true;
  try {
    const j = readJson(file);
    return !j || !j.meta || !j.nav;
  } catch {
    return true;
  }
}

function flatten(obj, prefix = "", out = {}) {
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    for (const [k, v] of Object.entries(obj)) {
      flatten(v, prefix ? `${prefix}.${k}` : k, out);
    }
  } else {
    out[prefix] = obj;
  }
  return out;
}

function unflatten(flat) {
  const root = {};
  for (const [pathKey, value] of Object.entries(flat)) {
    const parts = pathKey.split(".");
    let cur = root;
    for (let i = 0; i < parts.length - 1; i++) {
      cur[parts[i]] = cur[parts[i]] || {};
      cur = cur[parts[i]];
    }
    cur[parts[parts.length - 1]] = value;
  }
  return root;
}

function missingKeys(enFlat, targetFlat) {
  return Object.keys(enFlat).filter((k) => targetFlat[k] == null || targetFlat[k] === "");
}

async function deeplTranslate(texts, targetLang) {
  const key = process.env.DEEPL_API_KEY;
  if (!key) return null;
  const endpoint = key.endsWith(":fx")
    ? "https://api-free.deepl.com/v2/translate"
    : "https://api.deepl.com/v2/translate";
  const body = new URLSearchParams();
  body.set("auth_key", key);
  body.set("target_lang", targetLang);
  body.set("source_lang", "EN");
  body.set("preserve_formatting", "1");
  for (const t of texts) body.append("text", t);
  const res = await fetch(endpoint, { method: "POST", body });
  if (!res.ok) throw new Error(`DeepL ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return data.translations.map((t) => t.text);
}

async function llmTranslateBatch(pairs, langName, dir) {
  const system = `You are a professional translator for Matrixly (AI agents for small businesses).
Translate UI strings to ${langName}. Return ONLY a JSON object mapping path → translated string.
${GLOSSARY}
${dir === "rtl" ? 'Set natural Modern Standard Arabic; meta.dir will be "rtl".' : ""}
Do not translate brand names listed in the glossary.`;

  const user = JSON.stringify(Object.fromEntries(pairs), null, 2);

  if (process.env.ANTHROPIC_API_KEY) {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 8192,
        system,
        messages: [{ role: "user", content: `Translate these UI strings. Return JSON only:\n${user}` }],
      }),
    });
    if (!res.ok) throw new Error(`Anthropic ${res.status}: ${await res.text()}`);
    const data = await res.json();
    const text = data.content?.map((c) => c.text).join("") || "";
    const match = text.match(/\{[\s\S]*\}/);
    if (!match) throw new Error("No JSON in Anthropic response");
    return JSON.parse(match[0]);
  }

  if (process.env.OPENAI_API_KEY) {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        temperature: 0.2,
        messages: [
          { role: "system", content: system },
          { role: "user", content: `Translate these UI strings. Return JSON only:\n${user}` },
        ],
        response_format: { type: "json_object" },
      }),
    });
    if (!res.ok) throw new Error(`OpenAI ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return JSON.parse(data.choices[0].message.content);
  }

  return null;
}

async function fillLocale(code, en, enFlat) {
  const file = path.join(I18N, `${code}.json`);
  const metaCfg = TARGETS[code];
  let target = {};
  if (!isEmptyFile(file) && !forceList.includes(code)) {
    target = readJson(file);
  }

  const targetFlat = flatten(target);
  const missing = missingKeys(enFlat, targetFlat);

  if (missing.length === 0 && !forceList.includes(code) && !isEmptyFile(file)) {
    console.log(`[ok] ${code}: complete (${Object.keys(enFlat).length} keys)`);
    return { code, wrote: false, missing: 0 };
  }

  console.log(`[work] ${code}: ${missing.length} missing keys (provider=${metaCfg.provider})`);

  const toFill = forceList.includes(code) ? Object.keys(enFlat) : missing;
  const updates = { ...targetFlat };

  // Always set meta
  updates["meta.lang"] = code;
  updates["meta.dir"] = metaCfg.dir || "ltr";
  updates["meta.name"] = metaCfg.name;
  if (!updates["meta.nativeName"]) {
    // keep existing native if present
  }

  const stringKeys = toFill.filter((k) => typeof enFlat[k] === "string" && !k.startsWith("meta."));

  if (metaCfg.provider === "deepl" && process.env.DEEPL_API_KEY) {
    const batchSize = 40;
    for (let i = 0; i < stringKeys.length; i += batchSize) {
      const slice = stringKeys.slice(i, i + batchSize);
      const texts = slice.map((k) => enFlat[k]);
      try {
        const translated = await deeplTranslate(texts, metaCfg.deepl);
        if (translated) {
          slice.forEach((k, idx) => {
            updates[k] = translated[idx];
          });
          continue;
        }
      } catch (e) {
        console.warn(`[warn] DeepL batch failed for ${code}:`, e.message);
      }
      // fallback: leave English for this batch if no existing
      slice.forEach((k) => {
        if (updates[k] == null) updates[k] = enFlat[k];
      });
    }
  } else if (metaCfg.provider === "llm" && (process.env.ANTHROPIC_API_KEY || process.env.OPENAI_API_KEY)) {
    const batchSize = 50;
    for (let i = 0; i < stringKeys.length; i += batchSize) {
      const slice = stringKeys.slice(i, i + batchSize);
      const pairs = slice.map((k) => [k, enFlat[k]]);
      try {
        const map = await llmTranslateBatch(pairs, metaCfg.name, metaCfg.dir);
        if (map) {
          slice.forEach((k) => {
            if (map[k]) updates[k] = map[k];
            else if (updates[k] == null) updates[k] = enFlat[k];
          });
          continue;
        }
      } catch (e) {
        console.warn(`[warn] LLM batch failed for ${code}:`, e.message);
      }
      slice.forEach((k) => {
        if (updates[k] == null) updates[k] = enFlat[k];
      });
    }
  } else {
    // No API key: preserve existing translations; fill holes from English only for brand-new empties
    if (isEmptyFile(file) || forceList.includes(code)) {
      console.warn(
        `[warn] ${code}: no API key and locale incomplete — keeping existing seed if any, else English fallback for missing keys.`
      );
    }
    stringKeys.forEach((k) => {
      if (updates[k] == null || updates[k] === "") updates[k] = enFlat[k];
    });
  }

  // Ensure every en key exists
  for (const k of Object.keys(enFlat)) {
    if (updates[k] == null) updates[k] = enFlat[k];
  }

  const out = unflatten(updates);
  out.meta = out.meta || {};
  out.meta.lang = code;
  out.meta.dir = metaCfg.dir || "ltr";
  out.meta.name = metaCfg.name;
  if (!out.meta.nativeName) {
    out.meta.nativeName =
      { es: "Español", fr: "Français", ar: "العربية", bn: "বাংলা", de: "Deutsch", ms: "Bahasa Melayu" }[code] ||
      metaCfg.name;
  }

  if (dryRun) {
    console.log(`[dry-run] would write ${file}`);
    return { code, wrote: false, missing: missing.length, dryRun: true };
  }

  writeJson(file, out);
  console.log(`[wrote] ${file}`);
  return { code, wrote: true, missing: missing.length };
}

async function main() {
  const enPath = path.join(I18N, "en.json");
  if (!fs.existsSync(enPath) || isEmptyFile(enPath)) {
    console.error("i18n/en.json missing or empty — aborting");
    process.exit(1);
  }
  const en = readJson(enPath);
  // US English meta
  en.meta = en.meta || {};
  en.meta.lang = "en";
  en.meta.dir = "ltr";
  en.meta.name = "English (US)";
  en.meta.nativeName = "English";
  if (!dryRun) writeJson(enPath, en);

  const enFlat = flatten(en);
  console.log(`Source en.json: ${Object.keys(enFlat).length} keys`);
  console.log(GLOSSARY.split("\n")[0]);

  const results = [];
  for (const code of Object.keys(TARGETS)) {
    results.push(await fillLocale(code, en, enFlat));
  }

  // Key parity report
  console.log("\n--- parity ---");
  for (const code of ["en", ...Object.keys(TARGETS)]) {
    const f = path.join(I18N, `${code}.json`);
    if (isEmptyFile(f)) {
      console.log(`${code}: EMPTY`);
      continue;
    }
    const flat = flatten(readJson(f));
    const miss = missingKeys(enFlat, flat);
    console.log(`${code}: ${Object.keys(flat).length} keys, missing ${miss.length}`);
    if (miss.length) console.log("  ", miss.slice(0, 15).join(", "), miss.length > 15 ? "…" : "");
  }

  if (results.some((r) => r.missing > 0 && !r.wrote && !dryRun)) {
    // still ok if seeds filled holes with English
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

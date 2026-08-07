/**
 * Matrixly client-side i18n
 * Supports: en (default), es, fr, ar (RTL), bn
 * Persists language in localStorage under "matrixly-lang"
 * Expects elements with data-i18n="key.path" or data-i18n-html="key.path"
 * Also supports data-i18n-attr="attr:key.path" for attributes (e.g. placeholder, aria-label, title)
 */
(function () {
  const SUPPORTED = ["en", "es", "fr", "ar", "bn"];
  const DEFAULT_LANG = "en";
  const STORAGE_KEY = "matrixly-lang";
  const BASE = "/i18n/";

  let currentLang = DEFAULT_LANG;
  let catalog = {};

  function getNested(obj, path) {
    return path.split(".").reduce((o, k) => (o && o[k] != null ? o[k] : null), obj);
  }

  async function loadCatalog(lang) {
    if (!SUPPORTED.includes(lang)) lang = DEFAULT_LANG;
    try {
      const res = await fetch(`${BASE}${lang}.json`, { cache: "no-cache" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      catalog = await res.json();
      currentLang = lang;
      return catalog;
    } catch (err) {
      console.warn(`[i18n] Failed to load ${lang}.json, falling back to en`, err);
      if (lang !== DEFAULT_LANG) return loadCatalog(DEFAULT_LANG);
      catalog = {};
      return catalog;
    }
  }

  function applyDirection(lang) {
    const dir = (catalog.meta && catalog.meta.dir) || (lang === "ar" ? "rtl" : "ltr");
    document.documentElement.setAttribute("lang", lang);
    document.documentElement.setAttribute("dir", dir);
    document.documentElement.classList.toggle("rtl", dir === "rtl");
  }

  function translateElement(el) {
    const key = el.getAttribute("data-i18n");
    if (key) {
      const val = getNested(catalog, key);
      if (val != null) el.textContent = val;
    }
    const htmlKey = el.getAttribute("data-i18n-html");
    if (htmlKey) {
      const val = getNested(catalog, htmlKey);
      if (val != null) el.innerHTML = val;
    }
    const attrSpec = el.getAttribute("data-i18n-attr");
    if (attrSpec) {
      attrSpec.split(",").forEach((pair) => {
        const [attr, k] = pair.trim().split(":");
        if (attr && k) {
          const val = getNested(catalog, k);
          if (val != null) el.setAttribute(attr, val);
        }
      });
    }
  }

  function applyTranslations() {
    document.querySelectorAll("[data-i18n], [data-i18n-html], [data-i18n-attr]").forEach(translateElement);
  }

  async function setLanguage(lang) {
    if (!SUPPORTED.includes(lang)) lang = DEFAULT_LANG;
    await loadCatalog(lang);
    applyDirection(lang);
    applyTranslations();
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (_) {}
    window.dispatchEvent(new CustomEvent("matrixly:langchange", { detail: { lang, catalog } }));
  }

  function getSavedLang() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && SUPPORTED.includes(saved)) return saved;
    } catch (_) {}
    const nav = (navigator.language || "").slice(0, 2).toLowerCase();
    if (SUPPORTED.includes(nav)) return nav;
    return DEFAULT_LANG;
  }

  window.MatrixlyI18n = {
    setLanguage,
    getLanguage: () => currentLang,
    getCatalog: () => catalog,
    t: (key) => getNested(catalog, key) || key,
    supported: SUPPORTED,
  };

  function init() {
    const startLang = getSavedLang();
    setLanguage(startLang);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

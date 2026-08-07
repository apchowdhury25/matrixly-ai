/**
 * Matrixly client-side i18n
 * Supports: en (default, US), es, fr, ar (RTL), bn, de, ms
 * Persists language in localStorage under "matrixly-lang"
 * Catalogs cached in memory + sessionStorage for fast language switches
 * Expects elements with data-i18n="key.path" or data-i18n-html="key.path"
 * Also supports data-i18n-attr="attr:key.path" for attributes
 */
(function () {
  const SUPPORTED = ["en", "es", "fr", "ar", "bn", "de", "ms"];
  const DEFAULT_LANG = "en";
  const STORAGE_KEY = "matrixly-lang";
  const CACHE_PREFIX = "matrixly-i18n-catalog:";
  const CACHE_VERSION = "v2";
  const BASE = "/i18n/";

  let currentLang = DEFAULT_LANG;
  let catalog = {};
  /** @type {Record<string, object>} */
  const memoryCache = {};

  function getNested(obj, path) {
    return path.split(".").reduce(function (o, k) {
      return o && o[k] != null ? o[k] : null;
    }, obj);
  }

  function cacheKey(lang) {
    return CACHE_PREFIX + CACHE_VERSION + ":" + lang;
  }

  function readSessionCache(lang) {
    try {
      var raw = sessionStorage.getItem(cacheKey(lang));
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (_) {
      return null;
    }
  }

  function writeSessionCache(lang, data) {
    try {
      sessionStorage.setItem(cacheKey(lang), JSON.stringify(data));
    } catch (_) {
      /* quota / private mode — memory cache still works */
    }
  }

  async function fetchCatalog(lang) {
    if (memoryCache[lang]) return memoryCache[lang];
    var cached = readSessionCache(lang);
    if (cached && typeof cached === "object") {
      memoryCache[lang] = cached;
      return cached;
    }
    var res = await fetch(BASE + lang + ".json", { cache: "force-cache" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    var data = await res.json();
    memoryCache[lang] = data;
    writeSessionCache(lang, data);
    return data;
  }

  async function loadCatalog(lang) {
    if (!SUPPORTED.includes(lang)) lang = DEFAULT_LANG;
    try {
      catalog = await fetchCatalog(lang);
      currentLang = lang;
      return catalog;
    } catch (err) {
      console.warn("[i18n] Failed to load " + lang + ".json, falling back to en", err);
      if (lang !== DEFAULT_LANG) return loadCatalog(DEFAULT_LANG);
      catalog = {};
      return catalog;
    }
  }

  function applyDirection(lang) {
    var dir = (catalog.meta && catalog.meta.dir) || (lang === "ar" ? "rtl" : "ltr");
    document.documentElement.setAttribute("lang", lang === "en" ? "en-US" : lang);
    document.documentElement.setAttribute("dir", dir);
    document.documentElement.classList.toggle("rtl", dir === "rtl");
  }

  function translateElement(el) {
    var key = el.getAttribute("data-i18n");
    if (key) {
      var val = getNested(catalog, key);
      if (val != null) el.textContent = val;
    }
    var htmlKey = el.getAttribute("data-i18n-html");
    if (htmlKey) {
      var htmlVal = getNested(catalog, htmlKey);
      if (htmlVal != null) el.innerHTML = htmlVal;
    }
    var attrSpec = el.getAttribute("data-i18n-attr");
    if (attrSpec) {
      attrSpec.split(",").forEach(function (pair) {
        var parts = pair.trim().split(":");
        var attr = parts[0];
        var k = parts[1];
        if (attr && k) {
          var aVal = getNested(catalog, k);
          if (aVal != null) el.setAttribute(attr, aVal);
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
    window.dispatchEvent(new CustomEvent("matrixly:langchange", { detail: { lang: lang, catalog: catalog } }));
  }

  function getSavedLang() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && SUPPORTED.includes(saved)) return saved;
    } catch (_) {}
    var nav = (navigator.language || "").toLowerCase();
    if (nav.indexOf("en") === 0) return "en";
    var short = nav.slice(0, 2);
    if (SUPPORTED.includes(short)) return short;
    return DEFAULT_LANG;
  }

  /** Prefetch other locales into cache after first paint */
  function prefetchOthers(active) {
    SUPPORTED.forEach(function (lang) {
      if (lang === active) return;
      fetchCatalog(lang).catch(function () {});
    });
  }

  window.MatrixlyI18n = {
    setLanguage: setLanguage,
    getLanguage: function () {
      return currentLang;
    },
    getCatalog: function () {
      return catalog;
    },
    t: function (key) {
      return getNested(catalog, key) || key;
    },
    applyTranslations: applyTranslations,
    supported: SUPPORTED,
    clearCache: function () {
      Object.keys(memoryCache).forEach(function (k) {
        delete memoryCache[k];
      });
      try {
        Object.keys(sessionStorage).forEach(function (k) {
          if (k.indexOf(CACHE_PREFIX) === 0) sessionStorage.removeItem(k);
        });
      } catch (_) {}
    },
  };

  function init() {
    var startLang = getSavedLang();
    setLanguage(startLang).then(function () {
      if (typeof requestIdleCallback === "function") {
        requestIdleCallback(function () {
          prefetchOthers(startLang);
        });
      } else {
        setTimeout(function () {
          prefetchOthers(startLang);
        }, 1200);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

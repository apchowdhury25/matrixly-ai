/**
 * Matrixly — sync hero carousel agent-slide feature blocks
 * ---------------------------------------------------------------------------
 * After each slide's description <p>, injects the same feature Article cards
 * found on that agent's product page (e.g. BookWise Intent/Availability/Book/Remind,
 * ConnectForge Instant lead response / Appointments / Missed-call recovery).
 *
 * Source of truth (in order):
 *   1. Agent product page: main .grid > article.card-matrix with h2+p
 *   2. Fallback: /agents/ catalog article matching the slide title (ul ▸ items)
 *
 * Any edit to those product/catalog pages is reflected on the next load
 * (sessionStorage cache ~10 min for performance).
 */
(function (global) {
  "use strict";

  var CACHE_KEY = "matrixly-agent-features-v1";
  var CACHE_MS = 10 * 60 * 1000;
  var AGENTS_CATALOG_URL = "/agents/";

  function normalizeName(s) {
    return String(s || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function pathFromHref(href) {
    if (!href) return "";
    try {
      var u = new URL(href, global.location.origin);
      var p = u.pathname.replace(/\/+$/, "") || "/";
      return p;
    } catch (e) {
      return String(href).split("?")[0].replace(/\/+$/, "");
    }
  }

  function readCache() {
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !data.at || Date.now() - data.at > CACHE_MS) return null;
      return data.map || null;
    } catch (e) {
      return null;
    }
  }

  function writeCache(map) {
    try {
      sessionStorage.setItem(
        CACHE_KEY,
        JSON.stringify({ at: Date.now(), map: map })
      );
    } catch (e) { /* ignore quota */ }
  }

  /**
   * Feature cards from agent product pages (screenshots: red-boxed articles).
   * @param {Document} doc
   * @returns {{ title: string, body: string }[]}
   */
  function extractProductFeatures(doc) {
    // Prefer explicitly marked grids (product pages that opt in)
    var grids = doc.querySelectorAll("[data-agent-feature-grid]");
    if (!grids.length) {
      grids = doc.querySelectorAll("main .grid, main section .grid");
    }
    var best = [];

    grids.forEach(function (grid) {
      var arts = grid.querySelectorAll(":scope > article");
      if (arts.length < 2) return;

      var features = [];
      arts.forEach(function (a) {
        var h = a.querySelector("h2, h3");
        var p = a.querySelector("p");
        if (!h || !p) return;
        var title = (h.textContent || "").replace(/\s+/g, " ").trim();
        var body = (p.textContent || "").replace(/\s+/g, " ").trim();
        if (!title || !body) return;
        // Skip deploy / tools / CTA blocks
        if (
          /deploy on this machine|tools it connects|ready to deploy|pricing|get started/i.test(
            title
          )
        ) {
          return;
        }
        // Feature cards are short blurbs, not long prose
        if (body.length > 280) return;
        features.push({ title: title, body: body });
      });

      if (features.length > best.length) best = features;
    });

    return best;
  }

  /**
   * Fallback: Agents catalog page article bullets for this agent name.
   * @param {Document} doc
   * @param {string} agentName
   * @returns {{ title: string, body: string }[]}
   */
  function extractCatalogBullets(doc, agentName) {
    var want = normalizeName(agentName);
    var articles = doc.querySelectorAll(
      "[data-agent-card], article.card-matrix, article"
    );
    for (var i = 0; i < articles.length; i++) {
      var a = articles[i];
      var named = a.getAttribute("data-agent-name");
      var h3 = a.querySelector("h3");
      var label = named || (h3 ? h3.textContent : "");
      if (normalizeName(label) !== want) continue;

      var items = [];
      a.querySelectorAll("ul li").forEach(function (li) {
        var t = (li.textContent || "")
          .replace(/^[▸►•]\s*/, "")
          .replace(/\s+/g, " ")
          .trim();
        if (t) items.push({ title: t, body: "" });
      });
      if (items.length) return items;
    }
    return [];
  }

  async function fetchHtml(url) {
    var res = await fetch(url, { credentials: "same-origin", cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status + " for " + url);
    return res.text();
  }

  function parseHtml(html) {
    return new DOMParser().parseFromString(html, "text/html");
  }

  /**
   * Render feature cards into the slide mount point.
   * @param {HTMLElement} mount
   * @param {{ title: string, body: string }[]} features
   * @param {"product"|"catalog"} source
   */
  function renderFeatures(mount, features, source) {
    if (!mount || !features || !features.length) return;

    mount.innerHTML = "";
    mount.setAttribute("data-features-source", source);
    mount.classList.add("agent-slide-features", "is-synced");

    var hasBodies = features.some(function (f) {
      return f.body && f.body.length > 0;
    });

    if (hasBodies) {
      // Product-page style: compact title + blurb cards (matches red-box screenshots)
      var grid = document.createElement("div");
      grid.className = "agent-feature-grid";
      features.forEach(function (f) {
        var card = document.createElement("div");
        card.className = "agent-feature-card";
        var h = document.createElement("p");
        h.className = "agent-feature-title";
        h.textContent = f.title;
        var b = document.createElement("p");
        b.className = "agent-feature-body";
        b.textContent = f.body;
        card.appendChild(h);
        card.appendChild(b);
        grid.appendChild(card);
      });
      mount.appendChild(grid);
    } else {
      // Catalog bullets as check-style benefits
      var list = document.createElement("div");
      list.className = "space-y-2";
      features.forEach(function (f) {
        var p = document.createElement("p");
        p.className = "agent-slide-benefit";
        p.textContent = f.title;
        list.appendChild(p);
      });
      mount.appendChild(list);
    }
  }

  /**
   * Ensure each slide has a features mount after the last content <p>
   * (the description), before the CTA.
   * @param {HTMLElement} slide
   */
  function ensureMount(slide) {
    var existing = slide.querySelector("[data-agent-features]");
    if (existing) return existing;

    // Prefer replacing legacy benefit block
    var legacy = slide.querySelector(".space-y-2.mb-5, .space-y-2");
    var cta = slide.querySelector("a.btn-primary");

    var mount = document.createElement("div");
    mount.setAttribute("data-agent-features", "");
    mount.className = "agent-slide-features mb-5";

    if (legacy && legacy.querySelector(".agent-slide-benefit")) {
      legacy.replaceWith(mount);
      // keep legacy content as temporary fallback until fetch completes
      mount.appendChild(legacy);
      legacy.classList.remove("mb-5");
      return mount;
    }

    if (cta && cta.parentNode === slide) {
      slide.insertBefore(mount, cta);
    } else {
      slide.appendChild(mount);
    }
    return mount;
  }

  function slideMeta(slide) {
    var h3 = slide.querySelector("h3");
    var cta = slide.querySelector("a.btn-primary[href]");
    return {
      name: h3 ? h3.textContent.trim() : "",
      href: cta ? cta.getAttribute("href") : "",
      path: cta ? pathFromHref(cta.getAttribute("href")) : ""
    };
  }

  /**
   * @param {HTMLElement} [root] carousel root (defaults to #agent-carousel)
   */
  async function sync(root) {
    root = root || document.getElementById("agent-carousel");
    if (!root) return { synced: 0 };

    var slides = Array.prototype.slice.call(
      root.querySelectorAll("[data-agent-slide]")
    );
    if (!slides.length) return { synced: 0 };

    var cache = readCache() || {};
    var catalogDoc = null;
    var synced = 0;

    async function getCatalogDoc() {
      if (catalogDoc) return catalogDoc;
      try {
        var html = await fetchHtml(AGENTS_CATALOG_URL);
        catalogDoc = parseHtml(html);
      } catch (e) {
        catalogDoc = null;
      }
      return catalogDoc;
    }

    await Promise.all(
      slides.map(async function (slide) {
        var meta = slideMeta(slide);
        var mount = ensureMount(slide);
        if (!meta.path && !meta.name) return;

        var cacheKey = meta.path || normalizeName(meta.name);
        var features = cache[cacheKey] || null;
        var source = "cache";

        if (!features || !features.length) {
          // 1) Product page feature articles
          if (meta.path && meta.path !== "/" && meta.path !== "/agents") {
            try {
              var productHtml = await fetchHtml(meta.path + "/");
              // try with and without trailing slash already handled by path
              var productDoc = parseHtml(productHtml);
              features = extractProductFeatures(productDoc);
              source = "product";
            } catch (e1) {
              try {
                var productHtml2 = await fetchHtml(meta.path);
                features = extractProductFeatures(parseHtml(productHtml2));
                source = "product";
              } catch (e2) {
                features = null;
              }
            }
          }

          // 2) Agents catalog fallback
          if (!features || !features.length) {
            var cat = await getCatalogDoc();
            if (cat && meta.name) {
              features = extractCatalogBullets(cat, meta.name);
              source = "catalog";
            }
          }

          if (features && features.length) {
            cache[cacheKey] = features;
          }
        }

        if (features && features.length) {
          renderFeatures(mount, features, source);
          synced += 1;
        }
      })
    );

    writeCache(cache);
    return { synced: synced, total: slides.length };
  }

  // Auto-run when DOM ready if carousel exists
  function boot() {
    if (!document.getElementById("agent-carousel")) return;
    sync().catch(function () { /* silent — static fallback benefits remain */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.MatrixlyAgentSlideSync = {
    sync: sync,
    extractProductFeatures: extractProductFeatures,
    extractCatalogBullets: extractCatalogBullets
  };
})(typeof window !== "undefined" ? window : globalThis);

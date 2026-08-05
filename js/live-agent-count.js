/**
 * Matrixly — dynamic live agent count
 * ---------------------------------------------------------------------------
 * Counts agents marked Live on /agents/ (data-agent-card[data-agent-status=live])
 * and fills any [data-live-agent-count] elements site-wide.
 *
 * By default excludes Starter Pack so copy like
 *   "N live agents + Starter Pack for support, booking & invoices"
 * stays accurate. Override with data-include-starter-pack on the element.
 *
 * Optional:
 *   [data-live-agent-count]              → number only (e.g. 16)
 *   [data-live-agent-count-plus]         → "16+" style if you want a plus
 *   [data-live-agent-phrase]             → full "16 live agents" phrase
 */
(function (global) {
  "use strict";

  var CACHE_KEY = "matrixly-live-agent-count-v1";
  var CACHE_MS = 10 * 60 * 1000;
  var CATALOG_URL = "/agents/";

  function readCache() {
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !data.at || Date.now() - data.at > CACHE_MS) return null;
      return data;
    } catch (e) {
      return null;
    }
  }

  function writeCache(payload) {
    try {
      sessionStorage.setItem(
        CACHE_KEY,
        JSON.stringify(Object.assign({ at: Date.now() }, payload))
      );
    } catch (e) { /* ignore */ }
  }

  /**
   * @param {Document} doc
   * @returns {{ live: number, liveIncludingStarter: number, total: number, names: string[] }}
   */
  function countFromDoc(doc) {
    var cards = Array.prototype.slice.call(
      doc.querySelectorAll("[data-agent-card], article.card-matrix")
    );
    var liveNames = [];
    var liveIncludingStarter = 0;
    var live = 0;
    var total = 0;

    cards.forEach(function (card) {
      // Prefer catalog cards inside the agents grid
      if (!card.matches("[data-agent-card]") && !card.querySelector("h3")) return;
      total += 1;

      var path = (card.getAttribute("data-agent-path") || "").replace(/\/+$/, "");
      var status = (card.getAttribute("data-agent-status") || "").toLowerCase();
      var isLive = status === "live";

      if (!status) {
        // Fallback: badge text "Live"
        var spans = card.querySelectorAll("span");
        for (var i = 0; i < spans.length; i++) {
          if ((spans[i].textContent || "").trim() === "Live") {
            isLive = true;
            break;
          }
        }
      }

      if (!isLive) return;

      var nameEl = card.querySelector("h3");
      var name = (
        card.getAttribute("data-agent-name") ||
        (nameEl ? nameEl.textContent : "") ||
        ""
      ).trim();

      liveIncludingStarter += 1;
      var isStarter =
        path === "/starter-pack" ||
        /^starter pack$/i.test(name);

      if (!isStarter) {
        live += 1;
        if (name) liveNames.push(name);
      }
    });

    return {
      live: live,
      liveIncludingStarter: liveIncludingStarter,
      total: total,
      names: liveNames
    };
  }

  async function fetchCounts() {
    var cached = readCache();
    if (cached && typeof cached.live === "number") return cached;

    var res = await fetch(CATALOG_URL, {
      credentials: "same-origin",
      cache: "no-store"
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    var html = await res.text();
    var doc = new DOMParser().parseFromString(html, "text/html");
    var counts = countFromDoc(doc);
    writeCache(counts);
    return counts;
  }

  function applyCounts(counts) {
    if (!counts || typeof counts.live !== "number") return;

    document.querySelectorAll("[data-live-agent-count]").forEach(function (el) {
      var includeStarter =
        el.getAttribute("data-include-starter-pack") === "true" ||
        el.getAttribute("data-include-starter-pack") === "";
      var n = includeStarter ? counts.liveIncludingStarter : counts.live;
      if (n < 1) return;
      el.textContent = String(n);
    });

    document.querySelectorAll("[data-live-agent-count-plus]").forEach(function (el) {
      var includeStarter =
        el.getAttribute("data-include-starter-pack") === "true";
      var n = includeStarter ? counts.liveIncludingStarter : counts.live;
      if (n < 1) return;
      el.textContent = n + "+";
    });

    document.querySelectorAll("[data-live-agent-phrase]").forEach(function (el) {
      var includeStarter =
        el.getAttribute("data-include-starter-pack") === "true";
      var n = includeStarter ? counts.liveIncludingStarter : counts.live;
      if (n < 1) return;
      var label = n === 1 ? "live agent" : "live agents";
      el.textContent = n + " " + label;
    });
  }

  async function refresh() {
    try {
      var counts = await fetchCounts();
      applyCounts(counts);
      return counts;
    } catch (e) {
      return null;
    }
  }

  function boot() {
    if (!document.querySelector("[data-live-agent-count], [data-live-agent-count-plus], [data-live-agent-phrase]")) {
      return;
    }
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.MatrixlyLiveAgentCount = {
    refresh: refresh,
    countFromDoc: countFromDoc,
    fetchCounts: fetchCounts
  };
})(typeof window !== "undefined" ? window : globalThis);

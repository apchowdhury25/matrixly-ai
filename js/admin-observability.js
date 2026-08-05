/**
 * Matrixly QA Admin — Observability & Infrastructure module
 * ---------------------------------------------------------------------------
 * Self-hosted stack status probes for:
 *   Docker Compose · Crawl4AI · Playwright (via Crawl4AI) · Prometheus ·
 *   Grafana · Loki
 *
 * Used by /admin (QA Admin console). Pure browser JS — no build step.
 * Services may block cross-origin probes; failures surface as "unreachable"
 * rather than hard errors so the console remains usable offline.
 *
 * Configure endpoints via localStorage key: matrixly-obs-endpoints
 * or window.MATRIXLY_OBS_ENDPOINTS before this script loads.
 *
 * Placeholder API endpoints (for future Matrixly control-plane proxy):
 *   GET  /api/obs/status          → aggregate health
 *   GET  /api/obs/crawl4ai        → Crawl4AI metrics
 *   GET  /api/obs/prometheus      → scrape targets
 *   GET  /api/obs/loki/errors     → recent error count
 *   POST /api/obs/stack/restart   → docker compose restart (server-side only)
 */
(function (global) {
  "use strict";

  // -------------------------------------------------------------------------
  // Types (JSDoc — mirrors what a React/Next TypeScript layer would export)
  // -------------------------------------------------------------------------

  /**
   * @typedef {"ok"|"warn"|"bad"|"unknown"} StatusLevel
   * @typedef {{ level: StatusLevel, label: string, detail?: string, latencyMs?: number }} ServiceStatus
   * @typedef {{
   *   crawl4ai: string,
   *   prometheus: string,
   *   grafana: string,
   *   loki: string,
   *   controlPlane?: string
   * }} ObsEndpoints
   * @typedef {{
   *   activeBrowsers: number|null,
   *   requestRate: number|null,
   *   successRate: number|null,
   *   p95LatencyMs: number|null,
   *   memoryBytes: number|null,
   *   errorRate: number|null,
   *   playwrightVersion: string|null
   * }} CrawlMetrics
   * @typedef {{
   *   stack: ServiceStatus,
   *   crawl4ai: ServiceStatus,
   *   playwright: ServiceStatus,
   *   prometheus: ServiceStatus,
   *   grafana: ServiceStatus,
   *   loki: ServiceStatus,
   *   metrics: CrawlMetrics,
   *   prometheusTargets: Array<{ job: string, health: string, lastError?: string }>,
   *   lokiRecentErrors: number|null,
   *   updatedAt: string
   * }} ObsSnapshot
   */

  var STORAGE_KEY = "matrixly-obs-endpoints";
  var VIEW_KEY = "matrixly-obs-grafana-view";

  /** @type {ObsEndpoints} */
  var DEFAULT_ENDPOINTS = {
    crawl4ai: "http://127.0.0.1:11235",
    prometheus: "http://127.0.0.1:9090",
    grafana: "http://127.0.0.1:3000",
    loki: "http://127.0.0.1:3100",
    controlPlane: "" // optional same-origin proxy, e.g. "/api/obs"
  };

  /** Full production docker-compose reference (also in infra/observability/) */
  var DOCKER_COMPOSE_YML = [
    "# Matrixly Observability Stack — production reference",
    "# Full file: infra/observability/docker-compose.yml",
    "# Run: cd infra/observability && docker compose up -d",
    "",
    "name: matrixly-observability",
    "",
    "services:",
    "  crawl4ai:",
    "    image: unclecode/crawl4ai:latest",
    "    container_name: matrixly-crawl4ai",
    "    ports:",
    "      - \"11235:11235\"",
    "    environment:",
    "      - CRAWL4AI_API_TOKEN=${CRAWL4AI_API_TOKEN:-}",
    "      - MAX_CONCURRENT_BROWSERS=${MAX_CONCURRENT_BROWSERS:-4}",
    "    volumes:",
    "      - crawl4ai_data:/data",
    "    healthcheck:",
    "      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:11235/health\"]",
    "      interval: 30s",
    "      timeout: 10s",
    "      retries: 3",
    "    restart: unless-stopped",
    "    networks: [matrixly-obs]",
    "",
    "  prometheus:",
    "    image: prom/prometheus:v2.54.1",
    "    container_name: matrixly-prometheus",
    "    ports:",
    "      - \"9090:9090\"",
    "    command:",
    "      - --config.file=/etc/prometheus/prometheus.yml",
    "      - --storage.tsdb.path=/prometheus",
    "      - --storage.tsdb.retention.time=15d",
    "      - --web.enable-lifecycle",
    "    volumes:",
    "      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro",
    "      - prometheus_data:/prometheus",
    "    restart: unless-stopped",
    "    networks: [matrixly-obs]",
    "",
    "  grafana:",
    "    image: grafana/grafana:11.2.0",
    "    container_name: matrixly-grafana",
    "    ports:",
    "      - \"3000:3000\"",
    "    environment:",
    "      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}",
    "      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-matrixly-change-me}",
    "      - GF_USERS_ALLOW_SIGN_UP=false",
    "      - GF_SERVER_ROOT_URL=${GRAFANA_ROOT_URL:-http://127.0.0.1:3000}",
    "    volumes:",
    "      - grafana_data:/var/lib/grafana",
    "      - ./grafana/provisioning:/etc/grafana/provisioning:ro",
    "      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro",
    "    depends_on: [prometheus, loki]",
    "    restart: unless-stopped",
    "    networks: [matrixly-obs]",
    "",
    "  loki:",
    "    image: grafana/loki:3.1.1",
    "    container_name: matrixly-loki",
    "    ports:",
    "      - \"3100:3100\"",
    "    command: -config.file=/etc/loki/loki-config.yml",
    "    volumes:",
    "      - ./loki-config.yml:/etc/loki/loki-config.yml:ro",
    "      - loki_data:/loki",
    "    restart: unless-stopped",
    "    networks: [matrixly-obs]",
    "",
    "  promtail:",
    "    image: grafana/promtail:3.1.1",
    "    container_name: matrixly-promtail",
    "    volumes:",
    "      - ./promtail-config.yml:/etc/promtail/config.yml:ro",
    "      - /var/lib/docker/containers:/var/lib/docker/containers:ro",
    "      - /var/run/docker.sock:/var/run/docker.sock:ro",
    "    command: -config.file=/etc/promtail/config.yml",
    "    depends_on: [loki]",
    "    restart: unless-stopped",
    "    networks: [matrixly-obs]",
    "",
    "networks:",
    "  matrixly-obs:",
    "    driver: bridge",
    "    name: matrixly-observability",
    "",
    "volumes:",
    "  crawl4ai_data:",
    "  prometheus_data:",
    "  grafana_data:",
    "  loki_data:"
  ].join("\n");

  var RESTART_COMMANDS = [
    "# From repo root — restart the full observability stack",
    "cd infra/observability",
    "docker compose pull",
    "docker compose up -d",
    "",
    "# Restart a single service",
    "docker compose restart crawl4ai",
    "docker compose restart prometheus grafana loki promtail",
    "",
    "# View status",
    "docker compose ps",
    "docker compose logs -f --tail=100 crawl4ai"
  ].join("\n");

  // -------------------------------------------------------------------------
  // Endpoint config
  // -------------------------------------------------------------------------

  /** @returns {ObsEndpoints} */
  function getEndpoints() {
    var merged = Object.assign({}, DEFAULT_ENDPOINTS);
    if (global.MATRIXLY_OBS_ENDPOINTS && typeof global.MATRIXLY_OBS_ENDPOINTS === "object") {
      Object.assign(merged, global.MATRIXLY_OBS_ENDPOINTS);
    }
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) Object.assign(merged, JSON.parse(raw));
    } catch (e) { /* ignore */ }
    return merged;
  }

  /** @param {Partial<ObsEndpoints>} partial */
  function setEndpoints(partial) {
    var next = Object.assign(getEndpoints(), partial || {});
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch (e) { /* ignore */ }
    return next;
  }

  // -------------------------------------------------------------------------
  // Low-level probe helpers
  // -------------------------------------------------------------------------

  /**
   * Probe a URL; returns status without throwing.
   * @param {string} url
   * @param {{ timeoutMs?: number, method?: string }} [opts]
   * @returns {Promise<{ ok: boolean, status: number|null, latencyMs: number, error?: string, body?: string }>}
   */
  async function probe(url, opts) {
    opts = opts || {};
    var timeoutMs = opts.timeoutMs != null ? opts.timeoutMs : 4000;
    var method = opts.method || "GET";
    var start = performance.now();
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = controller
      ? setTimeout(function () { controller.abort(); }, timeoutMs)
      : null;

    try {
      var res = await fetch(url, {
        method: method,
        mode: "cors",
        cache: "no-store",
        signal: controller ? controller.signal : undefined,
        credentials: "omit"
      });
      var latencyMs = Math.round(performance.now() - start);
      var body = "";
      try {
        body = await res.text();
      } catch (e) { /* empty */ }
      return {
        ok: res.ok,
        status: res.status,
        latencyMs: latencyMs,
        body: body
      };
    } catch (err) {
      return {
        ok: false,
        status: null,
        latencyMs: Math.round(performance.now() - start),
        error: String((err && err.name === "AbortError") ? "timeout" : (err && err.message) || err)
      };
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  /**
   * @param {boolean} ok
   * @param {string} labelOk
   * @param {string} labelBad
   * @param {object} [extra]
   * @returns {ServiceStatus}
   */
  function statusFromProbe(ok, labelOk, labelBad, extra) {
    extra = extra || {};
    return {
      level: ok ? "ok" : (extra.warn ? "warn" : "bad"),
      label: ok ? labelOk : labelBad,
      detail: extra.detail,
      latencyMs: extra.latencyMs
    };
  }

  // -------------------------------------------------------------------------
  // Service-specific collectors
  // -------------------------------------------------------------------------

  /**
   * Prefer control-plane aggregate if configured; else direct probes.
   * @returns {Promise<ObsSnapshot>}
   */
  async function fetchSnapshot() {
    var ep = getEndpoints();

    // Optional same-origin control plane (future API)
    if (ep.controlPlane) {
      try {
        var agg = await probe(ep.controlPlane.replace(/\/$/, "") + "/status", { timeoutMs: 5000 });
        if (agg.ok && agg.body) {
          var parsed = JSON.parse(agg.body);
          if (parsed && parsed.updatedAt) return normalizeSnapshot(parsed);
        }
      } catch (e) { /* fall through to direct probes */ }
    }

    var results = await Promise.all([
      probeCrawl4ai(ep.crawl4ai),
      probePrometheus(ep.prometheus),
      probeGrafana(ep.grafana),
      probeLoki(ep.loki)
    ]);

    var crawl = results[0];
    var prom = results[1];
    var graf = results[2];
    var loki = results[3];

    var servicesUp = [crawl.status, prom.status, graf.status, loki.status]
      .filter(function (s) { return s.level === "ok"; }).length;
    var stackLevel = servicesUp === 4 ? "ok" : servicesUp >= 2 ? "warn" : servicesUp > 0 ? "warn" : "bad";

    /** @type {ObsSnapshot} */
    var snap = {
      stack: {
        level: stackLevel,
        label: servicesUp + "/4 core services reachable",
        detail: "Direct browser probes (CORS may limit detail)"
      },
      crawl4ai: crawl.status,
      playwright: crawl.playwright,
      prometheus: prom.status,
      grafana: graf.status,
      loki: loki.status,
      metrics: crawl.metrics,
      prometheusTargets: prom.targets,
      lokiRecentErrors: loki.recentErrors,
      updatedAt: new Date().toISOString()
    };
    return snap;
  }

  /** @param {string} base */
  async function probeCrawl4ai(base) {
    var root = (base || "").replace(/\/$/, "");
    var health = await probe(root + "/health");
    var metrics = emptyMetrics();
    var playwrightStatus = {
      level: "unknown",
      label: "Unknown (via Crawl4AI)",
      detail: "Playwright runs inside the Crawl4AI container"
    };

    // Alternate endpoints used by various Crawl4AI builds
    if (!health.ok) {
      var alt = await probe(root + "/");
      if (alt.ok) health = alt;
    }

    // Best-effort metrics scrape (may be absent or CORS-blocked)
    var mProbe = await probe(root + "/metrics");
    if (mProbe.ok && mProbe.body) {
      metrics = parsePrometheusText(mProbe.body, metrics);
    }

    // Monitor / playground reachability (HEAD/GET)
    var monitor = await probe(root + "/monitor");

    if (health.ok) {
      playwrightStatus = {
        level: "ok",
        label: "Browser pool expected healthy",
        detail: metrics.activeBrowsers != null
          ? "Active browsers: " + metrics.activeBrowsers
          : "Health OK — pool size not exposed via /metrics",
        latencyMs: health.latencyMs
      };
      if (metrics.playwrightVersion) {
        playwrightStatus.detail += " · Playwright " + metrics.playwrightVersion;
      }
    } else if (health.error) {
      playwrightStatus = {
        level: "bad",
        label: "Unreachable",
        detail: health.error,
        latencyMs: health.latencyMs
      };
    }

    return {
      status: statusFromProbe(
        health.ok,
        "Connected",
        health.error === "timeout" ? "Timeout" : "Unreachable",
        {
          latencyMs: health.latencyMs,
          detail: health.ok
            ? "Port 11235 · monitor " + (monitor.ok ? "up" : "n/a")
            : (health.error || ("HTTP " + health.status)),
          warn: !health.ok && health.error && health.error.indexOf("Failed to fetch") !== -1
        }
      ),
      playwright: playwrightStatus,
      metrics: metrics
    };
  }

  /** @param {string} base */
  async function probePrometheus(base) {
    var root = (base || "").replace(/\/$/, "");
    var healthy = await probe(root + "/-/healthy");
    var targets = [];

    if (healthy.ok) {
      var tRes = await probe(root + "/api/v1/targets");
      if (tRes.ok && tRes.body) {
        try {
          var data = JSON.parse(tRes.body);
          var active = (data.data && data.data.activeTargets) || [];
          targets = active.map(function (t) {
            return {
              job: (t.labels && t.labels.job) || "unknown",
              health: t.health || "unknown",
              lastError: t.lastError || ""
            };
          });
        } catch (e) { /* ignore parse */ }
      }
    }

    var upCount = targets.filter(function (t) { return t.health === "up"; }).length;
    var detail = healthy.ok
      ? (targets.length ? upCount + "/" + targets.length + " targets up" : "Healthy (targets API may be CORS-blocked)")
      : (healthy.error || "HTTP " + healthy.status);

    return {
      status: statusFromProbe(healthy.ok, "Healthy", "Unreachable", {
        latencyMs: healthy.latencyMs,
        detail: detail
      }),
      targets: targets
    };
  }

  /** @param {string} base */
  async function probeGrafana(base) {
    var root = (base || "").replace(/\/$/, "");
    var health = await probe(root + "/api/health");
    var detail = "Admin UI · Matrixly Crawl4AI dashboard";
    if (health.ok && health.body) {
      try {
        var j = JSON.parse(health.body);
        if (j.database) detail = "DB: " + j.database + " · version probe OK";
      } catch (e) { /* ignore */ }
    }
    return {
      status: statusFromProbe(health.ok, "Online", "Unreachable", {
        latencyMs: health.latencyMs,
        detail: health.ok ? detail : (health.error || "HTTP " + health.status)
      })
    };
  }

  /** @param {string} base */
  async function probeLoki(base) {
    var root = (base || "").replace(/\/$/, "");
    var ready = await probe(root + "/ready");
    // LogQL query for recent errors — often CORS-blocked from browser
    var recentErrors = null;
    if (ready.ok) {
      var q = encodeURIComponent('{container=~".*crawl4ai.*"} |= "ERROR"');
      var end = Date.now() * 1e6;
      var start = (Date.now() - 3600 * 1000) * 1e6;
      var qUrl = root + "/loki/api/v1/query_range?query=" + q +
        "&start=" + start + "&end=" + end + "&limit=100";
      var qRes = await probe(qUrl);
      if (qRes.ok && qRes.body) {
        try {
          var data = JSON.parse(qRes.body);
          var streams = (data.data && data.data.result) || [];
          var count = 0;
          streams.forEach(function (s) {
            count += (s.values && s.values.length) || 0;
          });
          recentErrors = count;
        } catch (e) { /* ignore */ }
      }
    }
    return {
      status: statusFromProbe(ready.ok, "Ready", "Unreachable", {
        latencyMs: ready.latencyMs,
        detail: ready.ok
          ? (recentErrors != null ? recentErrors + " ERROR lines (1h)" : "Ready (LogQL may need Grafana Explore)")
          : (ready.error || "HTTP " + ready.status)
      }),
      recentErrors: recentErrors
    };
  }

  /** @returns {CrawlMetrics} */
  function emptyMetrics() {
    return {
      activeBrowsers: null,
      requestRate: null,
      successRate: null,
      p95LatencyMs: null,
      memoryBytes: null,
      errorRate: null,
      playwrightVersion: null
    };
  }

  /**
   * Minimal Prometheus text exposition parser for known Crawl4AI-ish metrics.
   * @param {string} text
   * @param {CrawlMetrics} into
   */
  function parsePrometheusText(text, into) {
    var lines = text.split("\n");
    lines.forEach(function (line) {
      if (!line || line.charAt(0) === "#") return;
      var parts = line.trim().split(/\s+/);
      if (parts.length < 2) return;
      var name = parts[0].replace(/\{.*\}$/, "");
      var val = parseFloat(parts[1]);
      if (isNaN(val)) return;
      if (name === "crawl4ai_browser_pool_size" || name === "crawl4ai_active_browsers") {
        into.activeBrowsers = val;
      } else if (name === "process_resident_memory_bytes") {
        into.memoryBytes = val;
      } else if (name.indexOf("playwright") !== -1 && name.indexOf("version") !== -1) {
        into.playwrightVersion = String(val);
      }
    });
    return into;
  }

  /** @param {object} raw @returns {ObsSnapshot} */
  function normalizeSnapshot(raw) {
    return {
      stack: raw.stack || { level: "unknown", label: "n/a" },
      crawl4ai: raw.crawl4ai || { level: "unknown", label: "n/a" },
      playwright: raw.playwright || { level: "unknown", label: "n/a" },
      prometheus: raw.prometheus || { level: "unknown", label: "n/a" },
      grafana: raw.grafana || { level: "unknown", label: "n/a" },
      loki: raw.loki || { level: "unknown", label: "n/a" },
      metrics: Object.assign(emptyMetrics(), raw.metrics || {}),
      prometheusTargets: raw.prometheusTargets || [],
      lokiRecentErrors: raw.lokiRecentErrors != null ? raw.lokiRecentErrors : null,
      updatedAt: raw.updatedAt || new Date().toISOString()
    };
  }

  // -------------------------------------------------------------------------
  // UI helpers
  // -------------------------------------------------------------------------

  function formatBytes(n) {
    if (n == null || isNaN(n)) return "—";
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB";
    return (n / 1073741824).toFixed(2) + " GB";
  }

  function formatMetric(v, suffix) {
    if (v == null || isNaN(v)) return "—";
    if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(2) + (suffix || "");
    return String(v) + (suffix || "");
  }

  function badgeClass(level) {
    if (level === "ok") return "obs-badge ok";
    if (level === "warn") return "obs-badge warn";
    if (level === "bad") return "obs-badge bad";
    return "obs-badge unknown";
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
        resolve();
      } catch (e) {
        reject(e);
      } finally {
        document.body.removeChild(ta);
      }
    });
  }

  /**
   * Grafana deep links
   * @param {ObsEndpoints} ep
   * @param {"metrics"|"logs"|"combined"} view
   */
  function grafanaUrls(ep, view) {
    var g = (ep.grafana || "").replace(/\/$/, "");
    var dash = g + "/d/matrixly-crawl4ai/matrixly-crawl4ai-monitoring";
    var exploreMetrics = g + "/explore?orgId=1&left=" + encodeURIComponent(JSON.stringify({
      datasource: "Prometheus",
      queries: [{ refId: "A", expr: "up" }],
      range: { from: "now-1h", to: "now" }
    }));
    var exploreLogs = g + "/explore?orgId=1&left=" + encodeURIComponent(JSON.stringify({
      datasource: "Loki",
      queries: [{
        refId: "A",
        expr: '{container=~".*crawl4ai.*"} |= "ERROR"'
      }],
      range: { from: "now-1h", to: "now" }
    }));
    return {
      dashboard: dash + "?orgId=1&from=now-1h&to=now",
      exploreMetrics: exploreMetrics,
      exploreLogs: exploreLogs,
      home: g,
      iframe: dash + "?orgId=1&from=now-1h&to=now&kiosk",
      view: view || "combined"
    };
  }

  function crawl4aiUrls(ep) {
    var c = (ep.crawl4ai || "").replace(/\/$/, "");
    return {
      root: c,
      playground: c + "/playground",
      monitor: c + "/monitor",
      health: c + "/health",
      metrics: c + "/metrics"
    };
  }

  /**
   * Mount observability UI into a root element.
   * @param {HTMLElement} root
   * @param {{ autoRefreshMs?: number }} [options]
   */
  function mount(root, options) {
    if (!root) return { unmount: function () {} };
    options = options || {};
    var autoRefreshMs = options.autoRefreshMs != null ? options.autoRefreshMs : 0;
    var refreshTimer = null;
    /** @type {ObsSnapshot|null} */
    var lastSnap = null;
    var grafanaView = "combined";
    try {
      grafanaView = localStorage.getItem(VIEW_KEY) || "combined";
    } catch (e) { /* ignore */ }

    root.innerHTML = buildShellHtml();
    bindShell(root);

    async function refresh() {
      setRefreshing(true);
      try {
        lastSnap = await fetchSnapshot();
        paint(lastSnap);
      } catch (err) {
        paintError(String(err && err.message || err));
      } finally {
        setRefreshing(false);
      }
    }

    function setRefreshing(on) {
      var btn = root.querySelector("[data-obs-refresh]");
      if (btn) {
        btn.disabled = on;
        btn.textContent = on ? "Refreshing…" : "Refresh Status";
      }
      var pulse = root.querySelector("[data-obs-updated]");
      if (pulse && on) pulse.textContent = "Probing services…";
    }

    function paintError(msg) {
      var el = root.querySelector("[data-obs-updated]");
      if (el) el.textContent = "Error: " + msg;
    }

    /**
     * @param {ObsSnapshot} snap
     */
    function paint(snap) {
      var ep = getEndpoints();
      var cUrls = crawl4aiUrls(ep);
      var gUrls = grafanaUrls(ep, grafanaView);

      setText(root, "[data-obs-updated]", "Updated " + new Date(snap.updatedAt).toLocaleString());

      paintServiceCard(root, "stack", snap.stack);
      paintServiceCard(root, "crawl4ai", snap.crawl4ai);
      paintServiceCard(root, "playwright", snap.playwright);
      paintServiceCard(root, "prometheus", snap.prometheus);
      paintServiceCard(root, "grafana", snap.grafana);
      paintServiceCard(root, "loki", snap.loki);

      // Metrics (cards + KPI strip share the same data-* hooks)
      var m = snap.metrics || emptyMetrics();
      setTextAll(root, "[data-metric-browsers]", formatMetric(m.activeBrowsers));
      setTextAll(root, "[data-metric-rate]", formatMetric(m.requestRate, " /s"));
      setTextAll(root, "[data-metric-success]", m.successRate != null ? (m.successRate * 100).toFixed(1) + "%" : "—");
      setTextAll(root, "[data-metric-p95]", m.p95LatencyMs != null ? formatMetric(m.p95LatencyMs, " ms") : "—");
      setTextAll(root, "[data-metric-mem]", formatBytes(m.memoryBytes));
      setTextAll(root, "[data-metric-errors]", formatMetric(m.errorRate, " /s"));
      setTextAll(root, "[data-metric-pw-ver]", m.playwrightVersion || "bundled w/ Crawl4AI");
      setTextAll(root, "[data-loki-errors]", snap.lokiRecentErrors != null ? String(snap.lokiRecentErrors) : "—");

      // Links
      setHref(root, "[data-link-crawl4ai]", cUrls.root);
      setHref(root, "[data-link-playground]", cUrls.playground);
      setHref(root, "[data-link-monitor]", cUrls.monitor);
      setHref(root, "[data-link-prometheus]", ep.prometheus);
      setHref(root, "[data-link-grafana]", gUrls.dashboard);
      setHref(root, "[data-link-grafana-home]", gUrls.home);
      setHref(root, "[data-link-loki]", ep.loki);
      setHref(root, "[data-link-explore-logs]", gUrls.exploreLogs);
      setHref(root, "[data-link-explore-metrics]", gUrls.exploreMetrics);

      // Prometheus targets table
      var tbody = root.querySelector("[data-prom-targets]");
      if (tbody) {
        tbody.innerHTML = "";
        if (!snap.prometheusTargets.length) {
          tbody.innerHTML = "<tr><td colspan=\"3\" class=\"obs-muted\">No targets (service down or CORS-blocked). Open Prometheus UI → Status → Targets.</td></tr>";
        } else {
          snap.prometheusTargets.forEach(function (t) {
            var tr = document.createElement("tr");
            var hc = t.health === "up" ? "status-ok" : "status-fail";
            tr.innerHTML =
              "<td>" + escapeHtml(t.job) + "</td>" +
              "<td class=\"" + hc + "\">" + escapeHtml(t.health) + "</td>" +
              "<td class=\"obs-muted\">" + escapeHtml(t.lastError || "—") + "</td>";
            tbody.appendChild(tr);
          });
        }
      }

      // Grafana iframe / view
      updateGrafanaView(root, gUrls, grafanaView);

      // Endpoint inputs
      var form = root.querySelector("[data-obs-endpoints]");
      if (form) {
        form.querySelector("[name=crawl4ai]").value = ep.crawl4ai;
        form.querySelector("[name=prometheus]").value = ep.prometheus;
        form.querySelector("[name=grafana]").value = ep.grafana;
        form.querySelector("[name=loki]").value = ep.loki;
      }
    }

    function paintServiceCard(rootEl, key, st) {
      var badge = rootEl.querySelector("[data-status-" + key + "]");
      if (badge) {
        badge.className = badgeClass(st.level);
        badge.textContent = st.label;
      }
      var detail = rootEl.querySelector("[data-detail-" + key + "]");
      if (detail) {
        var d = st.detail || "";
        if (st.latencyMs != null) d += (d ? " · " : "") + st.latencyMs + " ms";
        detail.textContent = d || "—";
      }
    }

    function updateGrafanaView(rootEl, gUrls, view) {
      rootEl.querySelectorAll("[data-gview]").forEach(function (btn) {
        btn.classList.toggle("active", btn.getAttribute("data-gview") === view);
      });
      var frame = rootEl.querySelector("[data-grafana-iframe]");
      var placeholder = rootEl.querySelector("[data-grafana-placeholder]");
      var openBtn = rootEl.querySelector("[data-open-grafana-view]");
      if (openBtn) {
        if (view === "metrics") openBtn.href = gUrls.exploreMetrics;
        else if (view === "logs") openBtn.href = gUrls.exploreLogs;
        else openBtn.href = gUrls.dashboard;
      }
      // Iframe often blocked by X-Frame-Options; show CTA fallback
      if (frame) {
        frame.src = gUrls.iframe;
        frame.onload = function () {
          /* if blocked, browser may show empty — keep placeholder visible via CSS */
        };
      }
      if (placeholder) {
        var hint =
          view === "metrics"
            ? "Metrics view (Prometheus): Request rate, success rate, latency, memory."
            : view === "logs"
              ? "Logs view (Loki): Crawl4AI ERROR lines and agent crawl failures."
              : "Combined dashboard: Matrixly Crawl4AI Monitoring (metrics + error logs).";
        placeholder.querySelector("[data-gview-hint]").textContent = hint;
      }
    }

    function bindShell(rootEl) {
      var refreshBtn = rootEl.querySelector("[data-obs-refresh]");
      if (refreshBtn) {
        refreshBtn.addEventListener("click", function () {
          refresh();
        });
      }

      function toggleCompose(sourceBtn) {
        var block = rootEl.querySelector("[data-obs-compose]");
        if (!block) return;
        var open = block.classList.toggle("open");
        rootEl.querySelectorAll("[data-obs-toggle-compose]").forEach(function (btn) {
          var isPrimary = btn.classList.contains("btn") && !btn.classList.contains("btn-sm");
          if (isPrimary || sourceBtn === btn) {
            btn.textContent = open ? "Hide docker-compose.yml" : "View Full docker-compose.yml";
          }
          btn.setAttribute("aria-expanded", open ? "true" : "false");
        });
        // Keep short label on in-card control
        rootEl.querySelectorAll(".obs-card [data-obs-toggle-compose]").forEach(function (btn) {
          btn.textContent = open ? "Hide compose" : "View compose";
        });
      }

      rootEl.querySelectorAll("[data-obs-toggle-compose]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          toggleCompose(btn);
        });
      });

      var copyCompose = rootEl.querySelector("[data-obs-copy-compose]");
      if (copyCompose) {
        copyCompose.addEventListener("click", function () {
          var btn = this;
          copyText(DOCKER_COMPOSE_YML).then(function () {
            btn.textContent = "Copied!";
            setTimeout(function () { btn.textContent = "Copy compose"; }, 1500);
          });
        });
      }

      rootEl.querySelectorAll("[data-obs-restart]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var block = rootEl.querySelector("[data-obs-restart-cmds]");
          if (block) block.classList.toggle("open");
        });
      });

      var copyRestart = rootEl.querySelector("[data-obs-copy-restart]");
      if (copyRestart) {
        copyRestart.addEventListener("click", function () {
          var btn = this;
          copyText(RESTART_COMMANDS).then(function () {
            btn.textContent = "Copied!";
            setTimeout(function () { btn.textContent = "Copy commands"; }, 1500);
          });
        });
      }

      rootEl.querySelectorAll("[data-gview]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          grafanaView = btn.getAttribute("data-gview") || "combined";
          try { localStorage.setItem(VIEW_KEY, grafanaView); } catch (e) { /* ignore */ }
          if (lastSnap) paint(lastSnap);
          else {
            var ep = getEndpoints();
            updateGrafanaView(rootEl, grafanaUrls(ep, grafanaView), grafanaView);
          }
        });
      });

      var form = rootEl.querySelector("[data-obs-endpoints]");
      if (form) {
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          setEndpoints({
            crawl4ai: form.querySelector("[name=crawl4ai]").value.trim(),
            prometheus: form.querySelector("[name=prometheus]").value.trim(),
            grafana: form.querySelector("[name=grafana]").value.trim(),
            loki: form.querySelector("[name=loki]").value.trim()
          });
          refresh();
        });
      }

      // Pre-fill compose code
      var pre = rootEl.querySelector("[data-obs-compose-code]");
      if (pre) pre.textContent = DOCKER_COMPOSE_YML;
      var preR = rootEl.querySelector("[data-obs-restart-code]");
      if (preR) preR.textContent = RESTART_COMMANDS;
    }

    function setText(rootEl, sel, text) {
      var el = rootEl.querySelector(sel);
      if (el) el.textContent = text;
    }
    function setTextAll(rootEl, sel, text) {
      rootEl.querySelectorAll(sel).forEach(function (el) {
        el.textContent = text;
      });
    }
    function setHref(rootEl, sel, href) {
      rootEl.querySelectorAll(sel).forEach(function (el) {
        if (href) el.href = href;
      });
    }
    function escapeHtml(s) {
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function buildShellHtml() {
      return [
        '<div class="obs-section">',
        '  <div class="obs-hero">',
        '    <div>',
        '      <h2 class="obs-title">Observability Stack <span class="obs-title-accent">(Self-Hosted)</span></h2>',
        '      <p class="obs-lede">Own your crawl + monitoring plane for <strong>SEOForge</strong>, <strong>ContentForge</strong>, <strong>Lead Qualifier</strong>, and other Matrixly agents — cost control, privacy, and reliability without SaaS lock-in.</p>',
        '    </div>',
        '    <div class="obs-hero-meta">',
        '      <span class="obs-badge unknown" data-status-stack>Checking…</span>',
        '      <span class="obs-muted" data-obs-updated>—</span>',
        '    </div>',
        '  </div>',

        '  <div class="obs-actions">',
        '    <button type="button" class="btn" data-obs-refresh>Refresh Status</button>',
        '    <button type="button" class="btn ghost" data-obs-restart>Restart Stack</button>',
        '    <button type="button" class="btn ghost" data-obs-toggle-compose aria-expanded="false">View Full docker-compose.yml</button>',
        '    <a class="btn ghost" data-link-grafana href="http://127.0.0.1:3000" target="_blank" rel="noopener">Open Grafana</a>',
        '    <a class="btn ghost" data-link-monitor href="http://127.0.0.1:11235/monitor" target="_blank" rel="noopener">Open Crawl4AI Monitor</a>',
        '    <a class="btn ghost" data-link-explore-logs href="http://127.0.0.1:3000" target="_blank" rel="noopener">View Recent Logs</a>',
        '  </div>',

        '  <div class="obs-collapse" data-obs-restart-cmds>',
        '    <div class="obs-collapse-head">',
        '      <span>Restart commands (run on the host — browser cannot restart Docker)</span>',
        '      <button type="button" class="btn ghost btn-sm" data-obs-copy-restart>Copy commands</button>',
        '    </div>',
        '    <pre class="cmd" data-obs-restart-code></pre>',
        '  </div>',

        '  <div class="obs-collapse" data-obs-compose>',
        '    <div class="obs-collapse-head">',
        '      <span>Production docker-compose.yml (Crawl4AI · Prometheus · Grafana · Loki · Promtail)</span>',
        '      <button type="button" class="btn ghost btn-sm" data-obs-copy-compose>Copy compose</button>',
        '    </div>',
        '    <pre class="cmd" data-obs-compose-code></pre>',
        '    <p class="tip">Source of truth on disk: <code>infra/observability/docker-compose.yml</code></p>',
        '  </div>',

        '  <div class="obs-grid">',
        // Docker Compose
        cardHtml("Docker Compose", "stack", [
          '<p class="obs-card-desc">Orchestrates the self-hosted stack. Status is derived from service reachability probes.</p>',
          '<ul class="obs-kv">',
          '  <li><span>Stack</span><strong data-detail-stack>—</strong></li>',
          '  <li><span>Compose project</span><strong>matrixly-observability</strong></li>',
          '  <li><span>Path</span><strong>infra/observability/</strong></li>',
          '</ul>',
          '<div class="obs-card-links">',
          '  <button type="button" class="btn ghost btn-sm" data-obs-toggle-compose>View compose</button>',
          '  <button type="button" class="btn ghost btn-sm" data-obs-restart>Restart cmds</button>',
          '</div>'
        ].join("")),

        // Crawl4AI
        cardHtml("Crawl4AI", "crawl4ai", [
          '<p class="obs-card-desc">Self-hosted crawler on port <strong>11235</strong> for agentic SEO &amp; content pipelines.</p>',
          '<ul class="obs-kv">',
          '  <li><span>Connection</span><strong data-detail-crawl4ai>—</strong></li>',
          '  <li><span>Active browsers</span><strong data-metric-browsers>—</strong></li>',
          '  <li><span>Request rate</span><strong data-metric-rate>—</strong></li>',
          '  <li><span>Success rate</span><strong data-metric-success>—</strong></li>',
          '</ul>',
          '<div class="obs-card-links">',
          '  <a class="btn ghost btn-sm" data-link-playground href="#" target="_blank" rel="noopener">Playground</a>',
          '  <a class="btn ghost btn-sm" data-link-monitor href="#" target="_blank" rel="noopener">/monitor</a>',
          '  <a class="btn ghost btn-sm" data-link-crawl4ai href="#" target="_blank" rel="noopener">Root</a>',
          '</div>'
        ].join("")),

        // Playwright
        cardHtml("Playwright", "playwright", [
          '<p class="obs-card-desc">Browser engine pool used by Crawl4AI (Chromium). Health tracks the parent crawler.</p>',
          '<ul class="obs-kv">',
          '  <li><span>Pool health</span><strong data-detail-playwright>—</strong></li>',
          '  <li><span>Version</span><strong data-metric-pw-ver>—</strong></li>',
          '  <li><span>Memory (process)</span><strong data-metric-mem>—</strong></li>',
          '</ul>',
          '<p class="tip">Resource spikes usually mean too many concurrent browsers — lower <code>MAX_CONCURRENT_BROWSERS</code>.</p>'
        ].join("")),

        // Prometheus
        cardHtml("Prometheus", "prometheus", [
          '<p class="obs-card-desc">Metrics scrape &amp; store for crawl success, latency, and host signals.</p>',
          '<ul class="obs-kv">',
          '  <li><span>Status</span><strong data-detail-prometheus>—</strong></li>',
          '  <li><span>P95 latency</span><strong data-metric-p95>—</strong></li>',
          '  <li><span>Error rate</span><strong data-metric-errors>—</strong></li>',
          '</ul>',
          '<div class="obs-targets-wrap">',
          '  <table class="obs-mini-table"><thead><tr><th>Job</th><th>Health</th><th>Last error</th></tr></thead>',
          '  <tbody data-prom-targets></tbody></table>',
          '</div>',
          '<div class="obs-card-links">',
          '  <a class="btn ghost btn-sm" data-link-prometheus href="#" target="_blank" rel="noopener">Open Prometheus</a>',
          '  <a class="btn ghost btn-sm" data-link-explore-metrics href="#" target="_blank" rel="noopener">Explore metrics</a>',
          '</div>'
        ].join("")),

        // Grafana
        cardHtml("Grafana", "grafana", [
          '<p class="obs-card-desc">Dashboards &amp; Explore. Pre-provisioned: <em>Matrixly Crawl4AI Monitoring</em>.</p>',
          '<ul class="obs-kv">',
          '  <li><span>Admin status</span><strong data-detail-grafana>—</strong></li>',
          '  <li><span>Dashboard UID</span><strong>matrixly-crawl4ai</strong></li>',
          '</ul>',
          '<div class="obs-card-links">',
          '  <a class="btn btn-sm" data-link-grafana href="#" target="_blank" rel="noopener">Open Dashboard</a>',
          '  <a class="btn ghost btn-sm" data-link-grafana-home href="#" target="_blank" rel="noopener">Grafana home</a>',
          '</div>'
        ].join("")),

        // Loki
        cardHtml("Loki", "loki", [
          '<p class="obs-card-desc">Log aggregation for Crawl4AI and stack containers (via Promtail).</p>',
          '<ul class="obs-kv">',
          '  <li><span>Status</span><strong data-detail-loki>—</strong></li>',
          '  <li><span>Recent ERROR count (1h)</span><strong data-loki-errors>—</strong></li>',
          '</ul>',
          '<p class="tip">LogQL: <code>{container=~".*crawl4ai.*"} |= "ERROR"</code></p>',
          '<div class="obs-card-links">',
          '  <a class="btn ghost btn-sm" data-link-explore-logs href="#" target="_blank" rel="noopener">Grafana Explore (Loki)</a>',
          '  <a class="btn ghost btn-sm" data-link-loki href="#" target="_blank" rel="noopener">Loki ready</a>',
          '</div>'
        ].join("")),
        "  </div>",

        // Grafana Dashboard sub-section
        '  <div class="obs-grafana-panel">',
        '    <div class="obs-grafana-head">',
        '      <div>',
        '        <h3>Grafana Dashboard</h3>',
        '        <p class="obs-muted">Matrixly Crawl4AI Monitoring — switch between Metrics (Prometheus), Logs (Loki), and Combined.</p>',
        '      </div>',
        '      <div class="obs-view-toggle" role="tablist">',
        '        <button type="button" class="obs-view-btn" data-gview="metrics" role="tab">Metrics</button>',
        '        <button type="button" class="obs-view-btn" data-gview="logs" role="tab">Logs</button>',
        '        <button type="button" class="obs-view-btn active" data-gview="combined" role="tab">Combined</button>',
        '      </div>',
        '    </div>',
        '    <div class="obs-metric-strip">',
        '      <div class="obs-m"><span class="l">Request Rate</span><span class="v" data-metric-rate>—</span></div>',
        '      <div class="obs-m"><span class="l">Success Rate</span><span class="v" data-metric-success>—</span></div>',
        '      <div class="obs-m"><span class="l">P95 Latency</span><span class="v" data-metric-p95>—</span></div>',
        '      <div class="obs-m"><span class="l">Memory</span><span class="v" data-metric-mem>—</span></div>',
        '      <div class="obs-m"><span class="l">Browser Pool</span><span class="v" data-metric-browsers>—</span></div>',
        '      <div class="obs-m"><span class="l">Error Rate</span><span class="v" data-metric-errors>—</span></div>',
        '      <div class="obs-m"><span class="l">Loki ERRORs (1h)</span><span class="v" data-loki-errors>—</span></div>',
        '    </div>',
        '    <div class="obs-iframe-wrap" data-grafana-placeholder>',
        '      <p class="obs-iframe-hint" data-gview-hint>Combined dashboard: Matrixly Crawl4AI Monitoring (metrics + error logs).</p>',
        '      <a class="btn" data-open-grafana-view href="http://127.0.0.1:3000" target="_blank" rel="noopener">Open Dashboard</a>',
        '      <p class="tip">Live iframe embed is attempted below; many Grafana installs set <code>X-Frame-Options</code> and block embedding — use the button if the frame is blank.</p>',
        '      <iframe class="obs-iframe" data-grafana-iframe title="Matrixly Grafana Crawl4AI Dashboard" loading="lazy" referrerpolicy="no-referrer"></iframe>',
        '    </div>',
        '  </div>',

        // Endpoint config
        '  <details class="obs-endpoints">',
        '    <summary>Endpoint configuration</summary>',
        '    <form data-obs-endpoints class="obs-endpoint-form">',
        '      <label>Crawl4AI base URL <input name="crawl4ai" type="url" spellcheck="false" /></label>',
        '      <label>Prometheus base URL <input name="prometheus" type="url" spellcheck="false" /></label>',
        '      <label>Grafana base URL <input name="grafana" type="url" spellcheck="false" /></label>',
        '      <label>Loki base URL <input name="loki" type="url" spellcheck="false" /></label>',
        '      <button type="submit" class="btn">Save &amp; re-probe</button>',
        '    </form>',
        '    <p class="tip">Stored in <code>localStorage</code> (<code>matrixly-obs-endpoints</code>). For production admin UIs behind a reverse proxy, point these at public hostnames or a same-origin <code>/api/obs</code> control plane.</p>',
        '  </details>',
        "</div>"
      ].join("\n");
    }

    function cardHtml(title, key, body) {
      return [
        '<article class="obs-card panel" data-card="' + key + '">',
        '  <h2><span>' + title + '</span> <span class="obs-badge unknown" data-status-' + key + '>…</span></h2>',
        '  <div class="body">' + body + "</div>",
        "</article>"
      ].join("");
    }

    refresh();
    if (autoRefreshMs > 0) {
      refreshTimer = setInterval(refresh, autoRefreshMs);
    }

    return {
      refresh: refresh,
      unmount: function () {
        if (refreshTimer) clearInterval(refreshTimer);
        root.innerHTML = "";
      },
      getSnapshot: function () { return lastSnap; }
    };
  }

  // Public API (React-like surface for future ports)
  global.MatrixlyObs = {
    DEFAULT_ENDPOINTS: DEFAULT_ENDPOINTS,
    DOCKER_COMPOSE_YML: DOCKER_COMPOSE_YML,
    RESTART_COMMANDS: RESTART_COMMANDS,
    getEndpoints: getEndpoints,
    setEndpoints: setEndpoints,
    fetchSnapshot: fetchSnapshot,
    probe: probe,
    grafanaUrls: grafanaUrls,
    crawl4aiUrls: crawl4aiUrls,
    copyText: copyText,
    mount: mount,
    formatBytes: formatBytes
  };
})(typeof window !== "undefined" ? window : globalThis);

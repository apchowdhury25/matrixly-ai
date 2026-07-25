/**
 * Matrixly ETF Portfolio Analyzer embed.
 */
(function () {
  var s = document.currentScript;
  if (!s) return;
  var api = (s.getAttribute("data-api") || "").replace(/\/$/, "");
  if (!api) return;

  var btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "ETF Analyzer";
  btn.style.cssText =
    "position:fixed;bottom:20px;right:20px;z-index:99999;background:#117ACA;color:#fff;" +
    "border:0;border-radius:999px;padding:12px 18px;font:700 14px Open Sans,system-ui,sans-serif;" +
    "box-shadow:0 8px 24px rgba(17,122,202,0.35);cursor:pointer;";

  var wrap = null;
  btn.addEventListener("click", function () {
    if (wrap) {
      wrap.style.display = wrap.style.display === "none" ? "block" : "none";
      return;
    }
    wrap = document.createElement("div");
    wrap.style.cssText =
      "position:fixed;bottom:72px;right:20px;z-index:99999;width:min(420px,95vw);height:min(640px,82vh);" +
      "border-radius:14px;overflow:hidden;border:1px solid #1e2a3a;box-shadow:0 16px 48px rgba(0,0,0,.35);";
    var iframe = document.createElement("iframe");
    iframe.title = "ETF Portfolio Analyzer";
    iframe.src = api + "/static/dashboard/index.html?api=" + encodeURIComponent(api);
    iframe.style.cssText = "width:100%;height:100%;border:0;background:#0b0f14;";
    wrap.appendChild(iframe);
    document.body.appendChild(wrap);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      document.body.appendChild(btn);
    });
  } else {
    document.body.appendChild(btn);
  }
})();

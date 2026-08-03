/**
 * Matrixly SEO-Bespoke embed widget
 * Usage:
 * <script src=".../static/widget/embed.js"
 *   data-api="http://localhost:8799"
 *   data-key="pk_live_..."
 *   async></script>
 */
(function () {
  var s = document.currentScript;
  if (!s) return;
  var api = (s.getAttribute("data-api") || "").replace(/\/$/, "");
  var key = s.getAttribute("data-key") || "";
  if (!api) return;

  var btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "SEO-Bespoke";
  btn.setAttribute(
    "style",
    "position:fixed;bottom:1.25rem;right:1.25rem;z-index:99999;" +
      "background:linear-gradient(145deg,#117aca,#3b9fe0);color:#fff;" +
      "border:0;border-radius:999px;padding:0.7rem 1.1rem;font-weight:700;" +
      "font-family:system-ui,sans-serif;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.35);"
  );
  btn.addEventListener("click", function () {
    var url = api + "/static/dashboard/index.html";
    if (key) url += "?widget_key=" + encodeURIComponent(key);
    window.open(url, "seo-bespoke", "width=1100,height=800");
  });
  document.body.appendChild(btn);
})();

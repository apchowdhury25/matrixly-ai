/**
 * Matrixly SEOForge launcher — opens embeddable dashboard
 * <script src="HOST/static/widget/embed.js" data-api="HOST" async></script>
 */
(function () {
  "use strict";
  var script = document.currentScript || document.getElementsByTagName("script")[document.getElementsByTagName("script").length - 1];
  var API = (script.getAttribute("data-api") || "").replace(/\/$/, "");
  if (!API) return;
  var btn = document.createElement("button");
  btn.textContent = "SEOForge";
  btn.setAttribute("aria-label", "Open SEOForge");
  btn.style.cssText = "position:fixed;right:20px;bottom:20px;z-index:2147483000;padding:12px 16px;border-radius:999px;border:1px solid rgba(59,159,224,.45);background:linear-gradient(145deg,#117aca,#3b9fe0);color:#fff;font:700 13px Open Sans,system-ui,sans-serif;cursor:pointer;box-shadow:0 12px 40px rgba(0,0,0,.45)";
  btn.onclick = function () {
    window.open(API + "/static/dashboard/index.html", "_blank", "noopener");
  };
  document.body.appendChild(btn);
})();

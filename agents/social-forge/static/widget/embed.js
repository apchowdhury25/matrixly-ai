/**
 * Matrixly SocialForge embed launcher.
 * <script src=".../embed.js" data-api="https://host" data-key="pk_live_..." async></script>
 */
(function () {
  var s = document.currentScript;
  if (!s) return;
  var api = (s.getAttribute("data-api") || "").replace(/\/$/, "");
  var key = s.getAttribute("data-key") || "";
  if (!api) return;

  var btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "SocialForge";
  btn.setAttribute("aria-label", "Open SocialForge");
  btn.style.cssText =
    "position:fixed;bottom:20px;right:20px;z-index:99999;background:#117ACA;color:#fff;" +
    "border:0;border-radius:999px;padding:12px 18px;font:700 14px Open Sans,system-ui,sans-serif;" +
    "box-shadow:0 8px 24px rgba(17,122,202,0.35);cursor:pointer;";

  var frameWrap = null;
  btn.addEventListener("click", function () {
    if (frameWrap) {
      frameWrap.style.display = frameWrap.style.display === "none" ? "block" : "none";
      return;
    }
    frameWrap = document.createElement("div");
    frameWrap.style.cssText =
      "position:fixed;bottom:72px;right:20px;z-index:99999;width:min(420px,94vw);height:min(640px,80vh);" +
      "border-radius:14px;overflow:hidden;box-shadow:0 16px 48px rgba(0,0,0,0.35);border:1px solid #1e2a3a;";
    var iframe = document.createElement("iframe");
    iframe.title = "SocialForge";
    iframe.src = api + "/static/calendar/index.html?api=" + encodeURIComponent(api);
    iframe.style.cssText = "width:100%;height:100%;border:0;background:#0b0f14;";
    frameWrap.appendChild(iframe);
    document.body.appendChild(frameWrap);
    if (key) {
      try {
        iframe.addEventListener("load", function () {
          /* keys entered in UI / localStorage */
        });
      } catch (e) {}
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.body.appendChild(btn);
  });
  if (document.readyState !== "loading") document.body.appendChild(btn);
})();

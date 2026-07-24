/**
 * Matrixly DocForge embed launcher.
 */
(function () {
  var s = document.currentScript;
  if (!s) return;
  var api = (s.getAttribute("data-api") || "").replace(/\/$/, "");
  if (!api) return;

  var btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "DocForge";
  btn.setAttribute("aria-label", "Open DocForge");
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
      "position:fixed;bottom:72px;right:20px;z-index:99999;width:min(460px,94vw);height:min(700px,84vh);" +
      "border-radius:14px;overflow:hidden;box-shadow:0 16px 48px rgba(0,0,0,0.35);border:1px solid #1e2a3a;";
    var iframe = document.createElement("iframe");
    iframe.title = "DocForge";
    iframe.src = api + "/static/workspace/index.html?api=" + encodeURIComponent(api);
    iframe.style.cssText = "width:100%;height:100%;border:0;background:#0b0f14;";
    frameWrap.appendChild(iframe);
    document.body.appendChild(frameWrap);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      document.body.appendChild(btn);
    });
  } else {
    document.body.appendChild(btn);
  }
})();

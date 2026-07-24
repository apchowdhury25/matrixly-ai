/**
 * Matrixly SupportForge — drop-in chat widget
 *
 * <script src="https://HOST/static/widget/embed.js"
 *   data-api="https://HOST"
 *   data-key="pk_live_..."
 *   data-title="Support"
 *   async></script>
 */
(function () {
  "use strict";

  var script = document.currentScript;
  if (!script) {
    var scripts = document.getElementsByTagName("script");
    script = scripts[scripts.length - 1];
  }

  var API = (script.getAttribute("data-api") || "").replace(/\/$/, "");
  var KEY = script.getAttribute("data-key") || "";
  var TITLE = script.getAttribute("data-title") || "SupportForge";
  var CSS = script.getAttribute("data-css") || API + "/static/widget/widget.css";

  if (!API || !KEY) {
    console.warn("[SupportForge] data-api and data-key are required");
    return;
  }

  function loadCss(href) {
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function mount() {
    loadCss(CSS);

    var root = el("div");
    root.id = "matrixly-sf-root";
    document.body.appendChild(root);

    var launcher = el("button", "sf-launcher");
    launcher.setAttribute("aria-label", "Open support chat");
    launcher.innerHTML =
      '<svg viewBox="0 0 24 24"><path d="M21 12a8.5 8.5 0 0 1-8.5 8.5c-1.3 0-2.5-.3-3.6-.8L3 21l1.4-5.5A8.4 8.4 0 0 1 3.5 12 8.5 8.5 0 1 1 21 12z"/></svg>';
    root.appendChild(launcher);

    var panel = el("div", "sf-panel");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", TITLE);

    var header = el("div", "sf-header");
    var brand = el("div", "sf-brand");
    brand.appendChild(el("strong", null, TITLE));
    brand.appendChild(el("span", null, "Matrixly · AI Support"));
    header.appendChild(brand);
    var actions = el("div", "sf-header-actions");
    var closeBtn = el("button", "sf-icon-btn", "×");
    closeBtn.setAttribute("aria-label", "Close");
    actions.appendChild(closeBtn);
    header.appendChild(actions);
    panel.appendChild(header);

    var messages = el("div", "sf-messages");
    panel.appendChild(messages);

    var footer = el("div", "sf-footer");
    var humanBtn = el("button", "sf-human", "Talk to a human");
    footer.appendChild(humanBtn);
    var row = el("div", "sf-input-row");
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Type your message…";
    input.setAttribute("aria-label", "Message");
    var send = el("button", null, "Send");
    row.appendChild(input);
    row.appendChild(send);
    footer.appendChild(row);
    var err = el("div", "sf-error");
    footer.appendChild(err);
    var powered = el("div", "sf-powered");
    powered.innerHTML = 'Powered by <a href="https://matrixbazaar.com" target="_blank" rel="noopener">Matrixly</a>';
    footer.appendChild(powered);
    panel.appendChild(footer);
    root.appendChild(panel);

    var state = {
      open: false,
      sessionId: null,
      busy: false,
    };

    function setOpen(v) {
      state.open = v;
      if (v) panel.classList.add("open");
      else panel.classList.remove("open");
      if (v && !state.sessionId) startSession();
    }

    launcher.addEventListener("click", function () {
      setOpen(!state.open);
    });
    closeBtn.addEventListener("click", function () {
      setOpen(false);
    });

    function addMsg(role, text, meta) {
      var m = el("div", "sf-msg " + role, text);
      messages.appendChild(m);
      if (meta) {
        var metaEl = el("div", "sf-meta");
        if (meta.confidence != null) {
          var badge = el(
            "span",
            "sf-badge" + (meta.requires_human ? " warn" : ""),
            "confidence " + Math.round(meta.confidence * 100) + "%"
          );
          metaEl.appendChild(badge);
        }
        if (meta.requires_human) {
          metaEl.appendChild(el("span", null, "human review"));
        }
        messages.appendChild(metaEl);
      }
      messages.scrollTop = messages.scrollHeight;
    }

    function setBusy(v) {
      state.busy = v;
      send.disabled = v;
      input.disabled = v;
    }

    function api(path, body) {
      return fetch(API + path, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Widget-Key": KEY,
        },
        body: JSON.stringify(body || {}),
      }).then(function (r) {
        if (!r.ok) {
          return r.json().catch(function () {
            return {};
          }).then(function (j) {
            throw new Error(j.detail || r.statusText || "Request failed");
          });
        }
        return r.json();
      });
    }

    function startSession() {
      setBusy(true);
      err.textContent = "";
      api("/v1/chat/session", {})
        .then(function (data) {
          state.sessionId = data.session_id;
          if (data.welcome) addMsg("bot", data.welcome);
        })
        .catch(function (e) {
          err.textContent = e.message || "Could not start chat";
        })
        .finally(function () {
          setBusy(false);
        });
    }

    function sendMessage(text) {
      if (!text || state.busy) return;
      addMsg("user", text);
      input.value = "";
      setBusy(true);
      err.textContent = "";
      var typing = el("div", "sf-typing", "SupportForge is typing…");
      messages.appendChild(typing);
      messages.scrollTop = messages.scrollHeight;

      api("/v1/chat", {
        session_id: state.sessionId,
        message: text,
        channel: "chat",
      })
        .then(function (data) {
          if (data.session_id) state.sessionId = data.session_id;
          typing.remove();
          addMsg("bot", data.reply, {
            confidence: data.confidence,
            requires_human: data.requires_human,
          });
        })
        .catch(function (e) {
          typing.remove();
          err.textContent = e.message || "Send failed";
        })
        .finally(function () {
          setBusy(false);
          input.focus();
        });
    }

    send.addEventListener("click", function () {
      sendMessage(input.value.trim());
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        sendMessage(input.value.trim());
      }
    });
    humanBtn.addEventListener("click", function () {
      sendMessage("I would like to speak with a human agent please.");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();

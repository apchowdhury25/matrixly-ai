/**
 * Matrixly BookWise — drop-in booking widget
 *
 * <script src="https://HOST/static/widget/embed.js"
 *   data-api="https://HOST"
 *   data-key="pk_live_..."
 *   data-title="Book with us"
 *   async></script>
 */
(function () {
  "use strict";
  var script = document.currentScript || document.getElementsByTagName("script")[document.getElementsByTagName("script").length - 1];
  var API = (script.getAttribute("data-api") || "").replace(/\/$/, "");
  var KEY = script.getAttribute("data-key") || "";
  var TITLE = script.getAttribute("data-title") || "BookWise";
  var CSS = script.getAttribute("data-css") || API + "/static/widget/widget.css";
  if (!API || !KEY) {
    console.warn("[BookWise] data-api and data-key are required");
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
    root.id = "matrixly-bw-root";
    document.body.appendChild(root);

    var launcher = el("button", "bw-launcher");
    launcher.setAttribute("aria-label", "Open booking chat");
    launcher.innerHTML = '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><circle cx="8.5" cy="15" r="1" fill="#fff" stroke="none"/><circle cx="12" cy="15" r="1" fill="#fff" stroke="none"/><circle cx="15.5" cy="15" r="1" fill="#fff" stroke="none"/></svg>';
    root.appendChild(launcher);

    var panel = el("div", "bw-panel");
    panel.setAttribute("role", "dialog");
    var header = el("div", "bw-header");
    var brand = el("div", "bw-brand");
    brand.appendChild(el("strong", null, TITLE));
    brand.appendChild(el("span", null, "Matrixly · BookWise"));
    header.appendChild(brand);
    var closeBtn = el("button", "bw-icon-btn", "×");
    header.appendChild(closeBtn);
    panel.appendChild(header);

    var messages = el("div", "bw-messages");
    panel.appendChild(messages);

    var footer = el("div", "bw-footer");
    var quick = el("div", "bw-quick");
    [["Availability", "What times are available this week?"], ["Book consult", "I'd like to book a consultation"], ["Reschedule", "I need to reschedule my appointment"], ["Cancel", "I need to cancel my appointment"]].forEach(function (pair) {
      var chip = el("button", "bw-chip", pair[0]);
      chip.onclick = function () { sendMessage(pair[1]); };
      quick.appendChild(chip);
    });
    footer.appendChild(quick);
    var row = el("div", "bw-input-row");
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Ask about times or book…";
    var send = el("button", null, "Send");
    row.appendChild(input);
    row.appendChild(send);
    footer.appendChild(row);
    var err = el("div", "bw-error");
    footer.appendChild(err);
    var powered = el("div", "bw-powered");
    powered.innerHTML = 'Powered by <a href="https://matrixly.world" target="_blank" rel="noopener">Matrixly</a>';
    footer.appendChild(powered);
    panel.appendChild(footer);
    root.appendChild(panel);

    var state = { open: false, sessionId: null, busy: false };

    function setOpen(v) {
      state.open = v;
      panel.classList.toggle("open", v);
      if (v && !state.sessionId) startSession();
    }
    launcher.onclick = function () { setOpen(!state.open); };
    closeBtn.onclick = function () { setOpen(false); };

    function addMsg(role, text) {
      messages.appendChild(el("div", "bw-msg " + role, text));
      messages.scrollTop = messages.scrollHeight;
    }

    function addSlots(proposals) {
      if (!proposals || !proposals.length) return;
      var wrap = el("div", "bw-slots");
      proposals.forEach(function (p, i) {
        var btn = el("button", "bw-slot", (i + 1) + ". " + p.label);
        btn.onclick = function () {
          sendMessage("Book slot " + (i + 1) + " please. " + p.label, p.start_iso);
        };
        wrap.appendChild(btn);
      });
      messages.appendChild(wrap);
      messages.scrollTop = messages.scrollHeight;
    }

    function api(path, body) {
      return fetch(API + path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Widget-Key": KEY },
        body: JSON.stringify(body || {}),
      }).then(function (r) {
        if (!r.ok) {
          return r.json().catch(function () { return {}; }).then(function (j) {
            throw new Error(j.detail || r.statusText || "Request failed");
          });
        }
        return r.json();
      });
    }

    function startSession() {
      state.busy = true;
      send.disabled = true;
      api("/v1/chat/session", {}).then(function (data) {
        state.sessionId = data.session_id;
        if (data.welcome) addMsg("bot", data.welcome);
      }).catch(function (e) {
        err.textContent = e.message || "Could not start chat";
      }).finally(function () {
        state.busy = false;
        send.disabled = false;
      });
    }

    function sendMessage(text, selectedSlot) {
      if (!text || state.busy) return;
      addMsg("user", text);
      input.value = "";
      state.busy = true;
      send.disabled = true;
      err.textContent = "";
      var typing = el("div", "bw-typing", "BookWise is checking calendars…");
      messages.appendChild(typing);

      var payload = { session_id: state.sessionId, message: text, channel: "chat" };
      if (selectedSlot) payload.selected_slot = selectedSlot;

      api("/v1/chat", payload).then(function (data) {
        if (data.session_id) state.sessionId = data.session_id;
        typing.remove();
        addMsg("bot", data.reply);
        addSlots(data.proposals);
      }).catch(function (e) {
        typing.remove();
        err.textContent = e.message || "Send failed";
      }).finally(function () {
        state.busy = false;
        send.disabled = false;
        input.focus();
      });
    }

    send.onclick = function () { sendMessage(input.value.trim()); };
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        sendMessage(input.value.trim());
      }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();

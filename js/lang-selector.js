/**
 * Matrixly language selector
 * Globe trigger (no country flags / codes — Windows renders 🇬🇧 as "GB").
 * US English default; native names only in the menu.
 * Injects own CSS so every page gets a consistent control.
 */
(function () {
  const LANGS = [
    { code: "en", name: "English" },
    { code: "es", name: "Español" },
    { code: "fr", name: "Français" },
    { code: "ar", name: "العربية" },
    { code: "bn", name: "বাংলা" },
    { code: "de", name: "Deutsch" },
    { code: "ms", name: "Bahasa Melayu" },
  ];

  const GLOBE_SVG =
    '<svg class="lang-selector-globe" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="10"/>' +
    '<path d="M2 12h20"/>' +
    '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>' +
    "</svg>";

  const CHEVRON_SVG =
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';

  function ensureStyles() {
    if (document.getElementById("matrixly-lang-selector-css")) return;
    var style = document.createElement("style");
    style.id = "matrixly-lang-selector-css";
    style.textContent =
      ".lang-selector{position:relative;flex-shrink:0}" +
      ".lang-selector-btn{display:inline-flex;align-items:center;gap:.4rem;min-height:40px;height:40px;padding:0 .65rem;border-radius:.5rem;" +
      "background:var(--toggle-bg,var(--bg-muted,#F0F4F8));border:1.5px solid var(--toggle-border,var(--border,#D0D7DE));" +
      "color:var(--ink,#211E1E);cursor:pointer;font-size:.8125rem;font-weight:700;line-height:1;" +
      "transition:background .2s ease,border-color .2s ease,transform .15s ease}" +
      ".lang-selector-btn:hover{border-color:var(--brand-blue,#117ACA);background:var(--brand-blue-soft,color-mix(in srgb,var(--brand-blue,#117ACA) 10%,transparent));transform:translateY(-1px)}" +
      ".lang-selector-btn:focus-visible{outline:2px solid var(--brand-blue,#117ACA);outline-offset:2px}" +
      ".lang-selector-globe{width:1.15rem;height:1.15rem;display:block;color:var(--brand-blue,#117ACA);flex-shrink:0}" +
      ".lang-selector-label{max-width:7.5rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--brand-blue,#117ACA)}" +
      ".lang-selector-chevron{display:inline-flex;color:var(--soft,#5C6670);transition:transform .15s ease}" +
      ".lang-selector.is-open .lang-selector-chevron{transform:rotate(180deg)}" +
      ".lang-selector-menu{position:absolute;top:calc(100% + 6px);right:0;min-width:13rem;margin:0;padding:.35rem;list-style:none;" +
      "border-radius:.75rem;border:1px solid var(--border,#D0D7DE);background:var(--card,#fff);" +
      "box-shadow:0 8px 28px rgba(33,30,30,.14);z-index:80}" +
      "html.rtl .lang-selector-menu{right:auto;left:0}" +
      ".lang-selector-option{display:flex;align-items:center;gap:.5rem;width:100%;padding:.55rem .65rem;border-radius:.5rem;" +
      "cursor:pointer;color:var(--ink,#211E1E);font-size:.875rem;font-weight:500;outline:none}" +
      ".lang-selector-option:hover,.lang-selector-option:focus-visible{background:var(--brand-blue-soft,color-mix(in srgb,var(--brand-blue,#117ACA) 10%,transparent))}" +
      ".lang-selector-option.is-selected{font-weight:700;background:color-mix(in srgb,var(--brand-blue,#117ACA) 12%,transparent)}" +
      ".lang-selector-option-name{flex:1;text-align:start}" +
      ".lang-selector-check{color:var(--brand-blue,#117ACA);font-weight:700;opacity:0;width:.9rem}" +
      ".lang-selector-option.is-selected .lang-selector-check{opacity:1}" +
      "#navbar .nav-actions,#navbar .nav-mobile,.nav-actions,.nav-mobile{gap:.5rem}";
    document.head.appendChild(style);
  }

  function currentCode() {
    if (window.MatrixlyI18n && typeof window.MatrixlyI18n.getLanguage === "function") {
      return window.MatrixlyI18n.getLanguage() || "en";
    }
    try {
      return localStorage.getItem("matrixly-lang") || "en";
    } catch (_) {
      return "en";
    }
  }

  function langMeta(code) {
    return LANGS.find(function (l) {
      return l.code === code;
    }) || LANGS[0];
  }

  function selectLabel() {
    if (window.MatrixlyI18n && typeof window.MatrixlyI18n.t === "function") {
      var t = window.MatrixlyI18n.t("common.selectLanguage");
      if (t && t !== "common.selectLanguage") return t;
    }
    return "Select language";
  }

  function buildSelector() {
    var wrap = document.createElement("div");
    wrap.className = "lang-selector";
    wrap.dataset.langSelector = "true";

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lang-selector-btn";
    btn.setAttribute("aria-haspopup", "listbox");
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-label", selectLabel());

    var globe = document.createElement("span");
    globe.className = "lang-selector-globe-wrap";
    globe.setAttribute("aria-hidden", "true");
    globe.innerHTML = GLOBE_SVG;

    var labelSpan = document.createElement("span");
    labelSpan.className = "lang-selector-label";

    var chevron = document.createElement("span");
    chevron.className = "lang-selector-chevron";
    chevron.setAttribute("aria-hidden", "true");
    chevron.innerHTML = CHEVRON_SVG;

    btn.appendChild(globe);
    btn.appendChild(labelSpan);
    btn.appendChild(chevron);

    var list = document.createElement("ul");
    list.className = "lang-selector-menu";
    list.setAttribute("role", "listbox");
    list.setAttribute("tabindex", "-1");
    list.hidden = true;

    LANGS.forEach(function (lang) {
      var li = document.createElement("li");
      li.setAttribute("role", "option");
      li.dataset.code = lang.code;
      li.className = "lang-selector-option";
      li.setAttribute("tabindex", "-1");
      li.innerHTML =
        '<span class="lang-selector-option-name">' +
        lang.name +
        '</span><span class="lang-selector-check" aria-hidden="true">✓</span>';
      list.appendChild(li);
    });

    wrap.appendChild(btn);
    wrap.appendChild(list);

    function syncUI() {
      var code = currentCode();
      var meta = langMeta(code);
      labelSpan.textContent = meta.name;
      btn.setAttribute("aria-label", selectLabel() + ": " + meta.name);
      list.querySelectorAll(".lang-selector-option").forEach(function (opt) {
        var selected = opt.dataset.code === code;
        opt.setAttribute("aria-selected", selected ? "true" : "false");
        opt.classList.toggle("is-selected", selected);
      });
    }

    function open() {
      list.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      wrap.classList.add("is-open");
      var selected =
        list.querySelector('.lang-selector-option[aria-selected="true"]') || list.firstElementChild;
      if (selected) selected.focus();
    }

    function close() {
      list.hidden = true;
      btn.setAttribute("aria-expanded", "false");
      wrap.classList.remove("is-open");
    }

    function toggle() {
      if (list.hidden) open();
      else close();
    }

    async function choose(code) {
      close();
      if (window.MatrixlyI18n && typeof window.MatrixlyI18n.setLanguage === "function") {
        await window.MatrixlyI18n.setLanguage(code);
      } else {
        try {
          localStorage.setItem("matrixly-lang", code);
        } catch (_) {}
        location.reload();
      }
      syncUI();
      document.querySelectorAll("[data-lang-selector]").forEach(function (el) {
        if (el !== wrap && el._langSync) el._langSync();
      });
    }

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggle();
    });

    btn.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        open();
      } else if (e.key === "Escape") {
        close();
      }
    });

    list.addEventListener("click", function (e) {
      var opt = e.target.closest(".lang-selector-option");
      if (opt && opt.dataset.code) {
        e.preventDefault();
        choose(opt.dataset.code);
      }
    });

    list.addEventListener("keydown", function (e) {
      var options = Array.from(list.querySelectorAll(".lang-selector-option"));
      var idx = options.indexOf(document.activeElement);
      if (e.key === "Escape") {
        e.preventDefault();
        close();
        btn.focus();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        (options[Math.min(options.length - 1, Math.max(0, idx) + 1)] || options[0]).focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        (options[Math.max(0, idx - 1)] || options[0]).focus();
      } else if (e.key === "Home") {
        e.preventDefault();
        options[0].focus();
      } else if (e.key === "End") {
        e.preventDefault();
        options[options.length - 1].focus();
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        var active = document.activeElement;
        if (active && active.dataset.code) choose(active.dataset.code);
      }
    });

    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) close();
    });

    wrap._langSync = syncUI;
    syncUI();
    return wrap;
  }

  function insertSelectors() {
    document.querySelectorAll("[data-lang-selector]").forEach(function (el) {
      el.remove();
    });

    var inserted = false;

    document.querySelectorAll(".nav-actions .theme-toggle, .nav-actions [data-theme-toggle]").forEach(function (themeBtn) {
      themeBtn.parentNode.insertBefore(buildSelector(), themeBtn);
      inserted = true;
    });

    document.querySelectorAll(".nav-mobile .theme-toggle, .nav-mobile [data-theme-toggle]").forEach(function (themeBtn) {
      themeBtn.parentNode.insertBefore(buildSelector(), themeBtn);
      inserted = true;
    });

    // Pages with theme toggle but outside .nav-actions / .nav-mobile
    if (!inserted) {
      document.querySelectorAll("[data-theme-toggle]").forEach(function (themeBtn) {
        if (themeBtn.closest("[data-lang-selector]")) return;
        themeBtn.parentNode.insertBefore(buildSelector(), themeBtn);
        inserted = true;
      });
    }

    // Simple agent/product pages: place in header nav cluster
    if (!inserted) {
      var headerNav =
        document.querySelector("header nav") ||
        document.querySelector("header .flex.items-center.justify-between") ||
        document.querySelector("header");
      if (headerNav) {
        var cluster =
          headerNav.querySelector(".flex.items-center.gap-4") ||
          headerNav.querySelector(".flex.items-center.justify-between") ||
          headerNav;
        var sel = buildSelector();
        sel.style.marginInlineStart = "0.5rem";
        // Prefer inserting before last child CTA / marketplace link
        var lastBtn = cluster.querySelector("a.btn-primary, a.btn-secondary, .btn-primary, .btn-secondary");
        if (lastBtn && lastBtn.parentNode === cluster) {
          cluster.insertBefore(sel, lastBtn);
        } else {
          cluster.appendChild(sel);
        }
      }
    }
  }

  function init() {
    ensureStyles();
    insertSelectors();
    window.addEventListener("matrixly:langchange", function () {
      document.querySelectorAll("[data-lang-selector]").forEach(function (el) {
        if (el._langSync) el._langSync();
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

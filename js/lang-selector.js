/**
 * Matrixly language selector
 * Places accessible dropdown next to theme toggles; calls MatrixlyI18n.setLanguage.
 */
(function () {
  const LANGS = [
    { code: "en", flag: "🇬🇧", name: "English", short: "EN" },
    { code: "es", flag: "🇪🇸", name: "Español", short: "ES" },
    { code: "fr", flag: "🇫🇷", name: "Français", short: "FR" },
    { code: "ar", flag: "🇸🇦", name: "العربية", short: "AR" },
    { code: "bn", flag: "🇧🇩", name: "বাংলা", short: "BN" },
    { code: "de", flag: "🇩🇪", name: "Deutsch", short: "DE" },
    { code: "ms", flag: "🇲🇾", name: "Bahasa Melayu", short: "MS" },
  ];

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
    return LANGS.find((l) => l.code === code) || LANGS[0];
  }

  function selectLabel() {
    if (window.MatrixlyI18n && typeof window.MatrixlyI18n.t === "function") {
      const t = window.MatrixlyI18n.t("common.selectLanguage");
      if (t && t !== "common.selectLanguage") return t;
    }
    return "Select language";
  }

  function buildSelector() {
    const wrap = document.createElement("div");
    wrap.className = "lang-selector";
    wrap.dataset.langSelector = "true";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lang-selector-btn";
    btn.setAttribute("aria-haspopup", "listbox");
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-label", selectLabel());

    const flagSpan = document.createElement("span");
    flagSpan.className = "lang-selector-flag";
    flagSpan.setAttribute("aria-hidden", "true");

    const codeSpan = document.createElement("span");
    codeSpan.className = "lang-selector-code";

    const chevron = document.createElement("span");
    chevron.className = "lang-selector-chevron";
    chevron.setAttribute("aria-hidden", "true");
    chevron.innerHTML =
      '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>';

    btn.appendChild(flagSpan);
    btn.appendChild(codeSpan);
    btn.appendChild(chevron);

    const list = document.createElement("ul");
    list.className = "lang-selector-menu";
    list.setAttribute("role", "listbox");
    list.setAttribute("tabindex", "-1");
    list.hidden = true;

    LANGS.forEach((lang) => {
      const li = document.createElement("li");
      li.setAttribute("role", "option");
      li.dataset.code = lang.code;
      li.className = "lang-selector-option";
      li.setAttribute("tabindex", "-1");
      li.innerHTML =
        '<span class="lang-selector-option-flag" aria-hidden="true">' +
        lang.flag +
        '</span><span class="lang-selector-option-name">' +
        lang.name +
        '</span><span class="lang-selector-option-short">' +
        lang.short +
        '</span><span class="lang-selector-check" aria-hidden="true">✓</span>';
      list.appendChild(li);
    });

    wrap.appendChild(btn);
    wrap.appendChild(list);

    function syncUI() {
      const code = currentCode();
      const meta = langMeta(code);
      flagSpan.textContent = meta.flag;
      codeSpan.textContent = meta.short;
      btn.setAttribute("aria-label", selectLabel() + ": " + meta.name);
      list.querySelectorAll(".lang-selector-option").forEach((opt) => {
        const selected = opt.dataset.code === code;
        opt.setAttribute("aria-selected", selected ? "true" : "false");
        opt.classList.toggle("is-selected", selected);
      });
    }

    function open() {
      list.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      wrap.classList.add("is-open");
      const selected = list.querySelector('.lang-selector-option[aria-selected="true"]') || list.firstElementChild;
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
      document.querySelectorAll("[data-lang-selector]").forEach((el) => {
        if (el !== wrap && el._langSync) el._langSync();
      });
    }

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggle();
    });

    btn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        open();
      } else if (e.key === "Escape") {
        close();
      }
    });

    list.addEventListener("click", (e) => {
      const opt = e.target.closest(".lang-selector-option");
      if (opt && opt.dataset.code) {
        e.preventDefault();
        choose(opt.dataset.code);
      }
    });

    list.addEventListener("keydown", (e) => {
      const options = Array.from(list.querySelectorAll(".lang-selector-option"));
      const idx = options.indexOf(document.activeElement);
      if (e.key === "Escape") {
        e.preventDefault();
        close();
        btn.focus();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        const next = options[Math.min(options.length - 1, Math.max(0, idx) + 1)] || options[0];
        next.focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const prev = options[Math.max(0, idx - 1)] || options[0];
        prev.focus();
      } else if (e.key === "Home") {
        e.preventDefault();
        options[0].focus();
      } else if (e.key === "End") {
        e.preventDefault();
        options[options.length - 1].focus();
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        const active = document.activeElement;
        if (active && active.dataset.code) choose(active.dataset.code);
      }
    });

    document.addEventListener("click", (e) => {
      if (!wrap.contains(e.target)) close();
    });

    wrap._langSync = syncUI;
    syncUI();
    return wrap;
  }

  function insertSelectors() {
    document.querySelectorAll("[data-lang-selector]").forEach((el) => el.remove());

    // Desktop: immediately before theme-toggle inside .nav-actions
    document.querySelectorAll(".nav-actions .theme-toggle").forEach((themeBtn) => {
      const sel = buildSelector();
      themeBtn.parentNode.insertBefore(sel, themeBtn);
    });

    // Mobile: immediately before theme-toggle inside .nav-mobile
    document.querySelectorAll(".nav-mobile .theme-toggle").forEach((themeBtn) => {
      const sel = buildSelector();
      themeBtn.parentNode.insertBefore(sel, themeBtn);
    });
  }

  function init() {
    insertSelectors();
    window.addEventListener("matrixly:langchange", () => {
      document.querySelectorAll("[data-lang-selector]").forEach((el) => {
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

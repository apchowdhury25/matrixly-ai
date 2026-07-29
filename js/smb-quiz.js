/**
 * Matrixly — “Which agents for my business?” quiz
 * Multi-step recommendations for SMB starter packs.
 */
(function () {
  'use strict';

  var AGENTS = {
    'lead-qualifier': {
      name: 'Lead Qualifier',
      href: '/lead-qualifier',
      blurb: 'Scores inbound leads and drafts outreach so hot jobs don’t go cold.',
    },
    'email-assistant': {
      name: 'Email Assistant',
      href: '/email-assistant',
      blurb: 'Triages your inbox, drafts replies, and surfaces what needs you now.',
    },
    'shipping-assistant': {
      name: 'Shipping Assistant',
      href: '/shipping-assistant',
      blurb: 'Rate-shops carriers, tracks packages, and cuts “where’s my order?” tickets.',
    },
    'support-forge': {
      name: 'SupportForge',
      href: '/support-forge',
      blurb: 'Answers customers from your knowledge base and escalates only when needed.',
    },
    'crm-assistant': {
      name: 'CRM Assistant',
      href: '/crm-assistant',
      blurb: 'Keeps contacts and pipeline hygiene clean with approve-to-write controls.',
    },
    'book-wise': {
      name: 'BookWise',
      href: '/book-wise',
      blurb: 'Books appointments, sends confirmations, and reduces scheduling back-and-forth.',
    },
    'content-forge': {
      name: 'ContentForge',
      href: '/content-forge',
      blurb: 'Creates SEO pages and local content in your voice — review before publish.',
    },
    'meet-wise': {
      name: 'MeetWise',
      href: '/meet-wise',
      blurb: 'Turns meetings into summaries, actions, and CRM notes automatically.',
    },
    'social-forge': {
      name: 'SocialForge',
      href: '/social-forge',
      blurb: 'Plans posts and helps reply in brand voice so local social stays consistent.',
    },
    'invoice-forge': {
      name: 'InvoiceForge',
      href: '/invoice-forge',
      blurb: 'Extracts invoice data and helps chase AR without drowning in paperwork.',
    },
  };

  /** industry + drain → ordered agent keys */
  var PACKS = {
    hvac: {
      email: ['email-assistant', 'lead-qualifier', 'book-wise'],
      leads: ['lead-qualifier', 'email-assistant', 'content-forge'],
      shipping: ['email-assistant', 'lead-qualifier', 'book-wise'],
      support: ['support-forge', 'email-assistant', 'book-wise'],
      content: ['content-forge', 'lead-qualifier', 'social-forge'],
    },
    shopify: {
      email: ['email-assistant', 'shipping-assistant', 'support-forge'],
      leads: ['lead-qualifier', 'email-assistant', 'content-forge'],
      shipping: ['shipping-assistant', 'support-forge', 'email-assistant'],
      support: ['support-forge', 'shipping-assistant', 'email-assistant'],
      content: ['content-forge', 'social-forge', 'email-assistant'],
    },
    professional: {
      email: ['email-assistant', 'crm-assistant', 'meet-wise'],
      leads: ['lead-qualifier', 'email-assistant', 'crm-assistant'],
      shipping: ['email-assistant', 'crm-assistant', 'meet-wise'],
      support: ['support-forge', 'email-assistant', 'crm-assistant'],
      content: ['content-forge', 'email-assistant', 'meet-wise'],
    },
    contractors: {
      email: ['email-assistant', 'lead-qualifier', 'book-wise'],
      leads: ['lead-qualifier', 'book-wise', 'email-assistant'],
      shipping: ['email-assistant', 'invoice-forge', 'lead-qualifier'],
      support: ['support-forge', 'book-wise', 'email-assistant'],
      content: ['content-forge', 'lead-qualifier', 'social-forge'],
    },
    retail: {
      email: ['email-assistant', 'support-forge', 'social-forge'],
      leads: ['lead-qualifier', 'email-assistant', 'social-forge'],
      shipping: ['shipping-assistant', 'support-forge', 'email-assistant'],
      support: ['support-forge', 'email-assistant', 'invoice-forge'],
      content: ['social-forge', 'content-forge', 'email-assistant'],
    },
  };

  var INDUSTRY_LABELS = {
    hvac: 'Home services / HVAC',
    shopify: 'E-commerce / Shopify',
    professional: 'Professional services',
    contractors: 'Contractors / trades',
    retail: 'Local retail',
  };

  var DRAIN_LABELS = {
    email: 'Email overload',
    leads: 'Lead follow-up',
    shipping: 'Shipping & order issues',
    support: 'Customer support',
    content: 'Content & marketing',
  };

  function recommend(industry, drain) {
    var byIndustry = PACKS[industry] || PACKS.professional;
    var keys = byIndustry[drain] || byIndustry.email || ['email-assistant', 'lead-qualifier', 'crm-assistant'];
    return keys.slice(0, 3).map(function (k) {
      return Object.assign({ id: k }, AGENTS[k]);
    });
  }

  function el(id) {
    return document.getElementById(id);
  }

  function init() {
    var root = el('agent-quiz');
    if (!root) return;

    var state = {
      step: 1,
      industry: null,
      drain: null,
      tools: [],
      team: null,
    };

    var stepEls = root.querySelectorAll('[data-quiz-step]');
    var progress = el('quiz-progress');
    var result = el('quiz-result');

    function showStep(n) {
      state.step = n;
      stepEls.forEach(function (s) {
        var sn = parseInt(s.getAttribute('data-quiz-step'), 10);
        s.classList.toggle('hidden', sn !== n);
      });
      if (progress) {
        var pct = Math.min(100, Math.round(((n - 1) / 4) * 100));
        if (n === 5) pct = 100;
        progress.style.width = pct + '%';
        progress.setAttribute('aria-valuenow', String(pct));
      }
      if (result) result.classList.toggle('hidden', n !== 5);
    }

    root.querySelectorAll('[data-quiz-choice]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var field = btn.getAttribute('data-quiz-field');
        var value = btn.getAttribute('data-quiz-choice');
        if (field === 'industry') {
          state.industry = value;
          root.querySelectorAll('[data-quiz-field="industry"]').forEach(function (b) {
            b.classList.toggle('is-selected', b === btn);
          });
          showStep(2);
        } else if (field === 'drain') {
          state.drain = value;
          root.querySelectorAll('[data-quiz-field="drain"]').forEach(function (b) {
            b.classList.toggle('is-selected', b === btn);
          });
          showStep(3);
        } else if (field === 'team') {
          state.team = value;
          root.querySelectorAll('[data-quiz-field="team"]').forEach(function (b) {
            b.classList.toggle('is-selected', b === btn);
          });
          renderResult();
          showStep(5);
        }
      });
    });

    root.querySelectorAll('[data-quiz-tool]').forEach(function (chip) {
      chip.addEventListener('click', function () {
        var t = chip.getAttribute('data-quiz-tool');
        var i = state.tools.indexOf(t);
        if (i >= 0) state.tools.splice(i, 1);
        else state.tools.push(t);
        chip.classList.toggle('is-selected', state.tools.indexOf(t) >= 0);
      });
    });

    var toolsNext = el('quiz-tools-next');
    if (toolsNext) {
      toolsNext.addEventListener('click', function () {
        showStep(4);
      });
    }

    var backBtns = root.querySelectorAll('[data-quiz-back]');
    backBtns.forEach(function (b) {
      b.addEventListener('click', function () {
        var to = parseInt(b.getAttribute('data-quiz-back'), 10);
        showStep(to);
      });
    });

    var restart = el('quiz-restart');
    if (restart) {
      restart.addEventListener('click', function () {
        state = { step: 1, industry: null, drain: null, tools: [], team: null };
        root.querySelectorAll('.is-selected').forEach(function (n) {
          n.classList.remove('is-selected');
        });
        showStep(1);
      });
    }

    function renderResult() {
      var pack = recommend(state.industry, state.drain);
      try {
        localStorage.setItem(
          'matrixly-quiz-pack',
          JSON.stringify({
            industry: state.industry,
            drain: state.drain,
            tools: state.tools,
            team: state.team,
            agents: pack.map(function (a) {
              return a.id;
            }),
            at: Date.now(),
          })
        );
      } catch (e) {}

      var title = el('quiz-result-title');
      var sub = el('quiz-result-sub');
      var list = el('quiz-result-agents');
      if (title) {
        title.textContent =
          'Your starter stack for ' + (INDUSTRY_LABELS[state.industry] || 'your business');
      }
      if (sub) {
        sub.textContent =
          'Based on ' +
          (DRAIN_LABELS[state.drain] || 'your priorities').toLowerCase() +
          (state.tools.length ? ' and tools like ' + state.tools.slice(0, 3).join(', ') : '') +
          '. Start free with this pack — change agents anytime.';
      }
      if (list) {
        list.innerHTML = pack
          .map(function (a, idx) {
            return (
              '<article class="card-matrix rounded-xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-3">' +
              '<div class="flex-shrink-0 w-10 h-10 rounded-lg bg-matrix-green/10 text-matrix-green font-bold text-sm flex items-center justify-center">' +
              (idx + 1) +
              '</div>' +
              '<div class="flex-grow min-w-0">' +
              '<h4 class="font-bold text-matrix-cream text-sm sm:text-base">' +
              a.name +
              '</h4>' +
              '<p class="text-xs sm:text-sm text-matrix-soft mt-0.5">' +
              a.blurb +
              '</p>' +
              '</div>' +
              '<a href="' +
              a.href +
              '" class="text-sm font-semibold text-matrix-green hover:underline whitespace-nowrap">Details →</a>' +
              '</article>'
            );
          })
          .join('');
      }

      var cta = el('quiz-start-pack');
      if (cta) {
        cta.setAttribute('data-pack', pack.map(function (a) { return a.id; }).join(','));
      }
    }

    // Deep-link: /#agent-quiz?industry=hvac
    try {
      var params = new URLSearchParams(window.location.search);
      var pre = params.get('industry') || root.getAttribute('data-preselect-industry');
      if (pre && PACKS[pre]) {
        state.industry = pre;
        var match = root.querySelector('[data-quiz-field="industry"][data-quiz-choice="' + pre + '"]');
        if (match) match.classList.add('is-selected');
        showStep(2);
      } else {
        showStep(1);
      }
    } catch (e) {
      showStep(1);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/**
 * Matrixly — Social-proof counters + peer activity feed
 * Deterministic date-seeded numbers (believable, not pure random spam).
 */
(function () {
  'use strict';

  var FEED = [
    'An HVAC shop in Texas just deployed Lead Qualifier + Email Assistant',
    'A Shopify store in Oregon cut WISMO tickets with Shipping Assistant',
    'A dental practice in Colorado turned on SupportForge overnight coverage',
    'A contractor in Florida booked 3 more jobs this week with BookWise',
    'A boutique in Chicago scheduled a week of posts with SocialForge',
    'A consulting firm in Illinois cleaned CRM hygiene with CRM Assistant',
    'A home-services team in Arizona published local SEO pages with ContentForge',
    'An e-com brand in New York connected ShipStation + SupportForge',
  ];

  function daySeed() {
    var d = new Date();
    return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
  }

  function seeded(n) {
    // simple LCG from day seed + n
    var x = (daySeed() * 9301 + n * 49297) % 233280;
    return x / 233280;
  }

  function agentsDeployedThisWeek() {
    // base 180–320 range by day
    return Math.floor(180 + seeded(1) * 140);
  }

  function hoursReclaimedLastMonth() {
    // base 12k–28k
    return Math.floor(12000 + seeded(2) * 16000);
  }

  function formatInt(n) {
    return n.toLocaleString('en-US');
  }

  function initCounters() {
    var agentsEl = document.getElementById('sp-agents-week');
    var hoursEl = document.getElementById('sp-hours-month');
    if (!agentsEl && !hoursEl) return;

    var agentsTarget = agentsDeployedThisWeek();
    var hoursTarget = hoursReclaimedLastMonth();

    // Slight “live” drift within the hour (bounded)
    var hour = new Date().getHours();
    agentsTarget += Math.floor(seeded(3 + hour) * 12);
    hoursTarget += Math.floor(seeded(4 + hour) * 400);

    function animate(el, target, duration) {
      if (!el) return;
      var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reduce) {
        el.textContent = formatInt(target);
        return;
      }
      var start = 0;
      var t0 = null;
      function frame(ts) {
        if (!t0) t0 = ts;
        var p = Math.min(1, (ts - t0) / duration);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = formatInt(Math.floor(start + (target - start) * eased));
        if (p < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    }

    animate(agentsEl, agentsTarget, 1400);
    animate(hoursEl, hoursTarget, 1600);
  }

  function initFeed() {
    var feedEl = document.getElementById('sp-feed');
    if (!feedEl) return;

    var start = Math.floor(seeded(9) * FEED.length);
    var idx = start;
    feedEl.textContent = FEED[idx];

    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return;

    setInterval(function () {
      idx = (idx + 1) % FEED.length;
      feedEl.classList.add('sp-feed-fade');
      setTimeout(function () {
        feedEl.textContent = FEED[idx];
        feedEl.classList.remove('sp-feed-fade');
      }, 280);
    }, 5200);
  }

  function initResourceGate() {
    // Soft email gate for /resources guides
    document.querySelectorAll('[data-resource-gate]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var emailInput = form.querySelector('input[type="email"]');
        var email = emailInput && emailInput.value ? emailInput.value.trim() : '';
        if (!email || email.indexOf('@') < 0) return;
        try {
          localStorage.setItem('matrixly-resource-email', email);
          localStorage.setItem('matrixly-resource-unlocked', '1');
        } catch (err) {}
        var panel = form.closest('[data-gate-panel]');
        if (panel) {
          var locked = panel.querySelector('[data-gate-locked]');
          var unlocked = panel.querySelector('[data-gate-unlocked]');
          if (locked) locked.classList.add('hidden');
          if (unlocked) unlocked.classList.remove('hidden');
        }
      });
    });

    // Auto-unlock if previously gated
    try {
      if (localStorage.getItem('matrixly-resource-unlocked') === '1') {
        document.querySelectorAll('[data-gate-panel]').forEach(function (panel) {
          var locked = panel.querySelector('[data-gate-locked]');
          var unlocked = panel.querySelector('[data-gate-unlocked]');
          if (locked) locked.classList.add('hidden');
          if (unlocked) unlocked.classList.remove('hidden');
        });
      }
    } catch (e) {}
  }

  function init() {
    initCounters();
    initFeed();
    initResourceGate();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

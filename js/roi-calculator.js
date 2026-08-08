/**
 * Matrixly — Time & money savings calculator
 * Assumptions documented in docs/SMB_CONVERSION_PLAN.md
 */
(function () {
  'use strict';

  var RATES = {
    email: 0.55,
    leads: 0.6,
    shipping: 0.5,
    content: 0.45,
  };

  var DEFAULT_HOURLY = 40;

  function num(v, fallback) {
    var n = parseFloat(v);
    return isFinite(n) && n >= 0 ? n : fallback;
  }

  function formatMoney(n) {
    return (
      '$' +
      Math.round(n).toLocaleString('en-US', {
        maximumFractionDigits: 0,
      })
    );
  }

  function formatHours(n) {
    return (Math.round(n * 10) / 10).toFixed(1);
  }

  function init() {
    var root = document.getElementById('roi-calculator');
    if (!root) return;

    var inputs = {
      email: document.getElementById('roi-email'),
      leads: document.getElementById('roi-leads'),
      shipping: document.getElementById('roi-shipping'),
      content: document.getElementById('roi-content'),
      hourly: document.getElementById('roi-hourly'),
    };

    var outs = {
      hoursWeek: document.getElementById('roi-hours-week'),
      hoursMonth: document.getElementById('roi-hours-month'),
      dollarsWeek: document.getElementById('roi-dollars-week'),
      dollarsMonth: document.getElementById('roi-dollars-month'),
      breakdown: document.getElementById('roi-breakdown'),
    };

    function read() {
      return {
        email: num(inputs.email && inputs.email.value, 8),
        leads: num(inputs.leads && inputs.leads.value, 6),
        shipping: num(inputs.shipping && inputs.shipping.value, 4),
        content: num(inputs.content && inputs.content.value, 5),
        hourly: num(inputs.hourly && inputs.hourly.value, DEFAULT_HOURLY),
      };
    }

    function syncLabels(v) {
      var map = [
        ['roi-email-val', v.email],
        ['roi-leads-val', v.leads],
        ['roi-shipping-val', v.shipping],
        ['roi-content-val', v.content],
        ['roi-hourly-val', v.hourly],
      ];
      map.forEach(function (pair) {
        var el = document.getElementById(pair[0]);
        if (el) el.textContent = String(pair[1]);
      });
    }

    function compute() {
      var v = read();
      syncLabels(v);

      var parts = [
        { key: 'email', label: 'Email', hours: v.email * RATES.email },
        { key: 'leads', label: 'Lead follow-up', hours: v.leads * RATES.leads },
        { key: 'shipping', label: 'Shipping / exceptions', hours: v.shipping * RATES.shipping },
        { key: 'content', label: 'Content / support', hours: v.content * RATES.content },
      ];

      var hoursWeek = parts.reduce(function (s, p) {
        return s + p.hours;
      }, 0);
      var hoursMonth = hoursWeek * 4.3;
      var dollarsWeek = hoursWeek * v.hourly;
      var dollarsMonth = hoursMonth * v.hourly;

      if (outs.hoursWeek) outs.hoursWeek.textContent = formatHours(hoursWeek);
      if (outs.hoursMonth) outs.hoursMonth.textContent = formatHours(hoursMonth);
      if (outs.dollarsWeek) outs.dollarsWeek.textContent = formatMoney(dollarsWeek);
      if (outs.dollarsMonth) outs.dollarsMonth.textContent = formatMoney(dollarsMonth);

      if (outs.breakdown) {
        outs.breakdown.innerHTML = parts
          .map(function (p) {
            var pct = hoursWeek > 0 ? Math.round((p.hours / hoursWeek) * 100) : 0;
            return (
              '<div class="flex items-center justify-between gap-3 text-sm py-1.5">' +
              '<span class="text-matrix-soft">' +
              p.label +
              '</span>' +
              '<span class="font-semibold text-matrix-cream tabular-nums">' +
              formatHours(p.hours) +
              ' hrs · ' +
              pct +
              '%</span></div>'
            );
          })
          .join('');
      }

      try {
        localStorage.setItem(
          'matrixly-roi',
          JSON.stringify({
            inputs: v,
            hoursWeek: hoursWeek,
            hoursMonth: hoursMonth,
            dollarsWeek: dollarsWeek,
            dollarsMonth: dollarsMonth,
            at: Date.now(),
          })
        );
      } catch (e) {}

      return { hoursWeek: hoursWeek, dollarsMonth: dollarsMonth };
    }

    Object.keys(inputs).forEach(function (k) {
      var el = inputs[k];
      if (!el) return;
      el.addEventListener('input', compute);
      el.addEventListener('change', compute);
    });

    var cta = document.getElementById('roi-cta');
    if (cta) {
      cta.addEventListener('click', function () {
        compute();
      });
    }

    compute();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/**
 * Matrixly — Live “see an agent in action” simulated demo (no API).
 */
(function () {
  'use strict';

  var SCRIPTS = {
    qualify: {
      label: 'Qualify this lead',
      agent: 'Lead Qualifier',
      href: '/lead-qualifier',
      lines: [
        { role: 'user', text: 'Qualify this lead: Sarah Chen, owner of CoolBreeze HVAC in Katy, TX. Requested a quote for a 3-ton unit install. Phone + email on form. Budget “ASAP for summer.”' },
        { role: 'agent', text: 'Scoring lead… industry fit, urgency, and contact completeness.' },
        { role: 'agent', text: '**Score: 86 / 100 · Hot**\n\n• Fit: Home services + HVAC install — strong match for service verticals\n• Urgency: Seasonal “ASAP” language → prioritize same-day outreach\n• Completeness: Name, business, location, channel present\n\n**Suggested next step**\n1. SMS + email within 15 minutes\n2. Offer 2 install windows this week\n3. Attach financing FAQ if job > $4k\n\nDraft opener ready for your review (HITL).' },
      ],
    },
    shipping: {
      label: 'Draft a reply to a shipping delay',
      agent: 'Shipping Assistant',
      href: '/shipping-assistant',
      lines: [
        { role: 'user', text: 'Customer asks: “Where is order #48219? Tracking stuck in Memphis for 3 days.”' },
        { role: 'agent', text: 'Pulling ShipStation status and exception playbook…' },
        { role: 'agent', text: '**Exception: carrier delay (Memphis hub)**\n\nDraft reply (approve to send):\n\n---\nHi there — thanks for checking on order #48219.\n\nYour package is still with the carrier and shows a hub delay in Memphis. Current ETA is **Thu–Fri**. We’ve flagged the shipment and will text you the moment it moves again.\n\nIf it hasn’t scanned by Friday noon, reply to this email and we’ll upgrade shipping or reship at no cost under our delay policy.\n\nSorry for the wait — we’ve got eyes on it.\n— The team\n---\n\nAlso queued: proactive WISMO reduction note for similar hub delays.' },
      ],
    },
    inbox: {
      label: 'Triage my inbox',
      agent: 'Email Assistant',
      href: '/email-assistant',
      lines: [
        { role: 'user', text: 'Triage today’s inbox: 47 unread — mix of leads, vendor invoices, and newsletters.' },
        { role: 'agent', text: 'Clustering by intent and urgency…' },
        { role: 'agent', text: '**Daily brief · 47 messages**\n\n🔴 **Urgent (4)** — 2 new job requests, 1 payment dispute, 1 missed call follow-up\n🟡 **Needs you (9)** — quotes, reschedule, partner reply\n🟢 **Agent-ready (18)** — FAQs & shipping updates (drafts prepared)\n⚪ **Noise (16)** — newsletters / promos (archived suggestions)\n\nI drafted replies for the 18 agent-ready threads. Review queue is open — nothing sends without you.' },
      ],
    },
  };

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function init() {
    var root = document.getElementById('live-demo');
    if (!root) return;

    var thread = document.getElementById('live-demo-thread');
    var status = document.getElementById('live-demo-status');
    var cta = document.getElementById('live-demo-cta');
    var agentName = document.getElementById('live-demo-agent');
    var busy = false;

    function bubble(role, text) {
      var wrap = document.createElement('div');
      wrap.className =
        'live-demo-bubble ' + (role === 'user' ? 'live-demo-bubble--user' : 'live-demo-bubble--agent');
      var who = document.createElement('p');
      who.className = 'live-demo-who';
      who.textContent = role === 'user' ? 'You' : 'Matrixly agent';
      var body = document.createElement('div');
      body.className = 'live-demo-body';
      // light markdown: **bold** and newlines
      var html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
      body.innerHTML = html;
      wrap.appendChild(who);
      wrap.appendChild(body);
      thread.appendChild(wrap);
      thread.scrollTop = thread.scrollHeight;
    }

    function setStatus(msg) {
      if (status) status.textContent = msg || '';
    }

    async function runScript(key) {
      if (busy) return;
      var script = SCRIPTS[key];
      if (!script) return;
      busy = true;
      thread.innerHTML = '';
      if (agentName) agentName.textContent = script.agent;
      if (cta) {
        cta.href = script.href;
        cta.classList.remove('opacity-50', 'pointer-events-none');
        cta.textContent = 'Start free with ' + script.agent;
      }
      setStatus('Agent working…');

      for (var i = 0; i < script.lines.length; i++) {
        var line = script.lines[i];
        if (line.role === 'agent') {
          setStatus('Typing…');
          await sleep(550 + Math.min(900, line.text.length * 4));
        } else {
          await sleep(200);
        }
        bubble(line.role, line.text);
      }
      setStatus('Demo complete · nothing was sent — this is a simulation');
      busy = false;
    }

    root.querySelectorAll('[data-demo-script]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var key = btn.getAttribute('data-demo-script');
        root.querySelectorAll('[data-demo-script]').forEach(function (b) {
          b.classList.toggle('is-selected', b === btn);
        });
        runScript(key);
      });
    });

    var form = document.getElementById('live-demo-form');
    var input = document.getElementById('live-demo-input');
    if (form && input) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var text = (input.value || '').trim();
        if (!text) return;
        var key = 'inbox';
        var lower = text.toLowerCase();
        if (lower.indexOf('ship') >= 0 || lower.indexOf('wismo') >= 0 || lower.indexOf('delay') >= 0 || lower.indexOf('track') >= 0) {
          key = 'shipping';
        } else if (lower.indexOf('lead') >= 0 || lower.indexOf('qualif') >= 0 || lower.indexOf('quote') >= 0) {
          key = 'qualify';
        }
        input.value = '';
        runScript(key);
      });
    }

    // Auto-run first demo for engagement
    if (!window.matchMedia || !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setTimeout(function () {
        runScript('qualify');
        var first = root.querySelector('[data-demo-script="qualify"]');
        if (first) first.classList.add('is-selected');
      }, 400);
    } else {
      var firstBtn = root.querySelector('[data-demo-script="qualify"]');
      if (firstBtn) firstBtn.classList.add('is-selected');
      runScript('qualify');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

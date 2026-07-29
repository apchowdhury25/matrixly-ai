/**
 * One-shot generator for vertical LPs and resource guides.
 * Run: node scripts/generate-smb-pages.mjs
 */
import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = process.cwd();

const head = (title, desc) => `<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <script>
    (function () {
      try {
        var t = localStorage.getItem('matrixly-theme');
        if (t === 'dark') {
          document.documentElement.classList.add('dark');
          document.documentElement.setAttribute('data-theme', 'dark');
        } else {
          document.documentElement.classList.remove('dark');
          document.documentElement.setAttribute('data-theme', 'light');
        }
      } catch (e) {}
    })();
  </script>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="description" content="${desc}" />
  <meta name="theme-color" content="#117ACA" />
  <meta property="og:title" content="${title}" />
  <meta property="og:description" content="${desc}" />
  <title>${title}</title>
  <link rel="icon" type="image/png" href="/assets/matrixly-logo.png" />
  <link rel="apple-touch-icon" href="/assets/matrixly-logo.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            matrix: {
              black: 'var(--bg)', void: 'var(--bg-alt)', green: 'var(--brand-blue)',
              neon: 'var(--brand-blue)', forest: 'var(--brand-blue-dark)', dim: 'var(--brand-blue-hover)',
              glow: 'color-mix(in srgb, var(--brand-blue) 12%, transparent)',
              border: 'var(--border)', muted: 'var(--bg-muted)', card: 'var(--card)',
              soft: 'var(--soft)', cream: 'var(--ink)',
            }
          },
          fontFamily: {
            sans: ['Open Sans', 'Helvetica Neue', 'Arial', 'sans-serif'],
          },
        },
      },
    };
  </script>
  <style>
    :root {
      --brand-blue: #117ACA; --brand-blue-dark: #0B5CAB; --brand-blue-hover: #0D6BB0;
      --ink: #211E1E; --soft: #5C6670; --border: #D0D7DE; --bg: #FFFFFF; --bg-alt: #F5F7FA;
      --bg-muted: #F0F4F8; --card: #FFFFFF; --nav-bg: rgba(255,255,255,.92);
    }
    html.dark {
      --brand-blue: #3B9FE0; --brand-blue-dark: #117ACA; --brand-blue-hover: #5BB0E8;
      --ink: #F0F4F8; --soft: #9AA4B2; --border: #1E2A3A; --section-divider: rgba(148,163,184,.08);
      --bg: #0B1220; --bg-alt: #111827; --bg-muted: #151C28; --card: #151C28; --nav-bg: rgba(11,18,32,.94);
    }
    html.dark header.border-b, html.dark footer.border-t,
    html.dark .border-matrix-border, html.dark .border-matrix-border\\/40, html.dark .border-matrix-border\\/50 {
      border-color: var(--section-divider) !important;
    }
    body { font-family: 'Open Sans', sans-serif; background: var(--bg); color: var(--ink); }
    .btn-primary { background: var(--brand-blue); color: #fff; font-weight: 700; }
    .btn-primary:hover { background: var(--brand-blue-dark); }
    .btn-secondary { border: 1px solid var(--border); color: var(--ink); font-weight: 600; background: var(--card); }
    .card-matrix { background: var(--card); border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(33,30,30,.06); }
    .nav-link { color: var(--soft); font-weight: 600; font-size: .9rem; }
    .nav-link:hover { color: var(--brand-blue); }
    .nav-scrolled { background: var(--nav-bg); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); }
    .theme-toggle { width: 2.5rem; height: 2.5rem; border-radius: 999px; border: 1px solid var(--border); background: var(--bg-muted); display: inline-flex; align-items: center; justify-content: center; color: var(--brand-blue); }
    html.dark .theme-icon-sun { display: none; }
    html:not(.dark) .theme-icon-moon { display: none; }
    .video-ph {
      position: relative; border-radius: .85rem; overflow: hidden; aspect-ratio: 16/9;
      background: linear-gradient(145deg, color-mix(in srgb, var(--brand-blue) 18%, var(--bg-muted)), var(--bg-muted));
      border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; text-align: center;
    }
    .video-ph-play {
      width: 3.25rem; height: 3.25rem; border-radius: 999px; background: color-mix(in srgb, var(--brand-blue) 92%, #000);
      color: #fff; display: flex; align-items: center; justify-content: center; margin: 0 auto .5rem;
    }
    .video-ph-badge { position: absolute; top: .65rem; right: .65rem; font-size: .7rem; font-weight: 700; padding: .2rem .5rem; border-radius: 999px; background: rgba(0,0,0,.45); color: #fff; }
    .mobile-menu { display: none; }
    .mobile-menu.open { display: block; }
  </style>
</head>
<body class="bg-matrix-black antialiased">
`;

const nav = (active = "") => `
<header id="navbar" class="fixed top-0 left-0 right-0 z-50 transition-all duration-300">
  <nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between min-h-[4rem]">
      <a href="/" class="inline-flex items-center gap-2" aria-label="Matrixly Home">
        <img src="/assets/matrixly-logo.png" alt="Matrixly" width="36" height="36" class="w-9 h-9 object-contain rounded-md" />
        <span class="font-bold text-lg tracking-tight text-matrix-cream">Matrixly</span>
      </a>
      <div class="hidden md:flex items-center gap-6">
        <a href="/#how-it-works" class="nav-link">How it Works</a>
        <a href="/agents" class="nav-link">Agents</a>
        <a href="/resources" class="nav-link"${active === "resources" ? ' aria-current="page"' : ""}>Resources</a>
        <a href="/pricing" class="nav-link">Pricing</a>
        <button type="button" class="theme-toggle" data-theme-toggle aria-label="Toggle theme">
          <svg class="theme-icon-sun w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
          <svg class="theme-icon-moon w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        </button>
        <a href="/#final-cta" class="btn-primary px-4 py-2 rounded-lg text-sm">Get Started</a>
      </div>
      <div class="md:hidden flex items-center gap-2">
        <button type="button" class="theme-toggle" data-theme-toggle aria-label="Toggle theme">
          <svg class="theme-icon-sun w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
          <svg class="theme-icon-moon w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        </button>
        <button id="mobile-toggle" class="text-matrix-green p-2" aria-label="Menu" aria-expanded="false">☰</button>
      </div>
    </div>
    <div id="mobile-menu" class="mobile-menu border-t border-matrix-border py-3">
      <a href="/agents" class="block py-2 font-semibold text-matrix-soft">Agents</a>
      <a href="/resources" class="block py-2 font-semibold text-matrix-soft">Resources</a>
      <a href="/pricing" class="block py-2 font-semibold text-matrix-soft">Pricing</a>
      <a href="/#final-cta" class="btn-primary block text-center mt-2 py-2 rounded-lg">Get Started</a>
    </div>
  </nav>
</header>
`;

const footer = `
<footer class="border-t border-matrix-border/50 bg-matrix-void pt-14 pb-8 mt-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-10 mb-12">
      <div class="col-span-2 md:col-span-1">
        <a href="/" class="font-bold text-lg mb-3 inline-flex items-center gap-2">
          <img src="/assets/matrixly-logo.png" alt="" width="32" height="32" class="w-8 h-8 rounded-md" />
          <span class="text-matrix-cream">Matrixly</span>
        </a>
        <p class="text-sm text-matrix-soft">AI agents that work while you run your business.</p>
      </div>
      <div>
        <h4 class="text-xs font-bold text-matrix-green uppercase tracking-wider mb-4">Product</h4>
        <ul class="space-y-2 text-sm text-matrix-soft">
          <li><a href="/agents" class="hover:text-matrix-green">Agents</a></li>
          <li><a href="/pricing" class="hover:text-matrix-green">Pricing</a></li>
          <li><a href="/resources" class="hover:text-matrix-green">Resources</a></li>
        </ul>
      </div>
      <div>
        <h4 class="text-xs font-bold text-matrix-green uppercase tracking-wider mb-4">Industries</h4>
        <ul class="space-y-2 text-sm text-matrix-soft">
          <li><a href="/for/hvac" class="hover:text-matrix-green">HVAC</a></li>
          <li><a href="/for/shopify" class="hover:text-matrix-green">Shopify</a></li>
          <li><a href="/for/professional-services" class="hover:text-matrix-green">Pro services</a></li>
          <li><a href="/for/contractors" class="hover:text-matrix-green">Contractors</a></li>
        </ul>
      </div>
      <div>
        <h4 class="text-xs font-bold text-matrix-green uppercase tracking-wider mb-4">Get started</h4>
        <ul class="space-y-2 text-sm text-matrix-soft">
          <li><a href="/#agent-quiz" class="hover:text-matrix-green">Agent quiz</a></li>
          <li><a href="/#roi-calculator" class="hover:text-matrix-green">ROI calculator</a></li>
          <li><a href="/#final-cta" class="hover:text-matrix-green">Start free</a></li>
        </ul>
      </div>
    </div>
    <p class="text-xs text-matrix-soft border-t border-matrix-border/40 pt-6">© <span id="year"></span> Matrixly · All rights reserved</p>
  </div>
</footer>
<script>
  document.getElementById('year').textContent = new Date().getFullYear();
  (function () {
    var nav = document.getElementById('navbar');
    var onScroll = function () { nav.classList.toggle('nav-scrolled', window.scrollY > 40); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  })();
  (function () {
    var toggle = document.getElementById('mobile-toggle');
    var menu = document.getElementById('mobile-menu');
    if (!toggle) return;
    toggle.addEventListener('click', function () {
      var open = menu.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
    });
  })();
  (function () {
    var KEY = 'matrixly-theme';
    function isDark() { return document.documentElement.classList.contains('dark'); }
    function apply(theme) {
      var dark = theme === 'dark';
      document.documentElement.classList.toggle('dark', dark);
      document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
      try { localStorage.setItem(KEY, dark ? 'dark' : 'light'); } catch (e) {}
    }
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () { apply(isDark() ? 'light' : 'dark'); });
    });
  })();
</script>
</body>
</html>
`;

const verticals = [
  {
    path: "for/hvac/index.html",
    title: "AI Agents for HVAC & Home Services — Matrixly",
    desc: "Book more jobs and reclaim 20+ hours a week. Lead Qualifier, Email Assistant, and local SEO agents built for US HVAC and home-service owners.",
    eyebrow: "Home services · HVAC",
    h1: "More booked jobs. Fewer after-hours fires.",
    lead: "Matrixly agents qualify web leads, answer inquiries, and grow local search visibility — so your truck is full of the right work.",
    video: "Watch how an HVAC owner gets more booked jobs",
    industry: "hvac",
    agents: [
      { name: "Lead Qualifier", href: "/lead-qualifier", why: "Score inbound quote requests and draft same-day outreach." },
      { name: "Email Assistant", href: "/email-assistant", why: "Triage after-hours inbox noise; surface jobs that need you." },
      { name: "ContentForge", href: "/content-forge", why: "Service pages that rank for “near me” and seasonal demand." },
      { name: "BookWise", href: "/book-wise", why: "Confirm installs and reduce scheduling ping-pong." },
    ],
    roi: ["+40% organic leads in 90 days (example)", "25 hrs/week reclaimed (example)", "Payback often under 30 days"],
    integrations: ["Gmail", "Google Business", "HubSpot / CRM", "Calendar", "Slack"],
    cta: "Start free with HVAC stack",
  },
  {
    path: "for/shopify/index.html",
    title: "AI Agents for Shopify & E-commerce — Matrixly",
    desc: "Cut WISMO tickets and reclaim ops hours. Shipping Assistant and SupportForge for US Shopify stores.",
    eyebrow: "E-commerce · Shopify",
    h1: "Ship smarter. Answer less. Sell more.",
    lead: "Rate-shop carriers, update customers before they ask “where’s my order?”, and keep support covered without adding warehouse staff.",
    video: "See a Shopify store cut WISMO tickets",
    industry: "shopify",
    agents: [
      { name: "Shipping Assistant", href: "/shipping-assistant", why: "Track exceptions, draft WISMO replies, rate-shop carriers." },
      { name: "SupportForge", href: "/support-forge", why: "KB answers for shipping, returns, and product FAQs." },
      { name: "Email Assistant", href: "/email-assistant", why: "Recovery and order emails without living in Gmail." },
      { name: "ContentForge", href: "/content-forge", why: "Product copy and SEO posts that convert." },
    ],
    roi: ["−60% WISMO tickets (example)", "Faster exception handling", "Clear ROI within first invoice cycle"],
    integrations: ["Shopify", "ShipStation", "Stripe", "Klaviyo", "Gmail"],
    cta: "Start free with e-com stack",
  },
  {
    path: "for/professional-services/index.html",
    title: "AI Agents for Professional Services — Matrixly",
    desc: "Inbox calm and a full pipeline for legal, dental, consulting, and agencies. Email, CRM, and meeting agents for US firms.",
    eyebrow: "Professional services",
    h1: "Inbox calm. Pipeline full.",
    lead: "Triage email, prep meetings, keep CRM clean, and follow up leads before they go cold — without hiring another coordinator.",
    video: "Inbox calm for professional services",
    industry: "professional",
    agents: [
      { name: "Email Assistant", href: "/email-assistant", why: "Daily brief, drafts, and urgent flags." },
      { name: "CRM Assistant", href: "/crm-assistant", why: "Contact hygiene with approve-to-write controls." },
      { name: "MeetWise", href: "/meet-wise", why: "Summaries, actions, and recap emails from transcripts." },
      { name: "Lead Qualifier", href: "/lead-qualifier", why: "Score consults and draft outreach sequences." },
    ],
    roi: ["Reply time: hours → minutes (example)", "More qualified consults booked", "Less CRM admin for owners"],
    integrations: ["Gmail", "HubSpot", "Slack", "Calendar", "Zoom / Meet"],
    cta: "Start free with services stack",
  },
  {
    path: "for/contractors/index.html",
    title: "AI Agents for Contractors & Trades — Matrixly",
    desc: "Book more jobs, answer leads faster, and reclaim admin hours. Built for US contractors and trade businesses.",
    eyebrow: "Contractors · Trades",
    h1: "Win the job. Skip the admin spiral.",
    lead: "Qualify leads, book site visits, keep invoices moving, and stay visible locally — while you’re on the tools.",
    video: "How contractors reclaim admin hours with agents",
    industry: "contractors",
    agents: [
      { name: "Lead Qualifier", href: "/lead-qualifier", why: "Hot job requests don’t sit until Sunday night." },
      { name: "BookWise", href: "/book-wise", why: "Estimates and site visits on the calendar automatically." },
      { name: "Email Assistant", href: "/email-assistant", why: "Customer and supplier threads triaged daily." },
      { name: "InvoiceForge", href: "/invoice-forge", why: "Extract and chase paperwork without drowning in PDFs." },
    ],
    roi: ["Faster quote response", "Fewer missed appointments", "Admin hours back to billable work"],
    integrations: ["Gmail", "Google Business", "QuickBooks", "Calendar", "Square"],
    cta: "Start free with contractor stack",
  },
  {
    path: "for/local-retail/index.html",
    title: "AI Agents for Local Retail — Matrixly",
    desc: "Support, social, and ops agents for US local retail and brick-and-mortar shops with online demand.",
    eyebrow: "Local retail",
    h1: "Stay open online without living in the inbox.",
    lead: "Answer customers, keep social consistent, and handle shipping exceptions — so the floor and the stockroom stay your focus.",
    video: "Local retail agents in action",
    industry: "retail",
    agents: [
      { name: "SupportForge", href: "/support-forge", why: "Hours, stock, returns — answered from your knowledge base." },
      { name: "SocialForge", href: "/social-forge", why: "Posts and replies in brand voice for Meta and more." },
      { name: "Email Assistant", href: "/email-assistant", why: "Vendor and customer email without constant context-switching." },
      { name: "Shipping Assistant", href: "/shipping-assistant", why: "If you ship online orders, cut WISMO tickets." },
    ],
    roi: ["Fewer after-hours DMs unanswered", "Consistent social without a full-time marketer", "Clearer ops when online orders spike"],
    integrations: ["Shopify / Square", "Gmail", "Meta", "ShipStation", "Slack"],
    cta: "Start free with retail stack",
  },
];

function writeVertical(v) {
  const agentsHtml = v.agents
    .map(
      (a) => `
      <article class="card-matrix rounded-2xl p-5">
        <h3 class="font-bold text-matrix-cream mb-1"><a href="${a.href}" class="hover:text-matrix-green">${a.name}</a></h3>
        <p class="text-sm text-matrix-soft">${a.why}</p>
      </article>`
    )
    .join("");
  const roiHtml = v.roi.map((r) => `<li class="flex gap-2"><span class="text-matrix-green font-bold">✓</span><span>${r}</span></li>`).join("");
  const intHtml = v.integrations
    .map((i) => `<span class="card-matrix rounded-lg px-3 py-2 text-sm font-semibold text-matrix-cream">${i}</span>`)
    .join("");

  const html = `${head(v.title, v.desc)}
${nav()}
<main class="pt-24 pb-16">
  <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
    <div class="grid lg:grid-cols-2 gap-10 items-center">
      <div>
        <p class="text-sm font-semibold text-matrix-green uppercase tracking-wide mb-3">${v.eyebrow}</p>
        <h1 class="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-matrix-cream tracking-tight mb-4">${v.h1}</h1>
        <p class="text-lg text-matrix-soft mb-6 leading-relaxed">${v.lead}</p>
        <div class="flex flex-col sm:flex-row gap-3 mb-4">
          <a href="/#final-cta" class="btn-primary px-6 py-3 rounded-xl text-sm text-center">${v.cta}</a>
          <a href="/#agent-quiz?industry=${v.industry}" class="btn-secondary px-6 py-3 rounded-xl text-sm text-center">Take the agent quiz</a>
        </div>
        <p class="text-sm text-matrix-soft">Cancel anytime · 14-day free explore · <a href="/#guarantee" class="text-matrix-green font-semibold hover:underline">10-hour guarantee</a></p>
      </div>
      <div class="video-ph" role="img" aria-label="Demo video placeholder">
        <span class="video-ph-badge">1:15</span>
        <div>
          <div class="video-ph-play" aria-hidden="true">▶</div>
          <p class="text-sm font-semibold text-matrix-cream px-4">${v.video}</p>
          <p class="text-xs text-matrix-soft mt-1">Video placeholder · embed when ready</p>
        </div>
      </div>
    </div>
  </section>

  <section class="bg-matrix-muted border-y border-matrix-border/40 py-14">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <h2 class="text-2xl font-bold text-matrix-cream mb-2">Starter agent stack</h2>
      <p class="text-matrix-soft mb-8">Deploy 2–3 agents first. Expand when ROI is obvious.</p>
      <div class="grid sm:grid-cols-2 gap-4">${agentsHtml}</div>
    </div>
  </section>

  <section class="py-14">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid md:grid-cols-2 gap-10">
      <div>
        <h2 class="text-2xl font-bold text-matrix-cream mb-4">Industry ROI examples</h2>
        <ul class="space-y-3 text-matrix-soft">${roiHtml}</ul>
        <p class="text-xs text-matrix-soft mt-4">Illustrative · results vary by niche and execution</p>
      </div>
      <div>
        <h2 class="text-2xl font-bold text-matrix-cream mb-4">Integrations that matter</h2>
        <div class="flex flex-wrap gap-2">${intHtml}</div>
        <a href="/integrations" class="inline-block mt-6 text-sm font-semibold text-matrix-green hover:underline">Browse all integrations →</a>
      </div>
    </div>
  </section>

  <section class="pb-8">
    <div class="max-w-3xl mx-auto px-4 text-center card-matrix rounded-2xl p-8 border-matrix-green/25">
      <h2 class="text-xl font-bold text-matrix-cream mb-2">Ready when you are</h2>
      <p class="text-matrix-soft mb-6">Start free. Connect tools in minutes. Cancel anytime — no contract.</p>
      <a href="/#final-cta" class="btn-primary px-8 py-3 rounded-xl text-sm inline-block">${v.cta}</a>
    </div>
  </section>
</main>
${footer}`;

  const full = join(ROOT, v.path);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, html, "utf8");
  console.log("wrote", v.path);
}

const guides = [
  {
    path: "resources/7-day-setup/index.html",
    title: "7-Day Setup Checklist for Your First Agent — Matrixly",
    desc: "Day-by-day checklist to deploy your first Matrixly agent without a tech team.",
    h1: "7-day setup checklist for your first agent",
    body: `
      <ol class="list-decimal pl-5 space-y-4 text-matrix-soft">
        <li><strong class="text-matrix-cream">Day 1 — Pick one pain.</strong> Email, leads, shipping, or support. Don’t boil the ocean.</li>
        <li><strong class="text-matrix-cream">Day 2 — Create free account.</strong> Explore the marketplace; open the matching agent page.</li>
        <li><strong class="text-matrix-cream">Day 3 — Connect one tool.</strong> Gmail or Shopify or ShipStation — one integration only.</li>
        <li><strong class="text-matrix-cream">Day 4 — Run a sandbox job.</strong> Use sample data; review drafts before anything goes live.</li>
        <li><strong class="text-matrix-cream">Day 5 — Set HITL rules.</strong> Decide what auto-runs vs. what needs your approve click.</li>
        <li><strong class="text-matrix-cream">Day 6 — Go live on a narrow slice.</strong> One inbox label, one lead source, or one shipping exception type.</li>
        <li><strong class="text-matrix-cream">Day 7 — Measure hours.</strong> Note time saved; add a second agent only if ROI is clear.</li>
      </ol>`,
  },
  {
    path: "resources/email-voice/index.html",
    title: "How to Teach Email Assistant Your Voice — Matrixly",
    desc: "Playbook for teaching Matrixly Email Assistant your tone, do/don’t rules, and review habits.",
    h1: "How to teach Email Assistant your voice",
    body: `
      <ul class="space-y-4 text-matrix-soft">
        <li><strong class="text-matrix-cream">Collect 5–10 “gold” emails</strong> you actually sent that sound like you.</li>
        <li><strong class="text-matrix-cream">Write do / don’t rules</strong> (e.g. never promise discounts; always offer two time slots).</li>
        <li><strong class="text-matrix-cream">Set reading level</strong> — short sentences for SMS-style; longer for B2B proposals.</li>
        <li><strong class="text-matrix-cream">Review the first 20 drafts</strong> before raising autonomy.</li>
        <li><strong class="text-matrix-cream">Re-train monthly</strong> as seasons and offers change.</li>
      </ul>`,
  },
  {
    path: "resources/local-seo-playbook/index.html",
    title: "Local SEO Agent Playbook for Service Businesses — Matrixly",
    desc: "Playbook for service businesses using Matrixly agents for local SEO and Google Business.",
    h1: "Local SEO agent playbook for service businesses",
    body: `
      <ul class="space-y-4 text-matrix-soft">
        <li><strong class="text-matrix-cream">Map “near me” services</strong> — HVAC repair, emergency plumbing, roofing quotes, etc.</li>
        <li><strong class="text-matrix-cream">One page per service + city</strong> with proof (photos, reviews, response times).</li>
        <li><strong class="text-matrix-cream">Google Business hygiene</strong> — hours, categories, weekly posts.</li>
        <li><strong class="text-matrix-cream">Lead capture</strong> → Lead Qualifier within minutes of form submit.</li>
        <li><strong class="text-matrix-cream">Measure</strong> calls, forms, and booked jobs — not vanity rankings alone.</li>
      </ul>`,
  },
  {
    path: "resources/shipping-exceptions/index.html",
    title: "Shipping Exception Playbook — Matrixly",
    desc: "How US Shopify and e-com teams use Shipping Assistant for delays, WISMO, and carrier issues.",
    h1: "Shipping exception playbook",
    body: `
      <ul class="space-y-4 text-matrix-soft">
        <li><strong class="text-matrix-cream">Define exception types</strong> — hub delay, address issue, weather, lost.</li>
        <li><strong class="text-matrix-cream">Proactive WISMO</strong> — message before the customer asks.</li>
        <li><strong class="text-matrix-cream">HITL for refunds/reships</strong> — agent drafts; human approves cost.</li>
        <li><strong class="text-matrix-cream">Templates per carrier</strong> so tone stays consistent.</li>
        <li><strong class="text-matrix-cream">Weekly review</strong> of exception rate and time-to-resolution.</li>
      </ul>`,
  },
  {
    path: "resources/lead-follow-up/index.html",
    title: "Lead Follow-up SOP — Matrixly",
    desc: "SOP for US SMBs using Lead Qualifier for fast, consistent lead follow-up.",
    h1: "Lead follow-up SOP",
    body: `
      <ul class="space-y-4 text-matrix-soft">
        <li><strong class="text-matrix-cream">SLA:</strong> first human-approved touch within 15 minutes during open hours.</li>
        <li><strong class="text-matrix-cream">Score thresholds:</strong> Hot / Warm / Nurture with different sequences.</li>
        <li><strong class="text-matrix-cream">Channels:</strong> email + SMS where compliant; never spam cold lists.</li>
        <li><strong class="text-matrix-cream">CRM write-back</strong> only after approve-to-write.</li>
        <li><strong class="text-matrix-cream">Weekly win/loss review</strong> — which scores convert to booked jobs?</li>
      </ul>`,
  },
];

function writeGuide(g) {
  const gateId = "gate-email-" + g.path.replace(/\W/g, "-");
  const html = `${head(g.title, g.desc)}
${nav("resources")}
<main class="pt-24 pb-16">
  <article class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
    <p class="text-sm font-semibold text-matrix-green mb-2"><a href="/resources" class="hover:underline">← Owner resources</a></p>
    <h1 class="text-3xl sm:text-4xl font-extrabold text-matrix-cream mb-4">${g.h1}</h1>
    <p class="text-matrix-soft mb-8">Practical one-pager for US small-business owners. Free to read after a quick email unlock (stored only in your browser for this demo site).</p>

    <div class="card-matrix rounded-2xl p-6 sm:p-8 mb-8" data-gate-panel>
      <div data-gate-locked>
        <h2 class="font-bold text-matrix-cream mb-2">Unlock this playbook</h2>
        <p class="text-sm text-matrix-soft mb-4">Enter your email to reveal the full checklist. No spam — static demo stores email in localStorage only until an ESP is connected.</p>
        <form data-resource-gate class="flex flex-col sm:flex-row gap-2">
          <label class="sr-only" for="${gateId}">Email</label>
          <input id="${gateId}" type="email" required placeholder="you@company.com" class="flex-grow rounded-xl px-4 py-3 border border-matrix-border bg-matrix-card text-matrix-cream text-sm" />
          <button type="submit" class="btn-primary px-5 py-3 rounded-xl text-sm">Unlock free</button>
        </form>
      </div>
      <div data-gate-unlocked class="hidden">
        <p class="text-xs font-semibold text-matrix-green mb-4">Unlocked · save or print this page</p>
        ${g.body}
        <div class="mt-8 pt-6 border-t border-matrix-border/50">
          <a href="/#final-cta" class="btn-primary inline-block px-6 py-3 rounded-xl text-sm">Start free with Matrixly</a>
        </div>
      </div>
    </div>
  </article>
</main>
<script src="/js/social-proof.js" defer></script>
${footer}`;
  const full = join(ROOT, g.path);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, html, "utf8");
  console.log("wrote", g.path);
}

// Resources index
const resourcesIndex = `${head(
  "Owner Resources & Playbooks — Matrixly",
  "Downloadable playbooks and checklists for US small-business owners using Matrixly AI agents."
)}
${nav("resources")}
<main class="pt-24 pb-16">
  <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <p class="text-sm font-semibold text-matrix-green uppercase tracking-wide mb-3">Owner resources</p>
    <h1 class="text-3xl sm:text-4xl font-extrabold text-matrix-cream mb-4">Playbooks for busy owners</h1>
    <p class="text-lg text-matrix-soft max-w-2xl mb-10">Short, practical guides — setup checklists, voice training, local SEO, shipping, and lead follow-up. Best ones soft-gated for free email unlock.</p>
    <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
      ${guides
        .map(
          (g) => `
      <a href="/${dirname(g.path).replace(/\\\\/g, "/")}" class="card-matrix rounded-2xl p-6 block hover:border-matrix-green/40 transition-colors">
        <h2 class="font-bold text-matrix-cream mb-2">${g.h1}</h2>
        <p class="text-sm text-matrix-soft">${g.desc}</p>
        <span class="inline-block mt-4 text-sm font-semibold text-matrix-green">Open playbook →</span>
      </a>`
        )
        .join("")}
    </div>
    <div class="mt-12 card-matrix rounded-2xl p-8 text-center border-matrix-green/20">
      <h2 class="text-xl font-bold text-matrix-cream mb-2">Not sure where to start?</h2>
      <p class="text-matrix-soft mb-5">Take the 60-second quiz or calculate your hours back.</p>
      <div class="flex flex-wrap justify-center gap-3">
        <a href="/#agent-quiz" class="btn-primary px-5 py-3 rounded-xl text-sm">Agent quiz</a>
        <a href="/#roi-calculator" class="btn-secondary px-5 py-3 rounded-xl text-sm">ROI calculator</a>
      </div>
    </div>
  </section>
</main>
${footer}`;

writeFileSync(join(ROOT, "resources/index.html"), resourcesIndex, "utf8");
console.log("wrote resources/index.html");

verticals.forEach(writeVertical);
guides.forEach(writeGuide);
console.log("done");

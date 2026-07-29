# Matrixly SMB Conversion Plan

**Status:** Implementation in progress (static marketing site)  
**Audience:** US small-business owners and operators  
**Constraint for this workstream:** Build features in the working tree; **do not commit or push**.

---

## Thesis

Matrixly already speaks SMB language (20+ hours reclaimed, free tier, vertical use cases, Pick → Connect → Run → Grow). The next conversion lift comes from:

1. **Personalizing value** (quiz, ROI calculator)
2. **Making value visible in seconds** (live demo, short videos)
3. **Reducing risk** (guarantee, cancel anytime)
4. **Building trust** (named owner stories, social proof, peer activity)
5. **Guiding the next step** (vertical LPs, resources, comparison)

---

## The 10 ideas

| # | Idea | Primary surface | Acceptance |
|---|------|-----------------|------------|
| 1 | “Which agents for my business?” quiz | Homepage `#agent-quiz` | 4–5 steps → 2–3 agent pack + Start free |
| 2 | Vertical demo videos (60–90s) | Use-case cards, agent pages, `/for/*` | Playable placeholder or embed slot |
| 3 | Time & money savings calculator | Homepage `#roi-calculator` | Hours + $ value + trial CTA |
| 4 | Named owner stories | Homepage `#testimonials` / owner stories | Name, biz, location, before/after, clip slot |
| 5 | Risk-reversal guarantee | Homepage `#guarantee` + pricing | 14-day free + 10-hour month refund promise |
| 6 | vs. alternatives table | Homepage `#compare` + pricing | VA · Zapier+ChatGPT · Agency · Matrixly |
| 7 | Industry micro-LPs | `/for/*` | HVAC, Shopify, pro services, contractors, retail |
| 8 | Live agent-in-action widget | Homepage `#live-demo` | Simulated chat demo, no signup required |
| 9 | Owner resources / playbooks | `/resources` + guides | Soft email gate, downloadable/one-pager content |
| 10 | Social-proof counter + feed | Trust strip under hero | Seeded counters + rotating peer activity |

---

## Information architecture

### New routes

| Path | Purpose |
|------|---------|
| `/for/hvac` | Home services / HVAC |
| `/for/shopify` | E-commerce / Shopify |
| `/for/professional-services` | Legal, dental, consulting, agencies |
| `/for/contractors` | Trades & contractors |
| `/for/local-retail` | Local retail / brick + mortar |
| `/resources` | Owner playbook library index |
| `/resources/7-day-setup` | First agent checklist |
| `/resources/email-voice` | Teach Email Assistant your voice |
| `/resources/local-seo-playbook` | Local SEO for service businesses |
| `/resources/shipping-exceptions` | Shipping exception playbook |
| `/resources/lead-follow-up` | Lead follow-up SOP |

### Homepage section order (target)

1. Hero + social proof  
2. Trust / integrations  
3. Live demo  
4. How it works  
5. Use cases (→ vertical LPs + video)  
6. Agent quiz  
7. ROI calculator  
8. Impact charts (existing)  
9. Agents / products / logistics (existing)  
10. Comparison  
11. Owner stories  
12. Guarantee  
13. Pricing  
14. Integrations  
15. Resources teaser  
16. Final CTA  

---

## Content rules

### Illustrative social proof

Owner quotes and stories remain **illustrative composites** until real, permissioned customers are available. Structure (name, location, metrics, photo/clip slots) is production-ready for swap-in.

### Guarantee copy (canonical)

> Try free for 14 days. If you don’t save at least 10 hours in the first month on a paid plan, we’ll refund that plan — no questions asked.  
> Cancel anytime · No long-term contract.  
> *Terms apply · US paid plans.*

### ROI calculator assumptions

| Parameter | Default | Notes |
|-----------|---------|--------|
| Fully-loaded US SMB labor rate | **$40 / hour** | Adjustable in UI; blends wages + overhead for owner/operator time |
| Email reclaim rate | 55% | Agent drafts + triage still need light review |
| Lead follow-up reclaim rate | 60% | Scoring + sequences |
| Shipping / WISMO reclaim rate | 50% | Exceptions still need human judgment |
| Content / support reclaim rate | 45% | Brand review gate |

Hours reclaimed/week = Σ (input hours × category rate).  
Dollar value/week = hours × hourly rate.  
30-day projection = weeks × 4.3 (approx).

### Video placeholders

Until production footage exists, use design-system video cards (poster, title, duration, play affordance). Set `data-video-src` to a YouTube/Vimeo URL when available.

### Email gate (resources)

Static site only: capture email in `localStorage`, unlock guide content client-side. Wire to ESP later.

---

## Shared JS modules

| File | Role |
|------|------|
| `js/smb-quiz.js` | Multi-step quiz + pack recommendations |
| `js/roi-calculator.js` | Slider/input calculator |
| `js/live-agent-demo.js` | Simulated agent chat |
| `js/social-proof.js` | Date-seeded counters + activity feed |

Build copies the `js/` directory via `ASSET_DIRS` in `scripts/ci-build.mjs`.

---

## Positioning vs alternatives

| Dimension | Matrixly | Part-time VA | Zapier + ChatGPT | Agency |
|-----------|----------|--------------|------------------|--------|
| Monthly cost | $0–$149+ | $800–$2,000+ | $50–$200 + owner time | $2,000–$10,000+ |
| Setup | Minutes | Days–weeks | Hours–days DIY | Weeks |
| Maintenance | Low (managed agents) | Ongoing management | Owner builds & fixes | Included (expensive) |
| Output | Done work with HITL | Variable quality | Drafts + glue scripts | Campaigns / retainers |
| Autonomy | High within guardrails | Human only | Low without engineering | High but slow |

**Message:** Cheaper than hiring people; more autonomous than DIY automation; faster and more transparent than traditional agencies.

---

## Implementation checklist

- [x] Plan documented (`docs/SMB_CONVERSION_PLAN.md`)
- [x] JS modules (`js/smb-quiz.js`, `roi-calculator.js`, `live-agent-demo.js`, `social-proof.js`)
- [x] Homepage sections for all 10 ideas
- [x] Five vertical LPs under `/for/*`
- [x] Resources library + 5 guides
- [x] Pricing guarantee + compare echo
- [x] Agent video placeholders (Lead Qualifier, Shipping, Email)
- [x] `SITE_PAGES` updated in `scripts/ci-build.mjs`
- [x] Lint clean (`npm run lint` + `npm run build` passed)
- [x] No git commit / push

---

## Out of scope (this pass)

- Real customer video production and photography  
- Live analytics backend for counters  
- ESP / CRM wiring for resource gates  
- Git commit or deploy  

# Matrixly — Tailwind Design System Specification

**Source of truth:** Production static site (`index.html`, agent landing pages, catalog) at git `main`.  
**Brand name:** Matrixly only.  
**Stack context:** HTML5 + Tailwind CDN + CSS custom properties + light/dark theme toggle (`localStorage` key `matrixly-theme`).

> **Important naming note:** Historical token names use `matrix-green` / `neon`, but **the live accent color is brand blue** (`#117ACA` light / `#3B9FE0` dark), not lime/neon green. Treat “green” in class names as **brand accent**, not `#00FF00`.

---

## 1. Color Palette

### 1.1 CSS custom properties

#### Light (`:root`)

| Token | Hex / value | Role |
|-------|-------------|------|
| `--brand-blue` | `#117ACA` | Primary accent / CTAs |
| `--brand-blue-dark` | `#0B5CAB` | Pressed / dark accent |
| `--brand-blue-hover` | `#0D6BB0` | Hover accent |
| `--brand-blue-light` | `#DCEBFB` | Soft tint surfaces |
| `--brand-blue-soft` | `#E8F4FC` | Soft fill (tiles, terminal chrome) |
| `--ink` | `#211E1E` | Primary text |
| `--soft` | `#5C6670` | Secondary / muted text |
| `--border` | `#D0D7DE` | Borders |
| `--bg` | `#FFFFFF` | Page background |
| `--bg-alt` | `#F5F7FA` | Alternating sections |
| `--bg-muted` | `#F0F4F8` | Muted panels / code |
| `--card` | `#FFFFFF` | Card surfaces |
| `--nav-bg` | `rgba(255,255,255,0.92)` | Sticky nav glass |
| `--input-bg` | `#FFFFFF` | Form fields |
| `--toggle-bg` | `#F0F4F8` | Theme toggle fill |
| `--toggle-border` | `#D0D7DE` | Theme toggle border |
| `--grid-line` | `rgba(17,122,202,0.04)` | Subtle grid (often unused) |
| `--shadow-sm` | `0 1px 3px rgba(33,30,30,0.06)` | Resting elevation |
| `--shadow-md` | `0 8px 24px rgba(17,122,202,0.12)` | Hover elevation |

Legacy aliases (same values as brand blue): `--matrix-green`, `--matrix-neon` → `#117ACA`; `--matrix-forest` → `#0B5CAB`.

#### Dark (`html.dark`)

| Token | Hex / value | Role |
|-------|-------------|------|
| `--brand-blue` | `#3B9FE0` | Primary accent (brighter for dark UI) |
| `--brand-blue-dark` | `#117ACA` | Secondary accent |
| `--brand-blue-hover` | `#5BB0E8` | Hover |
| `--brand-blue-light` | `#1A3A52` | Soft tint |
| `--brand-blue-soft` | `#152536` | Soft fill |
| `--ink` | `#F0F4F8` | Primary text |
| `--soft` | `#9AA4B2` | Muted text |
| `--border` | `#1E2A3A` | Card/control borders |
| `--section-divider` | `rgba(148,163,184,0.08)` | Full-width section rules (soft) |
| `--bg` | `#0B1220` | Page background (deep navy) |
| `--bg-alt` | `#111827` | Alt sections |
| `--bg-muted` | `#151C28` | Muted panels |
| `--card` | `#151C28` | Cards |
| `--nav-bg` | `rgba(11,18,32,0.94)` | Nav glass |
| `--input-bg` | `#111827` | Inputs |
| `--toggle-bg` | `#1A2332` | Toggle |
| `--toggle-border` | `#1E2A3A` | Toggle border |
| `--grid-line` | `rgba(59,159,224,0.07)` | Grid tint |
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.4)` | Resting |
| `--shadow-md` | `0 8px 28px rgba(17,122,202,0.18)` | Hover glow |

`theme-color` meta: `#117ACA`.

### 1.2 Tailwind color map (`matrix.*`)

```js
// tailwind.config theme.extend.colors
matrix: {
  black: 'var(--bg)',      // page bg
  void:  'var(--bg-alt)',  // alt section
  green: 'var(--brand-blue)', // accent (name is legacy)
  neon:  'var(--brand-blue)',
  forest:'var(--brand-blue-dark)',
  dim:   'var(--brand-blue-hover)',
  glow:  'color-mix(in srgb, var(--brand-blue) 12%, transparent)',
  border:'var(--border)',
  muted: 'var(--bg-muted)',
  card:  'var(--card)',
  soft:  'var(--soft)',
  cream: 'var(--ink)',     // primary text (name is legacy)
}
```

### 1.3 Utility class patterns

| Intent | Classes / CSS |
|--------|----------------|
| Accent text | `text-matrix-green` or `text-[#117ACA]` (light) |
| Body text | `text-matrix-cream` → ink |
| Muted text | `text-matrix-soft` |
| Page bg | `bg-matrix-black` |
| Alt section | `bg-matrix-void` / `section-alt` |
| Card bg | `bg-matrix-card` |
| Border | `border-matrix-border` |
| Soft accent fill | `bg-matrix-green/10` |
| Status Live | `bg-matrix-green/10 text-matrix-green` |
| Status Beta | `bg-matrix-cream/5 text-amber-700` (or amber in dark) |
| Terminal dots | `bg-red-500/80`, `bg-yellow-500/80`, `bg-matrix-green/80` |

### 1.4 Success / status

| Status | Pattern |
|--------|---------|
| Live | `font-mono text-xs px-2 py-1 rounded bg-matrix-green/10 text-matrix-green` |
| Beta | `font-mono text-xs px-2 py-1 rounded bg-matrix-cream/5 text-amber-700` |
| Soon | `font-mono text-xs px-2 py-1 rounded bg-matrix-cream/5 text-matrix-soft` |
| Popular (pricing) | `.badge-popular` — solid brand blue, white text |
| Success in terminal | prefix `✓` + accent or soft green wording in mono |
| Warning in terminal | `⚠` + amber text |

---

## 2. Typography

### 2.1 Families

| Role | Spec |
|------|------|
| **UI / body / headings** | `'Open Sans', 'Helvetica Neue', Arial, sans-serif` |
| **Google Fonts load** | `Open+Sans:wght@400;500;600;700;800` |
| **“Mono” in Tailwind config** | Currently **same as sans** (Open Sans) — visual mono only via `font-mono` browser stack in some pages |
| **True mono (agent pages / cmds)** | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` (e.g. `pre.cmd`) |

### 2.2 Hierarchy

| Level | Pattern |
|-------|---------|
| **H1 hero** | `.h1-fluid` + `font-extrabold leading-[1.12] tracking-tight` — `clamp(1.75rem, 5vw + 0.5rem, 3.75rem)`, weight 700–800, letter-spacing `-0.02em` |
| **H2 section** | `.h2-fluid` + `font-bold` — `clamp(1.5rem, 3.5vw + 0.4rem, 3rem)`, `-0.015em` |
| **H3 card titles** | `text-lg sm:text-xl font-bold text-matrix-cream` |
| **Eyebrow / kicker** | `font-mono text-xs` or `text-sm` + `text-matrix-green tracking-wide` — often `// SECTION · LABEL` |
| **Body** | `text-base` / `text-lg text-matrix-soft` for supporting copy |
| **Nav links** | `text-sm font-bold` (0.875rem), color `var(--soft)` |
| **Stats** | large bold + `.stat-number` (`tabular-nums`) |
| **Logo wordmark** | `font-mono font-bold text-lg sm:text-xl tracking-tight` — `Matrixly` + accent `.AI` if used |

### 2.3 Code / terminal text

```
font-mono text-xs sm:text-sm leading-relaxed
text-matrix-soft for chrome labels
text-matrix-green for prompts / success lines
.cursor-blink for caret (▋, brand-blue)
```

---

## 3. Component Styles

### 3.1 Buttons

**Primary (`.btn-primary`)**

- Fill: brand blue; text white; border 1.5px brand blue  
- Weight 700; radius `0.5rem` (often `rounded-lg` / `rounded-xl` in markup)  
- min-height **44px**; letter-spacing `0.01em`  
- Hover: brand-blue-hover, lift `-1px`, stronger blue shadow  
- Active: brand-blue-dark  
- Focus-visible: 2px brand outline, offset 3px  

**Tailwind usage pattern:**

```html
<a class="btn-primary px-6 sm:px-8 py-3.5 sm:py-4 rounded-xl text-sm sm:text-base inline-flex items-center justify-center gap-2">
  Browse Agents
</a>
```

**Secondary (`.btn-secondary`)**

- Fill: card; text brand blue; border 1.5px brand blue  
- Weight 600; min-height 44px  
- Hover: brand-blue-soft bg, brand-blue-dark text, slight lift  

```html
<a class="btn-secondary px-6 py-3.5 rounded-xl text-sm inline-flex items-center justify-center">
  How it works
</a>
```

**Outline (implicit secondary)** — same as secondary; no separate ghost button in core CSS.

### 3.2 Cards

**Matrix card (`.card-matrix`)**

- bg `var(--card)`, border 1px `var(--border)`, shadow-sm  
- Hover: border brand blue, shadow-md, `translateY(-3px)` (disabled under 768px)  
- Radius typically `rounded-2xl`  
- Padding `p-5 sm:p-6`  

```html
<article class="card-matrix rounded-2xl p-5 sm:p-6 flex flex-col">
  ...
</article>
```

**Pricing featured (`.pricing-featured`)**

- Brand border + blue glow shadow  
- Gradient ring via `::before` mask  

**Feature / stat cards** — same `card-matrix` inside responsive grids.

### 3.3 Status badges

```html
<!-- Live -->
<span class="font-mono text-xs px-2 py-1 rounded bg-matrix-green/10 text-matrix-green">Live</span>

<!-- Beta -->
<span class="font-mono text-xs px-2 py-1 rounded bg-matrix-cream/5 text-amber-700">Beta</span>

<!-- Popular -->
<span class="badge-popular font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full">Most popular</span>
```

### 3.4 Agent tile / category chip (`.text-tile` / `.neon-tile`)

- 2.75rem square, radius 0.5rem  
- bg brand-blue-soft, border brand 35% mix  
- Label: 0.65rem, weight 700, brand color, letter-spacing 0.04em  
- Examples: `LEAD`, `MAIL`, `SHIP`, `ETF`, `CONT`  

```html
<div class="text-tile" aria-hidden="true">
  <div class="text-tile-base"><span>LEAD</span></div>
</div>
```

### 3.5 Section headers

```html
<p class="font-mono text-sm text-matrix-green mb-3 tracking-wide">// HOW IT WORKS</p>
<h2 class="h2-fluid font-bold text-matrix-cream mb-4">
  From marketplace to <span class="text-matrix-green">autonomy</span>
</h2>
<p class="text-matrix-soft text-lg max-w-xl">Supporting copy…</p>
```

**Numbered steps:** large mono index (`01`, `02`) or circular step with brand soft fill; optional `.flow-step-line` gradient connector.

### 3.6 Terminal / code blocks

**Window (`.terminal-window`)**

- bg alt, border, radius 12px, soft shadow  
- Header (`.terminal-header`): brand-blue-soft, traffic lights, mono title  

```html
<div class="terminal-window">
  <div class="terminal-header">
    <span class="terminal-dot bg-red-500/80"></span>
    <span class="terminal-dot bg-yellow-500/80"></span>
    <span class="terminal-dot bg-matrix-green/80"></span>
    <span class="ml-3 font-mono text-[10px] sm:text-xs text-matrix-soft">agent://seo-content-v2 — matrixly</span>
  </div>
  <div class="p-4 sm:p-5 font-mono text-xs sm:text-sm leading-relaxed space-y-1.5">
    <div class="text-matrix-soft">$ matrixly deploy --agent seo-content</div>
    <div class="text-matrix-green">✓ Agent initialized</div>
    <div class="text-matrix-soft cursor-blink">→ Analyzing…</div>
  </div>
</div>
```

**Deploy commands (`pre.cmd` on agent pages)**

```css
background: var(--bg-muted);
border: 1px solid var(--border);
border-radius: 0.75rem;
padding: 1rem 1.1rem;
font-size: 0.8rem;
font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
```

### 3.7 Navigation

- Fixed/sticky top; height 4rem (mobile) / 5rem (md+)  
- Grid: `auto 1fr auto` — brand | links | actions  
- Links: soft color; hover/current → brand blue  
- Scrolled: `.nav-scrolled` — frosted nav-bg, blur 16px, bottom border  
- Mobile: hamburger + `.mobile-menu` max-height transition  
- Actions: theme toggle (40px / 2.5rem) + primary CTA  

**Wordmark:** logo image optional + `Matrixly` bold mono; accent color on product suffix if present.

### 3.8 Footer

- `border-t border-matrix-border`, `bg-matrix-void`  
- Multi-column grid (2 col mobile → 4 col md)  
- Section labels: `font-mono text-xs text-matrix-green uppercase tracking-wider`  
- Links: `text-sm text-matrix-soft hover:text-matrix-green`  

### 3.9 Forms / auth modal

- Inputs: full width mobile; flex row from `sm`  
- min touch 44px; brand focus rings  
- Modal cards use `card-matrix` / elevated card  

### 3.10 Theme toggle

- `.theme-toggle` — 40×40, radius 0.5rem, toggle-bg/border, brand icon color  
- Persists `localStorage['matrixly-theme']` = `dark` | `light`  
- FOUC guard script in `<head>` sets `html.dark` before paint  

---

## 4. Layout & Spacing

### 4.1 Page structure

```
header#navbar (fixed)
main
  section (hero)
  section (logos / social proof)
  section (how it works)
  section (impact / charts)
  section (marketplace teaser)
  section (products)
  section (logistics / features)
  section (capabilities)
  section (wall of love)
  section (pricing)
  section (integrations / security)
  section (final CTA)
footer
```

### 4.2 Containers & section spacing

| Pattern | Classes |
|---------|---------|
| Container | `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` |
| Section vertical | `py-16 sm:py-20` or `py-20 sm:py-28` |
| Section alt | `bg-matrix-void` or `section-alt` + optional soft border-y |
| Hero | generous top padding under fixed nav (`pt-24`–`pt-32` range) |
| Card grids | `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6` |
| Two-column feature | `grid md:grid-cols-2 gap-10 md:gap-16 items-center` |

### 4.3 Radius scale

| Use | Value |
|-----|--------|
| Buttons / tiles | `0.5rem` (`rounded-lg`) |
| CTAs large | `rounded-xl` |
| Cards | `rounded-2xl` |
| Terminal | `12px` |
| Pills / badges | `rounded` / `rounded-full` |

### 4.4 Responsive behavior

| Breakpoint | Behavior |
|------------|----------|
| `< md` | Hide desktop nav; show mobile menu; stack CTAs full width; disable hover lift |
| `md+` | Full nav links + actions; multi-column grids |
| `lg+` | Wider gaps; floating terminal badges |
| Fluid type | `.h1-fluid` / `.h2-fluid` clamps |
| Reduced motion | Animations nearly disabled |

### 4.5 Motion

| Name | Use |
|------|-----|
| `animate-float` | Terminal / floating badges |
| `reveal` + `.visible` | Scroll-in sections (opacity + translateY) |
| `pulse-glow` | Optional CTA emphasis |
| `fade-up` | Entrance |

---

## 5. Visual Language & Theme Rules

### 5.1 Dual-theme principles

1. **Default shipping experience supports light + dark** via CSS variables — do not hardcode only one theme.  
2. **Dark = deep navy** (`#0B1220`), not pure black. Cards slightly lifted (`#151C28`).  
3. **Section dividers in dark** use `--section-divider` (very soft), never bright white hairlines.  
4. **Accent is electric blue**, high contrast on both themes.  
5. Prefer **token utilities** (`text-matrix-*`, `bg-matrix-*`) over raw hex in new code.

### 5.2 Accent usage (brand blue “Matrix” accent)

| Do | Don’t |
|----|--------|
| Use accent for CTAs, links hover, eyebrows, live badges, key numbers | Flood large body paragraphs in accent |
| Soft fills `bg-matrix-green/10` for chips | Neon glow on every card |
| Terminal success lines in accent | Rainbow status without hierarchy |

### 5.3 Agentic / technical feel

1. **Eyebrows** with `// SCREAMING_SNAKE` or `// DOMAIN · STATUS`  
2. **Terminal windows** for product demos (deploy logs, agent runs)  
3. **Monospace microcopy** for system status, tiles (`LEAD`, `SHIP`), integration names  
4. **▸ bullets** in accent for feature lists  
5. **HITL language** in product copy (approve-to-write, audit)  
6. **Wordmark:** clean `Matrixly` — technical, not playful cartoon  
7. Keep motion subtle; prefer professionalism over cyberpunk excess  

### 5.4 Copy & brand

- Brand string: **Matrixly** (never third-party product names as brand).  
- Voice: practical SMB operators, not enterprise theater.  
- Prefer “Deploy”, “Run”, “Agents”, “Marketplace”, “HITL”.  

---

## 6. Ready-to-paste Tailwind + token kit

### 6.1 Tailwind config snippet

```js
tailwind.config = {
  theme: {
    extend: {
      colors: {
        matrix: {
          black: 'var(--bg)',
          void: 'var(--bg-alt)',
          green: 'var(--brand-blue)',
          neon: 'var(--brand-blue)',
          forest: 'var(--brand-blue-dark)',
          dim: 'var(--brand-blue-hover)',
          glow: 'color-mix(in srgb, var(--brand-blue) 12%, transparent)',
          border: 'var(--border)',
          muted: 'var(--bg-muted)',
          card: 'var(--card)',
          soft: 'var(--soft)',
          cream: 'var(--ink)',
        },
      },
      fontFamily: {
        sans: ['Open Sans', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'glow-sm': '0 2px 8px rgba(17, 122, 202, 0.15)',
        glow: '0 4px 16px rgba(17, 122, 202, 0.18)',
        'glow-lg': '0 8px 28px rgba(17, 122, 202, 0.22)',
        card: '0 1px 3px rgba(33, 30, 30, 0.08), 0 4px 16px rgba(33, 30, 30, 0.06)',
      },
    },
  },
};
```

### 6.2 Component class cheat sheet

| Component | Classes |
|-----------|---------|
| Primary CTA | `btn-primary px-6 py-3.5 rounded-xl text-sm font-bold` |
| Secondary CTA | `btn-secondary px-6 py-3.5 rounded-xl text-sm` |
| Agent card | `card-matrix rounded-2xl p-5 sm:p-6 flex flex-col` |
| Section kicker | `font-mono text-sm text-matrix-green tracking-wide` |
| Section title | `h2-fluid font-bold text-matrix-cream` |
| Muted body | `text-matrix-soft text-lg` |
| Live badge | `font-mono text-xs px-2 py-1 rounded bg-matrix-green/10 text-matrix-green` |
| Page wrap | `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` |
| Section | `py-20 sm:py-28` |
| Nav link | `nav-link` (custom) or `text-sm font-bold text-matrix-soft hover:text-matrix-green` |

### 6.3 Theme bootstrap (required)

```html
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
```

---

## 7. File map (where styles live today)

| Area | Location |
|------|----------|
| Canonical tokens + components | Root `index.html` `<style>` + Tailwind config |
| Catalog | `agents/index.html` (mirrored tokens) |
| Per-agent marketing | `*/index.html` (shared subset of tokens + btn/card) |
| Logo asset | `assets/matrixly-transparent-logo.png` |

**Recommendation for future app work:** extract CSS variables + component classes into `packages/ui` or `styles/matrixly.css` and import everywhere so agent pages and the app shell cannot drift.

---

*End of Design System Specification — Matrixly*

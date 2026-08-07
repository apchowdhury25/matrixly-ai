#!/usr/bin/env python3
from pathlib import Path

p = Path("index.html")
t = p.read_text(encoding="utf-8")

repls = [
    (
        'data-quiz-back="1">← Back</button>',
        'data-quiz-back="1" data-i18n="quiz.back">← Back</button>',
    ),
    (
        'data-quiz-back="2">← Back</button>',
        'data-quiz-back="2" data-i18n="quiz.back">← Back</button>',
    ),
    (
        'data-quiz-back="3">← Back</button>',
        'data-quiz-back="3" data-i18n="quiz.back">← Back</button>',
    ),
    (
        'id="quiz-tools-next" class="btn-primary px-5 py-2.5 rounded-xl text-sm">Continue</button>',
        'id="quiz-tools-next" class="btn-primary px-5 py-2.5 rounded-xl text-sm" data-i18n="common.continue">Continue</button>',
    ),
    (
        'id="quiz-restart" class="btn-secondary px-6 py-3 rounded-xl text-sm">Retake quiz</button>',
        'id="quiz-restart" class="btn-secondary px-6 py-3 rounded-xl text-sm" data-i18n="quiz.retake">Retake quiz</button>',
    ),
    (
        '<p class="section-eyebrow">Results that matter</p>',
        '<p class="section-eyebrow" data-i18n="impact.title">Real impact for owners</p>',
    ),
    (
        '<p class="section-eyebrow">Ready agents</p>',
        '<p class="section-eyebrow" data-i18n="agentsTeaser.eyebrow">Your AI team</p>',
    ),
    (
        '<p class="section-eyebrow">Why Matrixly works</p>',
        '<p class="section-eyebrow" data-i18n="products.eyebrow">Product suite</p>',
    ),
    (
        '<p class="section-eyebrow">Owner stories</p>',
        '<p class="section-eyebrow" data-i18n="testimonials.title">What owners say</p>',
    ),
    (
        '<p class="section-eyebrow justify-center">Risk reversal</p>',
        '<p class="section-eyebrow justify-center" data-i18n="guarantee.title">Try it risk-free</p>',
    ),
    (
        '<p class="section-eyebrow">Owner resources</p>',
        '<p class="section-eyebrow" data-i18n="resources.eyebrow">Guides & playbooks</p>',
    ),
    (
        '<p class="section-eyebrow">Integrations &amp; security</p>',
        '<p class="section-eyebrow" data-i18n="integrations.eyebrow">Integrations</p>',
    ),
]

for a, b in repls:
    if a not in t:
        print("MISSING:", a[:70])
    else:
        t = t.replace(a, b, 1)
        print("ok:", a[:50])

if 'src="/js/i18n.js"' not in t:
    anchor = '  <script src="/js/smb-quiz.js" defer></script>'
    inject = (
        '  <script src="/js/i18n.js" defer></script>\n'
        '  <script src="/js/lang-selector.js" defer></script>\n'
        '  <script src="/js/smb-quiz.js" defer></script>'
    )
    if anchor in t:
        t = t.replace(anchor, inject, 1)
        print("scripts injected")
    else:
        print("script anchor missing")
else:
    print("i18n already present")

p.write_text(t, encoding="utf-8")
print("wrote", p)

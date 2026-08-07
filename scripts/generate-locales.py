#!/usr/bin/env python3
"""Generate complete i18n locale files for Matrixly (en, es, fr, ar, bn, de)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "i18n"

# English source of truth — same key structure as existing en.json
EN = {
  "meta": {
    "lang": "en",
    "dir": "ltr",
    "name": "English",
    "nativeName": "English"
  },
  "nav": {
    "howItWorks": "How it Works",
    "agents": "Agents",
    "resources": "Resources",
    "integrations": "Integrations",
    "pricing": "Pricing",
    "getStarted": "Get Started",
    "toggleMenu": "Toggle menu",
    "switchTheme": "Toggle light / dark theme"
  },
  "hero": {
    "badge": "Built for US small businesses · No tech team needed",
    "headline1": "Enterprise skills and systems — ",
    "headline2": "built for how small businesses actually work.",
    "sub1": "Bigger companies have specialized teams, proven playbooks, and powerful tools. Most small business owners wear every hat and still fall behind on the work that never stops — leads, email, support, shipping, invoicing, and local SEO.",
    "sub1Highlight": " 20+ hours a week",
    "sub1End": " to this — and it compounds every quarter you don't fix it.",
    "sub2Start": "Matrixly closes that gap.",
    "sub2": " We take the expertise, processes, and capabilities that used to be reserved for larger organizations and package them as ready-to-run AI agents tailored specifically to the way SMBs operate day to day. No developers required. No long implementation projects. No enterprise price tag.",
    "beforeLabel": "What you actually get",
    "beforeText": "Enterprise-grade capability — the same quality of systems and know-how bigger companies rely on",
    "afterLabel": "SMB-simple delivery",
    "afterText": "Pick an agent, connect the tools you already use, and go live in minutes",
    "bridgeLabel": "The result",
    "bridgeText": "You stop drowning in busywork and start running the business only you can run.",
    "bridgeHighlight": " 20+ hours a week",
    "bridgeEnd": " — without hiring more staff.",
    "cta": "Start free — no card needed",
    "spAgentsLabel": "Agents deployed this week by US SMBs",
    "spHoursLabel": "Hours reclaimed last month",
    "spFeed": "US small businesses are deploying Matrixly agents right now",
    "trust1": "Free to explore · Cancel anytime",
    "trust2": "Works with Shopify, Gmail & more",
    "trust3": "Your data never trains our models",
    "carouselTitle": "Meet your AI team",
    "carouselSub": "Pick an agent. Connect your tools. Get time and revenue back.",
    "live": "Live",
    "get1Title": "Enterprise-grade capability",
    "get1Text": " — the same quality of systems and know-how bigger companies rely on",
    "get2Title": "SMB-simple delivery",
    "get2Text": " — pick an agent, connect the tools you already use, and go live in minutes",
    "get3Title": "Real time back",
    "get3Text": " — most owners reclaim ",
    "get3Highlight": "20+ hours every week",
    "get3End": " without hiring more staff",
    "get4Title": "You stay in control",
    "get4Text": " — human approval steps where it matters, your data never trains our models",
    "whyEyebrow": "Why Matrixly"
  },
  "trust": {
    "title": "Connects to the tools US small businesses already use",
    "hoursBack": "Hours back every week",
    "hoursBackSub": "Less busywork. More time for customers and growth.",
    "payback": "Typical payback",
    "paybackSub": "Cheaper than a part-time hire — works 24/7",
    "minutes": "To first agent live",
    "minutesSub": "No developers. No long setup project."
  },
  "howItWorks": {
    "eyebrow": "How it works",
    "title": "From busywork to ",
    "titleHighlight": "done",
    "sub": "Four clear steps. No consultants. No six-month project.",
    "step1Label": "Step 1",
    "step1Title": "Pick your agents",
    "step1Text": "Choose the agents that match the work that drains your week — leads, email, support, shipping, SEO, and more.",
    "step2Label": "Step 2",
    "step2Title": "Connect your tools",
    "step2Text": "Link Gmail, Shopify, QuickBooks, CRM, or carriers in a few clicks. Your keys stay encrypted and private.",
    "step3Label": "Step 3",
    "step3Title": "Let agents work",
    "step3Text": "They draft replies, qualify leads, ship smarter, and grow local search — you review only what needs a human.",
    "step4Label": "Step 4",
    "step4Title": "See the impact",
    "step4Text": "Clear dashboard: hours saved, leads booked, tickets closed, and revenue tied to each agent."
  },
  "liveDemo": {
    "eyebrow": "See it work",
    "title": "Watch an agent ",
    "titleHighlight": "handle real work",
    "sub": "Type a request or tap a preset. This is a lightweight simulation — no signup required — so you can feel the product in seconds.",
    "chipQualify": "Qualify this lead",
    "chipShipping": "Draft a shipping delay reply",
    "chipInbox": "Triage my inbox",
    "placeholder": "e.g. Qualify this lead or draft a delay reply…",
    "run": "Run demo",
    "note": "Simulation only · nothing is sent to customers or connected tools",
    "cta": "Start free with this agent",
    "preview": "Agent preview",
    "sim": "live simulation",
    "demo": "Demo"
  },
  "useCases": {
    "eyebrow": "Built for Global Small and Medium Businesses",
    "title": "See how owners like you ",
    "titleHighlight": "get time back",
    "sub": "Home services, e-commerce, professional firms, contractors, and retail — agents handle the busywork so you can run the business.",
    "hvacTitle": "More booked jobs from local search",
    "hvacText": "Agents answer after-hours inquiries, qualify web leads, and publish service pages that rank for “near me” searches — so your phone rings with the right jobs.",
    "shopifyTitle": "Ship faster, sell more, answer less",
    "shopifyText": "Rate-shop carriers, update customers before they ask “where’s my order?”, and optimize product copy — without adding warehouse staff.",
    "proTitle": "Inbox calm. Pipeline full.",
    "proText": "Legal, dental, consulting, and local agencies use agents to triage email, prep meetings, keep CRM clean, and follow up leads before they go cold.",
    "quizCta": "Not sure? Take the 60-second quiz"
  },
  "quiz": {
    "eyebrow": "60-second fit check",
    "title": "Which agents fit ",
    "titleHighlight": "your week?",
    "sub": "Answer a few questions. We’ll recommend the agents that reclaim the most time for your business.",
    "start": "Start the quiz",
    "next": "Next",
    "back": "Back",
    "seeResults": "See my agents",
    "retake": "Retake quiz"
  },
  "roi": {
    "eyebrow": "Simple math",
    "title": "What is 20 hours a week ",
    "titleHighlight": "worth to you?",
    "sub": "Owners often underestimate the cost of busywork. Plug in your numbers — the payback is usually clear in under a minute.",
    "hoursLabel": "Hours lost to busywork / week",
    "rateLabel": "Your time value ($/hour)",
    "resultLabel": "Estimated value of time reclaimed / month",
    "cta": "Start free and reclaim those hours"
  },
  "impact": {
    "title": "Real impact for owners",
    "sub": "Hours back. Leads answered. Tickets closed. Revenue tied to agents — not more headcount."
  },
  "agentsTeaser": {
    "eyebrow": "Your AI team",
    "title": "Agents that do the work",
    "sub": "Each agent is ready to connect and run. Start with one. Add more as you see the hours come back.",
    "viewAll": "View all agents"
  },
  "products": {
    "eyebrow": "Product suite",
    "title": "Everything you need to ",
    "titleHighlight": "run lean",
    "sub": "From lead qualification to shipping exceptions — one place to deploy and manage your AI workforce."
  },
  "logistics": {
    "title": "Shipping & logistics agents",
    "sub": "Rate shop, track, and keep customers updated without living in the carrier portal."
  },
  "features": {
    "title": "Built for owners, not IT departments",
    "sub": "Security, privacy, and simple controls — so you stay in charge."
  },
  "compare": {
    "title": "How Matrixly compares",
    "sub": "No six-figure implementation. No waiting for a developer. Just agents that work."
  },
  "testimonials": {
    "title": "What owners say",
    "sub": "Real feedback from small business owners who reclaimed their week."
  },
  "guarantee": {
    "title": "Try it risk-free",
    "sub": "Explore free. Cancel anytime. Your data stays yours."
  },
  "pricing": {
    "eyebrow": "Simple pricing",
    "title": "Plans that scale with ",
    "titleHighlight": "your business",
    "sub": "Start free. Upgrade when the agents are saving you time and money.",
    "monthly": "Monthly",
    "yearly": "Yearly",
    "save": "Save",
    "popular": "Most popular",
    "cta": "Get started",
    "contact": "Talk to us"
  },
  "resources": {
    "eyebrow": "Guides & playbooks",
    "title": "Practical resources for ",
    "titleHighlight": "owners",
    "sub": "Short, actionable guides — setup, email voice, local SEO, shipping exceptions, and more."
  },
  "integrations": {
    "eyebrow": "Integrations",
    "title": "Works with the tools you ",
    "titleHighlight": "already use",
    "sub": "Gmail, Shopify, QuickBooks, CRMs, carriers, and more — connect in minutes."
  },
  "finalCta": {
    "title": "Ready to get your time back?",
    "sub": "Deploy your first agent in minutes. No card required to explore.",
    "cta": "Start free — no card needed"
  },
  "auth": {
    "signIn": "Sign in",
    "signUp": "Sign up",
    "email": "Email",
    "password": "Password",
    "forgot": "Forgot password?",
    "noAccount": "Don’t have an account?",
    "hasAccount": "Already have an account?"
  },
  "footer": {
    "product": "Product",
    "company": "Company",
    "resources": "Resources",
    "legal": "Legal",
    "privacy": "Privacy",
    "terms": "Terms",
    "contact": "Contact",
    "tagline": "AI agents for small and medium businesses — live in minutes, no tech team needed."
  },
  "common": {
    "learnMore": "Learn more",
    "getStarted": "Get started",
    "tryFree": "Try free",
    "loading": "Loading…",
    "error": "Something went wrong. Please try again.",
    "close": "Close",
    "save": "Save",
    "cancel": "Cancel",
    "continue": "Continue",
    "back": "Back",
    "next": "Next",
    "submit": "Submit",
    "language": "Language",
    "selectLanguage": "Select language"
  }
}

# Strip extra hero keys that aren't in original structure for empty locales compliance
# User said keep existing keys and not invent new ones. Original didn't have get* or whyEyebrow.
# I'll keep them only in en for richer page, but put same keys in all langs so structure matches.
# Actually user: "Keep all existing keys... Do not invent new keys."
# So I should NOT add get1Title etc. Map with existing keys only.
# Remove invented keys from EN for strict compliance.

for k in list(EN["hero"].keys()):
    if k.startswith("get") or k == "whyEyebrow":
        del EN["hero"][k]

ES = {
  "meta": {"lang": "es", "dir": "ltr", "name": "Spanish", "nativeName": "Español"},
  "nav": {
    "howItWorks": "Cómo funciona",
    "agents": "Agentes",
    "resources": "Recursos",
    "integrations": "Integraciones",
    "pricing": "Precios",
    "getStarted": "Empezar",
    "toggleMenu": "Abrir o cerrar menú",
    "switchTheme": "Cambiar tema claro / oscuro"
  },
  "hero": {
    "badge": "Hecho para pymes · Sin equipo técnico",
    "headline1": "Capacidades y sistemas de nivel empresa — ",
    "headline2": "diseñados para cómo operan de verdad las pymes.",
    "sub1": "Las empresas grandes tienen equipos especializados, playbooks probados y herramientas potentes. La mayoría de dueños de pymes llevan todos los sombreros y aun así se quedan atrás en el trabajo que no para: leads, correo, soporte, envíos, facturación y SEO local.",
    "sub1Highlight": " más de 20 horas a la semana",
    "sub1End": " en esto — y se acumula cada trimestre que no lo resuelves.",
    "sub2Start": "Matrixly cierra esa brecha.",
    "sub2": " Tomamos la experiencia, los procesos y las capacidades que antes solo tenían las grandes organizaciones y los empaquetamos como agentes de IA listos para usar, adaptados a cómo operan las pymes día a día. Sin desarrolladores. Sin proyectos largos. Sin precio de enterprise.",
    "beforeLabel": "Lo que realmente obtienes",
    "beforeText": "Capacidad de nivel empresarial — la misma calidad de sistemas y know-how en la que confían las grandes compañías",
    "afterLabel": "Entrega simple para pymes",
    "afterText": "Elige un agente, conecta las herramientas que ya usas y ponlo en marcha en minutos",
    "bridgeLabel": "El resultado",
    "bridgeText": "Dejas de ahogarte en tareas rutinarias y empiezas a dirigir el negocio que solo tú puedes dirigir.",
    "bridgeHighlight": " más de 20 horas a la semana",
    "bridgeEnd": " — sin contratar más personal.",
    "cta": "Empieza gratis — sin tarjeta",
    "spAgentsLabel": "Agentes desplegados esta semana por pymes",
    "spHoursLabel": "Horas recuperadas el mes pasado",
    "spFeed": "Las pymes están desplegando agentes Matrixly ahora mismo",
    "trust1": "Explora gratis · Cancela cuando quieras",
    "trust2": "Funciona con Shopify, Gmail y más",
    "trust3": "Tus datos nunca entrenan nuestros modelos",
    "carouselTitle": "Conoce tu equipo de IA",
    "carouselSub": "Elige un agente. Conecta tus herramientas. Recupera tiempo e ingresos.",
    "live": "En vivo"
  },
  "trust": {
    "title": "Se conecta a las herramientas que las pymes ya usan",
    "hoursBack": "Horas de vuelta cada semana",
    "hoursBackSub": "Menos trabajo rutinario. Más tiempo para clientes y crecimiento.",
    "payback": "Retorno típico",
    "paybackSub": "Más barato que un medio tiempo — trabaja 24/7",
    "minutes": "Hasta el primer agente en vivo",
    "minutesSub": "Sin desarrolladores. Sin un proyecto de meses."
  },
  "howItWorks": {
    "eyebrow": "Cómo funciona",
    "title": "Del trabajo rutinario a ",
    "titleHighlight": "hecho",
    "sub": "Cuatro pasos claros. Sin consultores. Sin proyecto de seis meses.",
    "step1Label": "Paso 1",
    "step1Title": "Elige tus agentes",
    "step1Text": "Escoge los agentes que cubren el trabajo que se come tu semana: leads, correo, soporte, envíos, SEO y más.",
    "step2Label": "Paso 2",
    "step2Title": "Conecta tus herramientas",
    "step2Text": "Vincula Gmail, Shopify, QuickBooks, CRM o transportistas en pocos clics. Tus claves quedan cifradas y privadas.",
    "step3Label": "Paso 3",
    "step3Title": "Deja que los agentes trabajen",
    "step3Text": "Redactan respuestas, califican leads, envían mejor y mejoran el SEO local — tú solo revisas lo que necesita un humano.",
    "step4Label": "Paso 4",
    "step4Title": "Mira el impacto",
    "step4Text": "Panel claro: horas ahorradas, leads captados, tickets cerrados e ingresos ligados a cada agente."
  },
  "liveDemo": {
    "eyebrow": "Míralo en acción",
    "title": "Mira cómo un agente ",
    "titleHighlight": "hace trabajo real",
    "sub": "Escribe una petición o elige una plantilla. Es una simulación ligera — sin registro — para que sientas el producto en segundos.",
    "chipQualify": "Calificar este lead",
    "chipShipping": "Redactar respuesta por retraso de envío",
    "chipInbox": "Triaje de mi bandeja",
    "placeholder": "p. ej. Calificar este lead o redactar una respuesta por retraso…",
    "run": "Ejecutar demo",
    "note": "Solo simulación · no se envía nada a clientes ni herramientas conectadas",
    "cta": "Empieza gratis con este agente",
    "preview": "Vista previa del agente",
    "sim": "simulación en vivo",
    "demo": "Demo"
  },
  "useCases": {
    "eyebrow": "Hecho para pymes de todo el mundo",
    "title": "Así recuperan tiempo ",
    "titleHighlight": "dueños como tú",
    "sub": "Servicios del hogar, e-commerce, despachos profesionales, contratistas y retail — los agentes hacen la rutina para que tú dirijas el negocio.",
    "hvacTitle": "Más trabajos reservados desde la búsqueda local",
    "hvacText": "Los agentes responden fuera de horario, califican leads web y publican páginas de servicio que rankean en búsquedas “cerca de mí” — para que el teléfono suene con los trabajos correctos.",
    "shopifyTitle": "Envía más rápido, vende más, responde menos",
    "shopifyText": "Compara tarifas de transportistas, actualiza a clientes antes de que pregunten “¿dónde está mi pedido?” y optimiza copys de producto — sin sumar personal de almacén.",
    "proTitle": "Bandeja en calma. Pipeline lleno.",
    "proText": "Despachos, clínicas, consultorías y agencias locales usan agentes para triaje de correo, prep de reuniones, CRM limpio y seguimiento de leads antes de que se enfríen.",
    "quizCta": "¿No estás seguro? Haz el quiz de 60 segundos"
  },
  "quiz": {
    "eyebrow": "Chequeo de encaje en 60 segundos",
    "title": "¿Qué agentes encajan con ",
    "titleHighlight": "tu semana?",
    "sub": "Responde unas preguntas. Te recomendaremos los agentes que más tiempo te devuelven.",
    "start": "Empezar el quiz",
    "next": "Siguiente",
    "back": "Atrás",
    "seeResults": "Ver mis agentes",
    "retake": "Repetir quiz"
  },
  "roi": {
    "eyebrow": "Cuentas claras",
    "title": "¿Cuánto valen 20 horas a la semana ",
    "titleHighlight": "para ti?",
    "sub": "Los dueños suelen subestimar el coste de la rutina. Introduce tus números — el retorno suele verse en menos de un minuto.",
    "hoursLabel": "Horas perdidas en rutina / semana",
    "rateLabel": "Valor de tu tiempo ($/hora)",
    "resultLabel": "Valor estimado del tiempo recuperado / mes",
    "cta": "Empieza gratis y recupera esas horas"
  },
  "impact": {
    "title": "Impacto real para dueños",
    "sub": "Horas de vuelta. Leads respondidos. Tickets cerrados. Ingresos ligados a agentes — no a más personal."
  },
  "agentsTeaser": {
    "eyebrow": "Tu equipo de IA",
    "title": "Agentes que hacen el trabajo",
    "sub": "Cada agente está listo para conectar y operar. Empieza con uno. Añade más cuando veas las horas volver.",
    "viewAll": "Ver todos los agentes"
  },
  "products": {
    "eyebrow": "Suite de productos",
    "title": "Todo lo que necesitas para ",
    "titleHighlight": "operar en ligero",
    "sub": "Desde calificación de leads hasta excepciones de envío — un solo lugar para desplegar y gestionar tu fuerza de trabajo de IA."
  },
  "logistics": {
    "title": "Agentes de envío y logística",
    "sub": "Compara tarifas, rastrea y mantén informados a los clientes sin vivir en el portal del transportista."
  },
  "features": {
    "title": "Hecho para dueños, no para departamentos de TI",
    "sub": "Seguridad, privacidad y controles simples — para que sigas al mando."
  },
  "compare": {
    "title": "Cómo se compara Matrixly",
    "sub": "Sin implantaciones de seis cifras. Sin esperar a un desarrollador. Solo agentes que funcionan."
  },
  "testimonials": {
    "title": "Lo que dicen los dueños",
    "sub": "Opiniones reales de emprendedores que recuperaron su semana."
  },
  "guarantee": {
    "title": "Pruébalo sin riesgo",
    "sub": "Explora gratis. Cancela cuando quieras. Tus datos son tuyos."
  },
  "pricing": {
    "eyebrow": "Precios simples",
    "title": "Planes que crecen con ",
    "titleHighlight": "tu negocio",
    "sub": "Empieza gratis. Mejora de plan cuando los agentes te ahorren tiempo y dinero.",
    "monthly": "Mensual",
    "yearly": "Anual",
    "save": "Ahorra",
    "popular": "Más popular",
    "cta": "Empezar",
    "contact": "Habla con nosotros"
  },
  "resources": {
    "eyebrow": "Guías y playbooks",
    "title": "Recursos prácticos para ",
    "titleHighlight": "dueños",
    "sub": "Guías cortas y accionables — setup, tono de correo, SEO local, excepciones de envío y más."
  },
  "integrations": {
    "eyebrow": "Integraciones",
    "title": "Funciona con las herramientas que ",
    "titleHighlight": "ya usas",
    "sub": "Gmail, Shopify, QuickBooks, CRMs, transportistas y más — conéctalos en minutos."
  },
  "finalCta": {
    "title": "¿Listo para recuperar tu tiempo?",
    "sub": "Despliega tu primer agente en minutos. Sin tarjeta para explorar.",
    "cta": "Empieza gratis — sin tarjeta"
  },
  "auth": {
    "signIn": "Iniciar sesión",
    "signUp": "Registrarse",
    "email": "Correo",
    "password": "Contraseña",
    "forgot": "¿Olvidaste la contraseña?",
    "noAccount": "¿No tienes cuenta?",
    "hasAccount": "¿Ya tienes cuenta?"
  },
  "footer": {
    "product": "Producto",
    "company": "Empresa",
    "resources": "Recursos",
    "legal": "Legal",
    "privacy": "Privacidad",
    "terms": "Términos",
    "contact": "Contacto",
    "tagline": "Agentes de IA para pymes — en vivo en minutos, sin equipo técnico."
  },
  "common": {
    "learnMore": "Saber más",
    "getStarted": "Empezar",
    "tryFree": "Probar gratis",
    "loading": "Cargando…",
    "error": "Algo salió mal. Inténtalo de nuevo.",
    "close": "Cerrar",
    "save": "Guardar",
    "cancel": "Cancelar",
    "continue": "Continuar",
    "back": "Atrás",
    "next": "Siguiente",
    "submit": "Enviar",
    "language": "Idioma",
    "selectLanguage": "Seleccionar idioma"
  }
}

FR = {
  "meta": {"lang": "fr", "dir": "ltr", "name": "French", "nativeName": "Français"},
  "nav": {
    "howItWorks": "Comment ça marche",
    "agents": "Agents",
    "resources": "Ressources",
    "integrations": "Intégrations",
    "pricing": "Tarifs",
    "getStarted": "Commencer",
    "toggleMenu": "Ouvrir ou fermer le menu",
    "switchTheme": "Basculer thème clair / sombre"
  },
  "hero": {
    "badge": "Conçu pour les PME · Sans équipe technique",
    "headline1": "Compétences et systèmes d’entreprise — ",
    "headline2": "pensés pour le quotidien des petites entreprises.",
    "sub1": "Les grandes entreprises ont des équipes spécialisées, des playbooks éprouvés et des outils puissants. La plupart des dirigeants de PME portent toutes les casquettes et prennent du retard sur le travail qui ne s’arrête jamais — leads, e-mails, support, expéditions, facturation et SEO local.",
    "sub1Highlight": " plus de 20 heures par semaine",
    "sub1End": " à cela — et cela s’accumule chaque trimestre sans solution.",
    "sub2Start": "Matrixly comble cet écart.",
    "sub2": " Nous prenons l’expertise, les processus et les capacités autrefois réservés aux grandes organisations et les packagons en agents IA prêts à l’emploi, adaptés au rythme des PME. Sans développeurs. Sans longs projets. Sans prix enterprise.",
    "beforeLabel": "Ce que vous obtenez vraiment",
    "beforeText": "Capacité de niveau entreprise — la même qualité de systèmes et de savoir-faire sur laquelle s’appuient les grandes sociétés",
    "afterLabel": "Livraison simple pour les PME",
    "afterText": "Choisissez un agent, connectez les outils que vous utilisez déjà, et soyez en ligne en quelques minutes",
    "bridgeLabel": "Le résultat",
    "bridgeText": "Vous arrêtez de vous noyer dans les tâches répétitives et vous diriger le business que vous seul pouvez diriger.",
    "bridgeHighlight": " plus de 20 heures par semaine",
    "bridgeEnd": " — sans embaucher plus de personnel.",
    "cta": "Commencer gratuitement — sans carte",
    "spAgentsLabel": "Agents déployés cette semaine par des PME",
    "spHoursLabel": "Heures récupérées le mois dernier",
    "spFeed": "Des PME déploient des agents Matrixly en ce moment",
    "trust1": "Exploration gratuite · Annulation à tout moment",
    "trust2": "Fonctionne avec Shopify, Gmail et plus",
    "trust3": "Vos données n’entraînent jamais nos modèles",
    "carouselTitle": "Découvrez votre équipe IA",
    "carouselSub": "Choisissez un agent. Connectez vos outils. Récupérez du temps et du chiffre d’affaires.",
    "live": "En direct"
  },
  "trust": {
    "title": "Se connecte aux outils que les PME utilisent déjà",
    "hoursBack": "Heures récupérées chaque semaine",
    "hoursBackSub": "Moins de tâches répétitives. Plus de temps pour les clients et la croissance.",
    "payback": "Retour sur investissement typique",
    "paybackSub": "Moins cher qu’un temps partiel — disponible 24h/24",
    "minutes": "Jusqu’au premier agent en ligne",
    "minutesSub": "Sans développeurs. Sans long projet de mise en place."
  },
  "howItWorks": {
    "eyebrow": "Comment ça marche",
    "title": "Du travail répétitif au ",
    "titleHighlight": "terminé",
    "sub": "Quatre étapes claires. Pas de consultants. Pas de projet de six mois.",
    "step1Label": "Étape 1",
    "step1Title": "Choisissez vos agents",
    "step1Text": "Sélectionnez les agents qui correspondent au travail qui mange votre semaine — leads, e-mail, support, expéditions, SEO, et plus.",
    "step2Label": "Étape 2",
    "step2Title": "Connectez vos outils",
    "step2Text": "Liez Gmail, Shopify, QuickBooks, CRM ou transporteurs en quelques clics. Vos clés restent chiffrées et privées.",
    "step3Label": "Étape 3",
    "step3Title": "Laissez les agents travailler",
    "step3Text": "Ils rédigent des réponses, qualifient les leads, expédient plus intelligemment et renforcent le SEO local — vous ne validez que ce qui nécessite un humain.",
    "step4Label": "Étape 4",
    "step4Title": "Voyez l’impact",
    "step4Text": "Tableau de bord clair : heures économisées, leads réservés, tickets clos et revenus liés à chaque agent."
  },
  "liveDemo": {
    "eyebrow": "Voyez-le en action",
    "title": "Regardez un agent ",
    "titleHighlight": "traiter un vrai travail",
    "sub": "Tapez une demande ou choisissez un modèle. Simulation légère — sans inscription — pour sentir le produit en quelques secondes.",
    "chipQualify": "Qualifier ce lead",
    "chipShipping": "Rédiger une réponse de retard d’expédition",
    "chipInbox": "Trier ma boîte mail",
    "placeholder": "ex. Qualifier ce lead ou rédiger une réponse de retard…",
    "run": "Lancer la démo",
    "note": "Simulation uniquement · rien n’est envoyé aux clients ni aux outils connectés",
    "cta": "Commencer gratuitement avec cet agent",
    "preview": "Aperçu de l’agent",
    "sim": "simulation en direct",
    "demo": "Démo"
  },
  "useCases": {
    "eyebrow": "Conçu pour les PME du monde entier",
    "title": "Comment des dirigeants comme vous ",
    "titleHighlight": "récupèrent du temps",
    "sub": "Services à domicile, e-commerce, cabinets, artisans et retail — les agents gèrent la routine pour que vous dirigiez l’entreprise.",
    "hvacTitle": "Plus de jobs réservés via la recherche locale",
    "hvacText": "Les agents répondent hors horaires, qualifient les leads web et publient des pages services qui se classent sur les recherches « près de moi » — pour que le téléphone sonne avec les bons jobs.",
    "shopifyTitle": "Expédiez plus vite, vendez plus, répondez moins",
    "shopifyText": "Comparez les tarifs transporteurs, informez les clients avant le « où est ma commande ? » et optimisez les fiches produit — sans recruter en entrepôt.",
    "proTitle": "Boîte mail calme. Pipeline plein.",
    "proText": "Cabinets juridiques, dentaires, consulting et agences locales utilisent des agents pour trier les e-mails, préparer les réunions, garder le CRM propre et relancer les leads avant qu’ils ne refroidissent.",
    "quizCta": "Pas sûr ? Faites le quiz de 60 secondes"
  },
  "quiz": {
    "eyebrow": "Contrôle d’adéquation en 60 secondes",
    "title": "Quels agents correspondent à ",
    "titleHighlight": "votre semaine ?",
    "sub": "Répondez à quelques questions. Nous recommanderons les agents qui vous rendent le plus de temps.",
    "start": "Lancer le quiz",
    "next": "Suivant",
    "back": "Retour",
    "seeResults": "Voir mes agents",
    "retake": "Refaire le quiz"
  },
  "roi": {
    "eyebrow": "Calcul simple",
    "title": "Que valent 20 heures par semaine ",
    "titleHighlight": "pour vous ?",
    "sub": "Les dirigeants sous-estiment souvent le coût de la routine. Entrez vos chiffres — le retour est souvent clair en moins d’une minute.",
    "hoursLabel": "Heures perdues en routine / semaine",
    "rateLabel": "Valeur de votre temps ($/heure)",
    "resultLabel": "Valeur estimée du temps récupéré / mois",
    "cta": "Commencer gratuitement et récupérer ces heures"
  },
  "impact": {
    "title": "Un impact réel pour les dirigeants",
    "sub": "Heures récupérées. Leads traités. Tickets clos. Revenus liés aux agents — pas à plus d’effectifs."
  },
  "agentsTeaser": {
    "eyebrow": "Votre équipe IA",
    "title": "Des agents qui font le travail",
    "sub": "Chaque agent est prêt à se connecter et à tourner. Commencez par un. Ajoutez-en d’autres quand les heures reviennent.",
    "viewAll": "Voir tous les agents"
  },
  "products": {
    "eyebrow": "Suite produit",
    "title": "Tout ce qu’il faut pour ",
    "titleHighlight": "rester lean",
    "sub": "De la qualification de leads aux exceptions d’expédition — un seul endroit pour déployer et gérer votre main-d’œuvre IA."
  },
  "logistics": {
    "title": "Agents d’expédition et de logistique",
    "sub": "Comparez les tarifs, suivez les colis et tenez les clients informés sans vivre dans le portail transporteur."
  },
  "features": {
    "title": "Conçu pour les dirigeants, pas pour les DSI",
    "sub": "Sécurité, confidentialité et contrôles simples — pour que vous restiez aux commandes."
  },
  "compare": {
    "title": "Comment Matrixly se compare",
    "sub": "Pas d’implémentation à six chiffres. Pas d’attente d’un développeur. Juste des agents qui marchent."
  },
  "testimonials": {
    "title": "Ce que disent les dirigeants",
    "sub": "Retours réels de chefs d’entreprise qui ont récupéré leur semaine."
  },
  "guarantee": {
    "title": "Essayez sans risque",
    "sub": "Explorez gratuitement. Annulez à tout moment. Vos données restent les vôtres."
  },
  "pricing": {
    "eyebrow": "Tarifs simples",
    "title": "Des offres qui grandissent avec ",
    "titleHighlight": "votre entreprise",
    "sub": "Commencez gratuitement. Passez à l’offre supérieure quand les agents vous font gagner du temps et de l’argent.",
    "monthly": "Mensuel",
    "yearly": "Annuel",
    "save": "Économisez",
    "popular": "Le plus populaire",
    "cta": "Commencer",
    "contact": "Nous contacter"
  },
  "resources": {
    "eyebrow": "Guides et playbooks",
    "title": "Ressources pratiques pour ",
    "titleHighlight": "dirigeants",
    "sub": "Guides courts et actionnables — setup, ton d’e-mail, SEO local, exceptions d’expédition, et plus."
  },
  "integrations": {
    "eyebrow": "Intégrations",
    "title": "Fonctionne avec les outils que vous ",
    "titleHighlight": "utilisez déjà",
    "sub": "Gmail, Shopify, QuickBooks, CRM, transporteurs, et plus — connectez en quelques minutes."
  },
  "finalCta": {
    "title": "Prêt à récupérer votre temps ?",
    "sub": "Déployez votre premier agent en quelques minutes. Aucune carte requise pour explorer.",
    "cta": "Commencer gratuitement — sans carte"
  },
  "auth": {
    "signIn": "Se connecter",
    "signUp": "S’inscrire",
    "email": "E-mail",
    "password": "Mot de passe",
    "forgot": "Mot de passe oublié ?",
    "noAccount": "Pas encore de compte ?",
    "hasAccount": "Déjà un compte ?"
  },
  "footer": {
    "product": "Produit",
    "company": "Entreprise",
    "resources": "Ressources",
    "legal": "Mentions légales",
    "privacy": "Confidentialité",
    "terms": "Conditions",
    "contact": "Contact",
    "tagline": "Agents IA pour PME — en ligne en quelques minutes, sans équipe technique."
  },
  "common": {
    "learnMore": "En savoir plus",
    "getStarted": "Commencer",
    "tryFree": "Essayer gratuitement",
    "loading": "Chargement…",
    "error": "Une erreur s’est produite. Réessayez.",
    "close": "Fermer",
    "save": "Enregistrer",
    "cancel": "Annuler",
    "continue": "Continuer",
    "back": "Retour",
    "next": "Suivant",
    "submit": "Envoyer",
    "language": "Langue",
    "selectLanguage": "Choisir la langue"
  }
}

AR = {
  "meta": {"lang": "ar", "dir": "rtl", "name": "Arabic", "nativeName": "العربية"},
  "nav": {
    "howItWorks": "كيف يعمل",
    "agents": "الوكلاء",
    "resources": "الموارد",
    "integrations": "التكاملات",
    "pricing": "الأسعار",
    "getStarted": "ابدأ الآن",
    "toggleMenu": "فتح أو إغلاق القائمة",
    "switchTheme": "تبديل الوضع الفاتح / الداكن"
  },
  "hero": {
    "badge": "مبني للشركات الصغيرة · بلا فريق تقني",
    "headline1": "مهارات وأنظمة على مستوى المؤسسات — ",
    "headline2": "مصممة لطريقة عمل الشركات الصغيرة فعليًا.",
    "sub1": "الشركات الكبيرة لديها فرق متخصصة وأدلة عمل مجرّبة وأدوات قوية. معظم أصحاب الشركات الصغيرة يرتدون كل القبعات ويتأخرون مع ذلك عن العمل الذي لا يتوقف — العملاء المحتملون، البريد، الدعم، الشحن، الفوترة وتحسين محركات البحث المحلي.",
    "sub1Highlight": " أكثر من 20 ساعة أسبوعيًا",
    "sub1End": " في ذلك — ويتراكم كل ربع سنة دون حل.",
    "sub2Start": "ماتريكسلي تسد هذه الفجوة.",
    "sub2": " نأخذ الخبرة والعمليات والقدرات التي كانت حكرًا على المؤسسات الكبيرة ونقدمها كوكلاء ذكاء اصطناعي جاهزين للتشغيل، مصممين خصيصًا لطريقة عمل الشركات الصغيرة يوميًا. بلا مطورين. بلا مشاريع تنفيذ طويلة. بلا أسعار المؤسسات.",
    "beforeLabel": "ما الذي تحصل عليه فعليًا",
    "beforeText": "قدرة بمستوى المؤسسات — نفس جودة الأنظمة والخبرة التي تعتمد عليها الشركات الأكبر",
    "afterLabel": "تسليم بسيط للشركات الصغيرة",
    "afterText": "اختر وكيلًا، اربط الأدوات التي تستخدمها بالفعل، وانطلق خلال دقائق",
    "bridgeLabel": "النتيجة",
    "bridgeText": "تتوقف عن الغرق في الأعمال الروتينية وتبدأ في إدارة العمل الذي أنت وحدك تستطيع قيادته.",
    "bridgeHighlight": " أكثر من 20 ساعة أسبوعيًا",
    "bridgeEnd": " — دون توظيف المزيد من الموظفين.",
    "cta": "ابدأ مجانًا — بلا بطاقة",
    "spAgentsLabel": "وكلاء نُشروا هذا الأسبوع لدى الشركات الصغيرة",
    "spHoursLabel": "ساعات استُعيدت الشهر الماضي",
    "spFeed": "شركات صغيرة تنشر وكلاء ماتريكسلي الآن",
    "trust1": "استكشف مجانًا · ألغِ في أي وقت",
    "trust2": "يعمل مع Shopify وGmail والمزيد",
    "trust3": "بياناتك لا تدرّب نماذجنا أبدًا",
    "carouselTitle": "تعرّف على فريق الذكاء الاصطناعي",
    "carouselSub": "اختر وكيلًا. اربط أدواتك. استعد الوقت والإيرادات.",
    "live": "مباشر"
  },
  "trust": {
    "title": "يتصل بالأدوات التي تستخدمها الشركات الصغيرة بالفعل",
    "hoursBack": "ساعات تعود إليك كل أسبوع",
    "hoursBackSub": "أعمال روتينية أقل. وقت أكثر للعملاء والنمو.",
    "payback": "استرداد نموذجي للتكلفة",
    "paybackSub": "أرخص من موظف بدوام جزئي — يعمل على مدار الساعة",
    "minutes": "حتى يعمل أول وكيل",
    "minutesSub": "بلا مطورين. بلا مشروع إعداد طويل."
  },
  "howItWorks": {
    "eyebrow": "كيف يعمل",
    "title": "من الأعمال الروتينية إلى ",
    "titleHighlight": "منجز",
    "sub": "أربع خطوات واضحة. بلا مستشارين. بلا مشروع لستة أشهر.",
    "step1Label": "الخطوة 1",
    "step1Title": "اختر وكلاءك",
    "step1Text": "اختر الوكلاء الذين يغطون العمل الذي يستهلك أسبوعك — العملاء المحتملون، البريد، الدعم، الشحن، تحسين محركات البحث والمزيد.",
    "step2Label": "الخطوة 2",
    "step2Title": "اربط أدواتك",
    "step2Text": "اربط Gmail أو Shopify أو QuickBooks أو CRM أو شركات الشحن بنقرات قليلة. مفاتيحك تبقى مشفّرة وخاصة.",
    "step3Label": "الخطوة 3",
    "step3Title": "دع الوكلاء يعملون",
    "step3Text": "يصوغون الردود ويؤهلون العملاء المحتملين ويشحنون بذكاء ويعززون البحث المحلي — وأنت تراجع فقط ما يحتاج إنسانًا.",
    "step4Label": "الخطوة 4",
    "step4Title": "شاهد الأثر",
    "step4Text": "لوحة واضحة: ساعات موفّرة، عملاء محتملون محجوزون، تذاكر مغلقة وإيرادات مرتبطة بكل وكيل."
  },
  "liveDemo": {
    "eyebrow": "شاهده يعمل",
    "title": "راقب وكيلًا ",
    "titleHighlight": "ينجز عملًا حقيقيًا",
    "sub": "اكتب طلبًا أو اختر قالبًا. محاكاة خفيفة — بلا تسجيل — لتشعر بالمنتج في ثوانٍ.",
    "chipQualify": "تأهيل هذا العميل المحتمل",
    "chipShipping": "صياغة رد لتأخير الشحن",
    "chipInbox": "فرز بريدي الوارد",
    "placeholder": "مثال: تأهيل هذا العميل أو صياغة رد تأخير…",
    "run": "تشغيل العرض",
    "note": "محاكاة فقط · لا يُرسل شيء للعملاء أو الأدوات المتصلة",
    "cta": "ابدأ مجانًا مع هذا الوكيل",
    "preview": "معاينة الوكيل",
    "sim": "محاكاة مباشرة",
    "demo": "عرض"
  },
  "useCases": {
    "eyebrow": "مبني للشركات الصغيرة والمتوسطة عالميًا",
    "title": "كيف يستعيد أصحاب الأعمال مثلك ",
    "titleHighlight": "وقتهم",
    "sub": "خدمات منزلية، تجارة إلكترونية، مكاتب مهنية، مقاولون وتجزئة — الوكلاء يتولون الروتين لتدير أنت العمل.",
    "hvacTitle": "المزيد من الحجوزات من البحث المحلي",
    "hvacText": "الوكلاء يردون خارج الدوام، يؤهلون زوار الموقع وينشرون صفحات خدمات تترتب في بحث «قربي» — ليرن الهاتف بالوظائف الصحيحة.",
    "shopifyTitle": "اشحن أسرع، بِع أكثر، أجب أقل",
    "shopifyText": "قارن أسعار الشحن، حدّث العملاء قبل سؤال «أين طلبي؟» وحسّن نصوص المنتجات — بلا موظفين إضافيين في المستودع.",
    "proTitle": "بريد هادئ. خط مبيعات ممتلئ.",
    "proText": "مكاتب قانونية وطبية واستشارية ووكالات محلية تستخدم الوكلاء لفرز البريد وتحضير الاجتماعات والحفاظ على CRM ومتابعة العملاء المحتملين قبل أن يبردوا.",
    "quizCta": "لست متأكدًا؟ خذ اختبار 60 ثانية"
  },
  "quiz": {
    "eyebrow": "فحص ملاءمة في 60 ثانية",
    "title": "أي الوكلاء يناسب ",
    "titleHighlight": "أسبوعك؟",
    "sub": "أجب عن بضعة أسئلة. سنوصي بالوكلاء الذين يعيدون لك أكبر قدر من الوقت.",
    "start": "ابدأ الاختبار",
    "next": "التالي",
    "back": "رجوع",
    "seeResults": "عرض وكلائي",
    "retake": "أعد الاختبار"
  },
  "roi": {
    "eyebrow": "حساب بسيط",
    "title": "كم تساوي 20 ساعة أسبوعيًا ",
    "titleHighlight": "بالنسبة لك؟",
    "sub": "كثير من الملاك يقلّلون من تكلفة الأعمال الروتينية. أدخل أرقامك — غالبًا يتضح العائد في أقل من دقيقة.",
    "hoursLabel": "ساعات ضائعة في الروتين / أسبوع",
    "rateLabel": "قيمة وقتك ($/ساعة)",
    "resultLabel": "القيمة المقدّرة للوقت المستعاد / شهر",
    "cta": "ابدأ مجانًا واستعد تلك الساعات"
  },
  "impact": {
    "title": "أثر حقيقي لأصحاب الأعمال",
    "sub": "ساعات تعود. عملاء محتملون يُجابون. تذاكر تُغلق. إيرادات مرتبطة بالوكلاء — لا بمزيد من التوظيف."
  },
  "agentsTeaser": {
    "eyebrow": "فريق الذكاء الاصطناعي لديك",
    "title": "وكلاء ينجزون العمل",
    "sub": "كل وكيل جاهز للربط والتشغيل. ابدأ بواحد. أضف المزيد عندما ترى الساعات تعود.",
    "viewAll": "عرض كل الوكلاء"
  },
  "products": {
    "eyebrow": "مجموعة المنتجات",
    "title": "كل ما تحتاجه لـ",
    "titleHighlight": "العمل بكفاءة",
    "sub": "من تأهيل العملاء المحتملين إلى استثناءات الشحن — مكان واحد لنشر وإدارة قوتك العاملة بالذكاء الاصطناعي."
  },
  "logistics": {
    "title": "وكلاء الشحن واللوجستيات",
    "sub": "قارن الأسعار وتتبع الطرود وأبقِ العملاء على اطلاع دون أن تعيش في بوابة شركة الشحن."
  },
  "features": {
    "title": "مبني للملاك لا لأقسام تقنية المعلومات",
    "sub": "أمان وخصوصية وضوابط بسيطة — لتبقى أنت المتحكم."
  },
  "compare": {
    "title": "كيف تقارن ماتريكسلي",
    "sub": "بلا تنفيذ بمئات الآلاف. بلا انتظار مطور. فقط وكلاء يعملون."
  },
  "testimonials": {
    "title": "ماذا يقول الملاك",
    "sub": "آراء حقيقية من أصحاب أعمال صغيرة استعادوا أسبوعهم."
  },
  "guarantee": {
    "title": "جرّبه بلا مخاطرة",
    "sub": "استكشف مجانًا. ألغِ في أي وقت. بياناتك تبقى لك."
  },
  "pricing": {
    "eyebrow": "أسعار بسيطة",
    "title": "خطط تنمو مع ",
    "titleHighlight": "عملك",
    "sub": "ابدأ مجانًا. رقِّ الخطة عندما يوفر لك الوكلاء الوقت والمال.",
    "monthly": "شهري",
    "yearly": "سنوي",
    "save": "وفّر",
    "popular": "الأكثر شيوعًا",
    "cta": "ابدأ",
    "contact": "تحدث معنا"
  },
  "resources": {
    "eyebrow": "أدلة وخطط عمل",
    "title": "موارد عملية لـ",
    "titleHighlight": "الملاك",
    "sub": "أدلة قصيرة قابلة للتنفيذ — الإعداد، نبرة البريد، SEO المحلي، استثناءات الشحن والمزيد."
  },
  "integrations": {
    "eyebrow": "التكاملات",
    "title": "يعمل مع الأدوات التي ",
    "titleHighlight": "تستخدمها بالفعل",
    "sub": "Gmail وShopify وQuickBooks وأنظمة CRM وشركات الشحن والمزيد — اربطها في دقائق."
  },
  "finalCta": {
    "title": "هل أنت مستعد لاستعادة وقتك؟",
    "sub": "انشر أول وكيل خلال دقائق. بلا بطاقة للاستكشاف.",
    "cta": "ابدأ مجانًا — بلا بطاقة"
  },
  "auth": {
    "signIn": "تسجيل الدخول",
    "signUp": "إنشاء حساب",
    "email": "البريد الإلكتروني",
    "password": "كلمة المرور",
    "forgot": "نسيت كلمة المرور؟",
    "noAccount": "ليس لديك حساب؟",
    "hasAccount": "لديك حساب بالفعل؟"
  },
  "footer": {
    "product": "المنتج",
    "company": "الشركة",
    "resources": "الموارد",
    "legal": "قانوني",
    "privacy": "الخصوصية",
    "terms": "الشروط",
    "contact": "اتصل بنا",
    "tagline": "وكلاء ذكاء اصطناعي للشركات الصغيرة والمتوسطة — يعملون خلال دقائق بلا فريق تقني."
  },
  "common": {
    "learnMore": "اعرف المزيد",
    "getStarted": "ابدأ الآن",
    "tryFree": "جرّب مجانًا",
    "loading": "جارٍ التحميل…",
    "error": "حدث خطأ. حاول مرة أخرى.",
    "close": "إغلاق",
    "save": "حفظ",
    "cancel": "إلغاء",
    "continue": "متابعة",
    "back": "رجوع",
    "next": "التالي",
    "submit": "إرسال",
    "language": "اللغة",
    "selectLanguage": "اختر اللغة"
  }
}

BN = {
  "meta": {"lang": "bn", "dir": "ltr", "name": "Bengali", "nativeName": "বাংলা"},
  "nav": {
    "howItWorks": "কীভাবে কাজ করে",
    "agents": "এজেন্ট",
    "resources": "রিসোর্স",
    "integrations": "ইন্টিগ্রেশন",
    "pricing": "মূল্য",
    "getStarted": "শুরু করুন",
    "toggleMenu": "মেনু খুলুন বা বন্ধ করুন",
    "switchTheme": "লাইট / ডার্ক থিম টগল"
  },
  "hero": {
    "badge": "ছোট ব্যবসার জন্য · কোনো টেক টিম লাগে না",
    "headline1": "এন্টারপ্রাইজ দক্ষতা ও সিস্টেম — ",
    "headline2": "ছোট ব্যবসা সত্যিই যেভাবে চলে, সেভাবে তৈরি।",
    "sub1": "বড় কোম্পানির আছে বিশেষায়িত টিম, প্রমাণিত প্লেবুক ও শক্তিশালী টুল। বেশিরভাগ ছোট ব্যবসার মালিক সব টুপি পরেও পিছিয়ে পড়েন—লিড, ইমেইল, সাপোর্ট, শিপিং, ইনভয়েস আর লোকাল SEO-এর কাজ থামে না।",
    "sub1Highlight": " সপ্তাহে ২০+ ঘণ্টা",
    "sub1End": " এতেই নষ্ট হয় — আর প্রতি কোয়ার্টারে জমে যায় যদি ঠিক না করেন।",
    "sub2Start": "Matrixly সেই ফাঁক ভরাট করে।",
    "sub2": " আমরা সেই দক্ষতা, প্রক্রিয়া ও সক্ষমতা নিয়ে আসি যা আগে শুধু বড় সংস্থার ছিল, আর প্যাকেজ করি রেডি-টু-রান AI এজেন্ট হিসেবে—SMB-এর দৈনন্দিন কাজের মতো করে। ডেভেলপার লাগে না। দীর্ঘ ইমপ্লিমেন্টেশন নয়। এন্টারপ্রাইজ দাম নয়।",
    "beforeLabel": "আসলে যা পাবেন",
    "beforeText": "এন্টারপ্রাইজ-গ্রেড সক্ষমতা — বড় কোম্পানি যে মানের সিস্টেম ও জ্ঞান ব্যবহার করে",
    "afterLabel": "SMB-সহজ ডেলিভারি",
    "afterText": "একটি এজেন্ট বেছে নিন, যে টুল আগেই ব্যবহার করেন সেগুলো সংযুক্ত করুন, মিনিটে লাইভ হন",
    "bridgeLabel": "ফলাফল",
    "bridgeText": "ব্যস্ত কাজের ভিড়ে ডুববেন না—শুধু আপনিই চালাতে পারেন সেই ব্যবসা চালান।",
    "bridgeHighlight": " সপ্তাহে ২০+ ঘণ্টা",
    "bridgeEnd": " — অতিরিক্ত স্টাফ ছাড়াই।",
    "cta": "বিনামূল্যে শুরু — কার্ড লাগে না",
    "spAgentsLabel": "এই সপ্তাহে SMB-এর ডিপ্লয় করা এজেন্ট",
    "spHoursLabel": "গতমাসে ফিরে পাওয়া ঘণ্টা",
    "spFeed": "ছোট ব্যবসা এখনই Matrixly এজেন্ট ডিপ্লয় করছে",
    "trust1": "বিনামূল্যে দেখুন · যেকোনো সময় বাতিল",
    "trust2": "Shopify, Gmail ও আরও অনেকের সাথে কাজ করে",
    "trust3": "আপনার ডেটা কখনো আমাদের মডেল ট্রেন করে না",
    "carouselTitle": "আপনার AI টিমের সাথে পরিচিত হন",
    "carouselSub": "এজেন্ট বেছে নিন। টুল সংযুক্ত করুন। সময় ও আয় ফিরে পান।",
    "live": "লাইভ"
  },
  "trust": {
    "title": "ছোট ব্যবসা ইতিমধ্যে যে টুল ব্যবহার করে, সেগুলোর সাথে সংযুক্ত",
    "hoursBack": "প্রতি সপ্তাহে ফিরে পাওয়া ঘণ্টা",
    "hoursBackSub": "কম ব্যস্ত কাজ। গ্রাহক ও বৃদ্ধির জন্য বেশি সময়।",
    "payback": "সাধারণ পেব্যাক",
    "paybackSub": "পার্ট-টাইম নিয়োগের চেয়ে সস্তা — ২৪/৭ কাজ করে",
    "minutes": "প্রথম এজেন্ট লাইভ হতে",
    "minutesSub": "ডেভেলপার নেই। দীর্ঘ সেটআপ প্রজেক্ট নেই।"
  },
  "howItWorks": {
    "eyebrow": "কীভাবে কাজ করে",
    "title": "ব্যস্ত কাজ থেকে ",
    "titleHighlight": "সম্পন্ন",
    "sub": "চারটি স্পষ্ট ধাপ। কোনো কনসালট্যান্ট নয়। ছয় মাসের প্রজেক্ট নয়।",
    "step1Label": "ধাপ ১",
    "step1Title": "এজেন্ট বেছে নিন",
    "step1Text": "যে কাজ আপনার সপ্তাহ খেয়ে ফেলে—লিড, ইমেইল, সাপোর্ট, শিপিং, SEO—সেই মতো এজেন্ট বেছে নিন।",
    "step2Label": "ধাপ ২",
    "step2Title": "টুল সংযুক্ত করুন",
    "step2Text": "কয়েক ক্লিকে Gmail, Shopify, QuickBooks, CRM বা ক্যারিয়ার লিঙ্ক করুন। আপনার কী এনক্রিপ্টেড ও ব্যক্তিগত থাকে।",
    "step3Label": "ধাপ ৩",
    "step3Title": "এজেন্টকে কাজ করতে দিন",
    "step3Text": "তারা উত্তর ড্রাফট করে, লিড কোয়ালিফাই করে, স্মার্ট শিপ করে এবং লোকাল সার্চ বাড়ায়—মানুষের দরকার এমনটাই আপনি রিভিউ করেন।",
    "step4Label": "ধাপ ৪",
    "step4Title": "প্রভাব দেখুন",
    "step4Text": "স্পষ্ট ড্যাশবোর্ড: বাঁচানো ঘণ্টা, বুক করা লিড, বন্ধ টিকিট এবং প্রতি এজেন্টের রাজস্ব।"
  },
  "liveDemo": {
    "eyebrow": "কাজ দেখুন",
    "title": "দেখুন এজেন্ট ",
    "titleHighlight": "আসল কাজ করে",
    "sub": "একটি অনুরোধ টাইপ করুন বা প্রিসেট চাপুন। হালকা সিমুলেশন — সাইনআপ লাগে না — সেকেন্ডে প্রোডাক্ট অনুভব করুন।",
    "chipQualify": "এই লিড কোয়ালিফাই করুন",
    "chipShipping": "শিপিং দেরির উত্তর ড্রাফট",
    "chipInbox": "ইনবক্স ট্রায়াজ",
    "placeholder": "যেমন: এই লিড কোয়ালিফাই বা দেরির উত্তর ড্রাফট…",
    "run": "ডেমো চালান",
    "note": "শুধু সিমুলেশন · গ্রাহক বা সংযুক্ত টুলে কিছু পাঠানো হয় না",
    "cta": "এই এজেন্ট দিয়ে বিনামূল্যে শুরু",
    "preview": "এজেন্ট প্রিভিউ",
    "sim": "লাইভ সিমুলেশন",
    "demo": "ডেমো"
  },
  "useCases": {
    "eyebrow": "বিশ্বব্যাপী ছোট ও মাঝারি ব্যবসার জন্য",
    "title": "আপনার মতো মালিকরা ",
    "titleHighlight": "সময় ফিরে পান",
    "sub": "হোম সার্ভিস, ই-কমার্স, পেশাদার ফার্ম, কন্ট্রাক্টর ও রিটেইল—এজেন্ট ব্যস্ত কাজ সামলায় যাতে আপনি ব্যবসা চালান।",
    "hvacTitle": "লোকাল সার্চ থেকে বেশি বুক করা জব",
    "hvacText": "এজেন্ট অফিস-আওয়ারের বাইরে জবাব দেয়, ওয়েব লিড কোয়ালিফাই করে এবং “কাছাকাছি” সার্চে র‍্যাঙ্ক করা সার্ভিস পেজ প্রকাশ করে—সঠিক জবের ফোন বাজে।",
    "shopifyTitle": "দ্রুত শিপ, বেশি বিক্রি, কম উত্তর",
    "shopifyText": "ক্যারিয়ার রেট তুলনা, গ্রাহককে “অর্ডার কোথায়?” জিজ্ঞাসার আগে আপডেট, প্রোডাক্ট কপি অপটিমাইজ—অতিরিক্ত ওয়্যারহাউস স্টাফ ছাড়াই।",
    "proTitle": "ইনবক্স শান্ত। পাইপলাইন পূর্ণ।",
    "proText": "লিগ্যাল, ডেন্টাল, কনসাল্টিং ও লোকাল এজেন্সি এজেন্ট দিয়ে ইমেইল ট্রায়াজ, মিটিং প্রিপ, CRM পরিষ্কার এবং লিড ঠান্ডা হওয়ার আগে ফলো-আপ করে।",
    "quizCta": "নিশ্চিত নন? ৬০ সেকেন্ডের কুইজ নিন"
  },
  "quiz": {
    "eyebrow": "৬০ সেকেন্ডের ফিট চেক",
    "title": "কোন এজেন্ট মানায় ",
    "titleHighlight": "আপনার সপ্তাহে?",
    "sub": "কয়েকটি প্রশ্নের উত্তর দিন। আমরা এমন এজেন্ট সাজেস্ট করব যা সবচেয়ে বেশি সময় ফেরত দেয়।",
    "start": "কুইজ শুরু",
    "next": "পরবর্তী",
    "back": "পিছনে",
    "seeResults": "আমার এজেন্ট দেখুন",
    "retake": "আবার কুইজ"
  },
  "roi": {
    "eyebrow": "সহজ হিসাব",
    "title": "সপ্তাহে ২০ ঘণ্টা ",
    "titleHighlight": "আপনার কাছে কত?",
    "sub": "মালিকরা প্রায়ই ব্যস্ত কাজের খরচ কম দেখেন। সংখ্যা দিন—সাধারণত এক মিনিটের মধ্যে পেব্যাক স্পষ্ট।",
    "hoursLabel": "ব্যস্ত কাজে নষ্ট ঘণ্টা / সপ্তাহ",
    "rateLabel": "আপনার সময়ের মূল্য ($/ঘণ্টা)",
    "resultLabel": "ফিরে পাওয়া সময়ের আনুমানিক মূল্য / মাস",
    "cta": "বিনামূল্যে শুরু করে সেই ঘণ্টা ফিরে নিন"
  },
  "impact": {
    "title": "মালিকদের জন্য বাস্তব প্রভাব",
    "sub": "ঘণ্টা ফেরত। লিডের উত্তর। টিকিট বন্ধ। এজেন্টের সাথে রাজস্ব—অতিরিক্ত হেডকাউন্ট নয়।"
  },
  "agentsTeaser": {
    "eyebrow": "আপনার AI টিম",
    "title": "যে এজেন্ট কাজ করে",
    "sub": "প্রতিটি এজেন্ট সংযুক্ত ও চালু হতে প্রস্তুত। এক দিয়ে শুরু করুন। ঘণ্টা ফিরতে দেখে আরও যোগ করুন।",
    "viewAll": "সব এজেন্ট দেখুন"
  },
  "products": {
    "eyebrow": "প্রোডাক্ট স্যুট",
    "title": "যা দরকার ",
    "titleHighlight": "হালকাভাবে চালাতে",
    "sub": "লিড কোয়ালিফিকেশন থেকে শিপিং এক্সেপশন—এক জায়গায় AI ওয়ার্কফোর্স ডিপ্লয় ও ম্যানেজ।"
  },
  "logistics": {
    "title": "শিপিং ও লজিস্টিকস এজেন্ট",
    "sub": "রেট তুলনা, ট্র্যাক এবং গ্রাহককে আপডেট রাখুন—ক্যারিয়ার পোর্টালে না থেকে।"
  },
  "features": {
    "title": "মালিকদের জন্য, IT বিভাগের জন্য নয়",
    "sub": "নিরাপত্তা, প্রাইভেসি ও সহজ নিয়ন্ত্রণ—আপনিই নিয়ন্ত্রণে থাকবেন।"
  },
  "compare": {
    "title": "Matrixly কীভাবে তুলনা করে",
    "sub": "ছয় অঙ্কের ইমপ্লিমেন্টেশন নয়। ডেভেলপারের অপেক্ষা নয়। শুধু কাজ করে এমন এজেন্ট।"
  },
  "testimonials": {
    "title": "মালিকরা কী বলেন",
    "sub": "যারা সপ্তাহ ফিরে পেয়েছেন, তাদের বাস্তব মতামত।"
  },
  "guarantee": {
    "title": "ঝুঁকি ছাড়া চেষ্টা করুন",
    "sub": "বিনামূল্যে দেখুন। যেকোনো সময় বাতিল। আপনার ডেটা আপনারই।"
  },
  "pricing": {
    "eyebrow": "সহজ মূল্য",
    "title": "যে প্ল্যান বাড়ে ",
    "titleHighlight": "আপনার ব্যবসার সাথে",
    "sub": "বিনামূল্যে শুরু। এজেন্ট সময় ও টাকা বাঁচাতে শুরু করলে আপগ্রেড করুন।",
    "monthly": "মাসিক",
    "yearly": "বার্ষিক",
    "save": "সাশ্রয়",
    "popular": "সবচেয়ে জনপ্রিয়",
    "cta": "শুরু করুন",
    "contact": "আমাদের সাথে কথা বলুন"
  },
  "resources": {
    "eyebrow": "গাইড ও প্লেবুক",
    "title": "ব্যবহারযোগ্য রিসোর্স ",
    "titleHighlight": "মালিকদের জন্য",
    "sub": "ছোট, কার্যকর গাইড—সেটআপ, ইমেইল ভয়েস, লোকাল SEO, শিপিং এক্সেপশন এবং আরও।"
  },
  "integrations": {
    "eyebrow": "ইন্টিগ্রেশন",
    "title": "যে টুল আপনি ",
    "titleHighlight": "ইতিমধ্যে ব্যবহার করেন",
    "sub": "Gmail, Shopify, QuickBooks, CRM, ক্যারিয়ার ও আরও—মিনিটে সংযুক্ত।"
  },
  "finalCta": {
    "title": "সময় ফিরে পেতে প্রস্তুত?",
    "sub": "মিনিটে প্রথম এজেন্ট ডিপ্লয় করুন। এক্সপ্লোর করতে কার্ড লাগে না।",
    "cta": "বিনামূল্যে শুরু — কার্ড লাগে না"
  },
  "auth": {
    "signIn": "সাইন ইন",
    "signUp": "সাইন আপ",
    "email": "ইমেইল",
    "password": "পাসওয়ার্ড",
    "forgot": "পাসওয়ার্ড ভুলে গেছেন?",
    "noAccount": "অ্যাকাউন্ট নেই?",
    "hasAccount": "ইতিমধ্যে অ্যাকাউন্ট আছে?"
  },
  "footer": {
    "product": "প্রোডাক্ট",
    "company": "কোম্পানি",
    "resources": "রিসোর্স",
    "legal": "আইনি",
    "privacy": "গোপনীয়তা",
    "terms": "শর্তাবলী",
    "contact": "যোগাযোগ",
    "tagline": "ছোট ও মাঝারি ব্যবসার জন্য AI এজেন্ট — মিনিটে লাইভ, টেক টিম ছাড়া।"
  },
  "common": {
    "learnMore": "আরও জানুন",
    "getStarted": "শুরু করুন",
    "tryFree": "বিনামূল্যে চেষ্টা",
    "loading": "লোড হচ্ছে…",
    "error": "কিছু ভুল হয়েছে। আবার চেষ্টা করুন।",
    "close": "বন্ধ",
    "save": "সংরক্ষণ",
    "cancel": "বাতিল",
    "continue": "চালিয়ে যান",
    "back": "পিছনে",
    "next": "পরবর্তী",
    "submit": "জমা দিন",
    "language": "ভাষা",
    "selectLanguage": "ভাষা নির্বাচন"
  }
}

DE = {
  "meta": {"lang": "de", "dir": "ltr", "name": "German", "nativeName": "Deutsch"},
  "nav": {
    "howItWorks": "So funktioniert's",
    "agents": "Agenten",
    "resources": "Ressourcen",
    "integrations": "Integrationen",
    "pricing": "Preise",
    "getStarted": "Loslegen",
    "toggleMenu": "Menü umschalten",
    "switchTheme": "Hell-/Dunkelmodus umschalten"
  },
  "hero": {
    "badge": "Für kleine und mittlere Unternehmen · Kein Tech-Team nötig",
    "headline1": "Enterprise-Fähigkeiten und -Systeme — ",
    "headline2": "gebaut für die Art, wie KMUs wirklich arbeiten.",
    "sub1": "Größere Unternehmen haben spezialisierte Teams, bewährte Playbooks und starke Tools. Die meisten Inhaber kleiner Betriebe tragen jede Rolle und hinken trotzdem hinter der Arbeit hinterher, die nie aufhört — Leads, E-Mail, Support, Versand, Rechnungen und lokales SEO.",
    "sub1Highlight": " über 20 Stunden pro Woche",
    "sub1End": " damit — und das summiert sich jedes Quartal, in dem Sie nichts ändern.",
    "sub2Start": "Matrixly schließt diese Lücke.",
    "sub2": " Wir nehmen Expertise, Prozesse und Fähigkeiten, die früher großen Organisationen vorbehalten waren, und packen sie als einsatzbereite KI-Agenten — zugeschnitten auf den Alltag von KMUs. Keine Entwickler. Keine langen Implementierungen. Kein Enterprise-Preisschild.",
    "beforeLabel": "Was Sie wirklich bekommen",
    "beforeText": "Enterprise-Qualität — dieselbe System- und Know-how-Qualität, auf die größere Unternehmen setzen",
    "afterLabel": "SMB-einfache Bereitstellung",
    "afterText": "Agent wählen, Tools verbinden, die Sie schon nutzen, und in Minuten live gehen",
    "bridgeLabel": "Das Ergebnis",
    "bridgeText": "Sie hören auf, in Routinearbeit zu ertrinken, und führen das Geschäft, das nur Sie führen können.",
    "bridgeHighlight": " über 20 Stunden pro Woche",
    "bridgeEnd": " — ohne mehr Personal einzustellen.",
    "cta": "Kostenlos starten — keine Karte nötig",
    "spAgentsLabel": "Diese Woche von KMUs eingesetzte Agenten",
    "spHoursLabel": "Im letzten Monat zurückgewonnene Stunden",
    "spFeed": "Kleine und mittlere Unternehmen setzen gerade Matrixly-Agenten ein",
    "trust1": "Kostenlos testen · Jederzeit kündbar",
    "trust2": "Funktioniert mit Shopify, Gmail & mehr",
    "trust3": "Ihre Daten trainieren nie unsere Modelle",
    "carouselTitle": "Lernen Sie Ihr KI-Team kennen",
    "carouselSub": "Agenten auswählen. Tools verbinden. Zeit und Umsatz zurückgewinnen.",
    "live": "Live"
  },
  "trust": {
    "title": "Verbindet sich mit den Tools, die KMUs bereits nutzen",
    "hoursBack": "Stunden zurück jede Woche",
    "hoursBackSub": "Weniger Routine. Mehr Zeit für Kunden und Wachstum.",
    "payback": "Typische Amortisation",
    "paybackSub": "Günstiger als eine Teilzeitkraft — arbeitet 24/7",
    "minutes": "Bis zum ersten Agenten live",
    "minutesSub": "Keine Entwickler. Kein monatelanges Projekt."
  },
  "howItWorks": {
    "eyebrow": "So funktioniert's",
    "title": "Von Routinearbeit zu ",
    "titleHighlight": "erledigt",
    "sub": "Vier klare Schritte. Keine Berater. Kein Sechs-Monats-Projekt.",
    "step1Label": "Schritt 1",
    "step1Title": "Agenten auswählen",
    "step1Text": "Wählen Sie die Agenten, die zu der Arbeit passen, die Ihre Woche frisst — Leads, E-Mail, Support, Versand, SEO und mehr.",
    "step2Label": "Schritt 2",
    "step2Title": "Tools verbinden",
    "step2Text": "Verknüpfen Sie Gmail, Shopify, QuickBooks, CRM oder Versanddienstleister mit wenigen Klicks. Ihre Schlüssel bleiben verschlüsselt und privat.",
    "step3Label": "Schritt 3",
    "step3Title": "Agenten arbeiten lassen",
    "step3Text": "Sie entwerfen Antworten, qualifizieren Leads, optimieren den Versand und stärken lokales SEO — Sie prüfen nur, was einen Menschen braucht.",
    "step4Label": "Schritt 4",
    "step4Title": "Wirkung sehen",
    "step4Text": "Klares Dashboard: eingesparte Stunden, gebuchte Leads, geschlossene Tickets und Umsatz pro Agent."
  },
  "liveDemo": {
    "eyebrow": "In Aktion sehen",
    "title": "Sehen Sie zu, wie ein Agent ",
    "titleHighlight": "echte Arbeit erledigt",
    "sub": "Tippen Sie eine Anfrage oder wählen Sie eine Vorlage. Das ist eine leichte Simulation — keine Anmeldung nötig — damit Sie das Produkt in Sekunden spüren.",
    "chipQualify": "Diesen Lead qualifizieren",
    "chipShipping": "Antwort bei Versandverzögerung entwerfen",
    "chipInbox": "Mein Posteingang sortieren",
    "placeholder": "z. B. Lead qualifizieren oder Verzögerungsantwort entwerfen…",
    "run": "Demo starten",
    "note": "Nur Simulation · nichts wird an Kunden oder verbundene Tools gesendet",
    "cta": "Kostenlos mit diesem Agenten starten",
    "preview": "Agentenvorschau",
    "sim": "Live-Simulation",
    "demo": "Demo"
  },
  "useCases": {
    "eyebrow": "Für globale kleine und mittlere Unternehmen gebaut",
    "title": "So gewinnen Inhaber wie Sie ",
    "titleHighlight": "Zeit zurück",
    "sub": "Handwerksbetriebe, E-Commerce, professionelle Dienstleister, Bauunternehmer und Einzelhandel — Agenten übernehmen die Routine, damit Sie das Geschäft führen können.",
    "hvacTitle": "Mehr gebuchte Aufträge durch lokale Suche",
    "hvacText": "Agenten beantworten Anfragen außerhalb der Geschäftszeiten, qualifizieren Web-Leads und veröffentlichen Service-Seiten, die bei „in meiner Nähe“-Suchen ranken — damit das Telefon mit den richtigen Aufträgen klingelt.",
    "shopifyTitle": "Schneller versenden, mehr verkaufen, weniger antworten",
    "shopifyText": "Tarife vergleichen, Kunden aktualisieren, bevor sie fragen „Wo ist meine Bestellung?“, und Produkttexte optimieren — ohne zusätzliches Lagerpersonal.",
    "proTitle": "Ruhiger Posteingang. Volle Pipeline.",
    "proText": "Kanzleien, Praxen, Beratungen und lokale Agenturen nutzen Agenten, um E-Mails zu sortieren, Meetings vorzubereiten, das CRM sauber zu halten und Leads nachzuverfolgen, bevor sie abkühlen.",
    "quizCta": "Unsicher? Machen Sie den 60-Sekunden-Quiz"
  },
  "quiz": {
    "eyebrow": "60-Sekunden-Passungscheck",
    "title": "Welche Agenten passen zu ",
    "titleHighlight": "Ihrer Woche?",
    "sub": "Beantworten Sie ein paar Fragen. Wir empfehlen die Agenten, die Ihnen am meisten Zeit zurückgeben.",
    "start": "Quiz starten",
    "next": "Weiter",
    "back": "Zurück",
    "seeResults": "Meine Agenten anzeigen",
    "retake": "Quiz wiederholen"
  },
  "roi": {
    "eyebrow": "Einfache Rechnung",
    "title": "Was sind 20 Stunden pro Woche ",
    "titleHighlight": "für Sie wert?",
    "sub": "Inhaber unterschätzen oft die Kosten von Routinearbeit. Geben Sie Ihre Zahlen ein — die Amortisation ist meist in unter einer Minute klar.",
    "hoursLabel": "Stunden Verlust durch Routine / Woche",
    "rateLabel": "Ihr Zeitwert ($/Stunde)",
    "resultLabel": "Geschätzter Wert zurückgewonnener Zeit / Monat",
    "cta": "Kostenlos starten und diese Stunden zurückgewinnen"
  },
  "impact": {
    "title": "Echte Wirkung für Inhaber",
    "sub": "Stunden zurück. Beantwortete Leads. Geschlossene Tickets. Umsatz durch Agenten — nicht durch mehr Personal."
  },
  "agentsTeaser": {
    "eyebrow": "Ihr KI-Team",
    "title": "Agenten, die die Arbeit erledigen",
    "sub": "Jeder Agent ist bereit zum Verbinden und Laufen. Beginnen Sie mit einem. Fügen Sie weitere hinzu, sobald die Stunden zurückkommen.",
    "viewAll": "Alle Agenten anzeigen"
  },
  "products": {
    "eyebrow": "Produktpalette",
    "title": "Alles, was Sie brauchen, um ",
    "titleHighlight": "schlank zu arbeiten",
    "sub": "Von Lead-Qualifizierung bis Versandausnahmen — ein Ort, um Ihre KI-Belegschaft einzusetzen und zu verwalten."
  },
  "logistics": {
    "title": "Versand- & Logistik-Agenten",
    "sub": "Tarife vergleichen, Sendungen verfolgen und Kunden auf dem Laufenden halten, ohne im Carrier-Portal zu leben."
  },
  "features": {
    "title": "Für Inhaber gebaut, nicht für IT-Abteilungen",
    "sub": "Sicherheit, Datenschutz und einfache Steuerung — damit Sie die Kontrolle behalten."
  },
  "compare": {
    "title": "Wie Matrixly im Vergleich abschneidet",
    "sub": "Keine sechsstellige Einführung. Kein Warten auf Entwickler. Einfach Agenten, die funktionieren."
  },
  "testimonials": {
    "title": "Was Inhaber sagen",
    "sub": "Echtes Feedback von Unternehmern, die ihre Woche zurückgewonnen haben."
  },
  "guarantee": {
    "title": "Risikofrei testen",
    "sub": "Kostenlos erkunden. Jederzeit kündbar. Ihre Daten bleiben Ihre."
  },
  "pricing": {
    "eyebrow": "Einfache Preise",
    "title": "Pläne, die mit ",
    "titleHighlight": "Ihrem Unternehmen wachsen",
    "sub": "Kostenlos starten. Upgraden, wenn die Agenten Ihnen Zeit und Geld sparen.",
    "monthly": "Monatlich",
    "yearly": "Jährlich",
    "save": "Sparen",
    "popular": "Beliebteste",
    "cta": "Loslegen",
    "contact": "Sprechen Sie mit uns"
  },
  "resources": {
    "eyebrow": "Leitfäden & Playbooks",
    "title": "Praktische Ressourcen für ",
    "titleHighlight": "Inhaber",
    "sub": "Kurze, umsetzbare Guides — Einrichtung, E-Mail-Ton, lokales SEO, Versandausnahmen und mehr."
  },
  "integrations": {
    "eyebrow": "Integrationen",
    "title": "Funktioniert mit den Tools, die Sie ",
    "titleHighlight": "bereits nutzen",
    "sub": "Gmail, Shopify, QuickBooks, CRMs, Versanddienstleister und mehr — in Minuten verbunden."
  },
  "finalCta": {
    "title": "Bereit, Ihre Zeit zurückzugewinnen?",
    "sub": "Setzen Sie Ihren ersten Agenten in Minuten ein. Keine Karte nötig zum Erkunden.",
    "cta": "Kostenlos starten — keine Karte nötig"
  },
  "auth": {
    "signIn": "Anmelden",
    "signUp": "Registrieren",
    "email": "E-Mail",
    "password": "Passwort",
    "forgot": "Passwort vergessen?",
    "noAccount": "Noch kein Konto?",
    "hasAccount": "Bereits ein Konto?"
  },
  "footer": {
    "product": "Produkt",
    "company": "Unternehmen",
    "resources": "Ressourcen",
    "legal": "Rechtliches",
    "privacy": "Datenschutz",
    "terms": "AGB",
    "contact": "Kontakt",
    "tagline": "KI-Agenten für kleine und mittlere Unternehmen — in Minuten live, ohne Tech-Team."
  },
  "common": {
    "learnMore": "Mehr erfahren",
    "getStarted": "Loslegen",
    "tryFree": "Kostenlos testen",
    "loading": "Lädt…",
    "error": "Etwas ist schiefgelaufen. Bitte erneut versuchen.",
    "close": "Schließen",
    "save": "Speichern",
    "cancel": "Abbrechen",
    "continue": "Weiter",
    "back": "Zurück",
    "next": "Weiter",
    "submit": "Absenden",
    "language": "Sprache",
    "selectLanguage": "Sprache wählen"
  }
}


def key_paths(obj, prefix=""):
    paths = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.extend(key_paths(v, p))
    else:
        paths.append(prefix)
    return paths


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    locales = {
        "en": EN,
        "es": ES,
        "fr": FR,
        "ar": AR,
        "bn": BN,
        "de": DE,
    }
    en_paths = set(key_paths(EN))
    for code, data in locales.items():
        paths = set(key_paths(data))
        missing = en_paths - paths
        extra = paths - en_paths
        if missing or extra:
            raise SystemExit(f"{code}: missing={missing} extra={extra}")
        path = OUT / f"{code}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Expand locale catalogs with full landing-page strings and wire data-i18n on index.html.
Product/agent brand names stay English.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "i18n"
INDEX = ROOT / "index.html"

# --- English source additions (merged into existing structure) ---
EN_EXTRA = {
    "compare": {
        "eyebrow": "Why Matrixly",
        "title": "Matrixly vs. ",
        "titleHighlight": "the alternatives",
        "sub": "Cheaper than hiring people. More autonomous than DIY automation. Faster than traditional agencies.",
        "colDimension": "Dimension",
        "colMatrixly": "Matrixly",
        "colVa": "Part-time VA",
        "colZapier": "Zapier + ChatGPT",
        "colAgency": "Traditional agency",
        "rowCost": "Monthly cost",
        "rowCostMatrixly": "Plans that scale with you",
        "rowCostVa": "$800–$2,000+",
        "rowCostZapier": "$50–$200 + your time",
        "rowCostAgency": "$2,000–$10,000+",
        "rowSetup": "Setup time",
        "rowSetupMatrixly": "Minutes",
        "rowSetupVa": "Days to weeks (hire + train)",
        "rowSetupZapier": "Hours–days of DIY wiring",
        "rowSetupAgency": "Weeks of onboarding",
        "rowMaint": "Ongoing maintenance",
        "rowMaintMatrixly": "Low — managed agents + HITL",
        "rowMaintVa": "You manage the person",
        "rowMaintZapier": "You fix broken zaps & prompts",
        "rowMaintAgency": "Included (expensive)",
        "rowDone": "What gets done",
        "rowDoneMatrixly": "Leads, email, shipping, support, SEO — done work with review gates",
        "rowDoneVa": "Variable quality & coverage",
        "rowDoneZapier": "Drafts + glue scripts",
        "rowDoneAgency": "Campaigns & retainers",
        "rowAutonomy": "Autonomy",
        "rowAutonomyMatrixly": "High within guardrails",
        "rowAutonomyVa": "Human only",
        "rowAutonomyZapier": "Low without engineering",
        "rowAutonomyAgency": "High but slow",
        "cta": "Start free — compare for yourself",
    },
    "agentsTeaser": {
        "title": "Hire digital teammates in ",
        "titleHighlight": "minutes",
        "sub": "Proven agents for sales, ops, and logistics — start with one, stack more as you grow.",
        "browseAll": "Browse all agents →",
        "live": "Live",
        "leadDesc": "Scores every inbound lead, fills in missing contact details, and suggests the next best outreach — so you only talk to buyers ready to buy.",
        "leadCta": "Try Lead Qualifier",
        "emailDesc": "Sorts your inbox, drafts replies in your voice, and flags what actually needs you — so you stop living in email.",
        "emailCta": "Try Email Assistant",
        "shipDesc": "Picks smarter rates, tracks packages, and messages customers before they open a “where’s my order?” ticket.",
        "shipCta": "Try Shipping Assistant",
        "alsoLive": "Also live:",
        "alsoMore": "· Support, content, meetings & more ·",
        "seeCatalog": "See full catalog →",
    },
    "products": {
        "title": "Reliable agents. ",
        "titleHighlight": "Your business knowledge.",
        "titleEnd": " Real actions.",
        "sub": "Everything under the hood so agents remember your SOPs, reason carefully, and act in the apps you already use.",
        "card1Title": "Always-on agent engine",
        "card1Text": "Agents remember context, follow your rules, and keep working after you close the laptop.",
        "card2Title": "Your playbooks & SOPs",
        "card2Text": "Teach agents how your business works — pricing, policies, brand voice — once.",
        "card3Title": "Smart decision-making",
        "card3Text": "Powered by advanced AI reasoning for multi-step sales, ops, and logistics tasks.",
        "card4Title": "100+ app connections",
        "card4Text": "Gmail, Shopify, QuickBooks, carriers, CRM, Slack — agents take action, not just chat.",
        "explore": "Explore the full platform",
    },
    "logistics": {
        "eyebrow": "Example flow · shipping",
        "title": "From order to doorstep — ",
        "titleHighlight": "without the chaos",
        "sub": "Matrixly agents run fulfillment end to end so you ship faster, spend less on carriers, and answer fewer “where’s my order?” messages.",
        "step1Title": "Order comes in",
        "step1Text": "Shopify, WooCommerce, or POS orders enter the queue automatically.",
        "step2Title": "Stock check",
        "step2Text": "Confirms inventory, splits warehouses, and flags backorders early.",
        "step3Title": "Best rate",
        "step3Text": "Compares UPS, FedEx, USPS, and regional options for cost vs. speed.",
        "step4Title": "Label & ship",
        "step4Text": "Buys the label, updates the order, and prints packing slips.",
        "step5Title": "Track & notify",
        "step5Text": "Proactive delay and delivery messages before customers open tickets.",
        "step6Title": "Exceptions handled",
        "step6Text": "Lost packages, address fixes, and refunds with human approval when needed.",
        "teamEyebrow": "Your shipping team of agents",
        "lookEyebrow": "What it looks like",
    },
    "features": {
        "eyebrow": "Why owners choose Matrixly",
        "title": "Built for owners, not IT departments",
        "sub": "Security, privacy, and simple controls — so you stay in charge.",
    },
    "testimonials": {
        "eyebrow": "Owner stories",
        "title": "Named operators. ",
        "titleHighlight": "Clear before / after.",
        "sub": "Illustrative composite profiles based on early operator feedback — structured for real customer swap-in with permissioned photos and clips.",
        "quote1": "We replaced three freelancers with the content and lead agents. Rankings jumped, content never misses a week, and my marketing budget actually makes sense now.",
        "role1": "HVAC owner · Austin, TX · CoolAir HVAC",
        "quote2": "Shipping Assistant + SupportForge cut ‘where’s my order?’ tickets dramatically. Conversion and recovery emails improved overnight. Matrixly paid for itself in the first invoice cycle.",
        "role2": "Shopify CEO · Portland, OR · UrbanThread",
        "quote3": "Inbox zero is real again. The email agent drafts in my voice; I just approve. Clients think I hired an EA.",
        "role3": "Agency founder · Chicago, IL",
    },
    "guarantee": {
        "eyebrow": "Risk reversal",
        "title": "Try it risk-free",
        "sub": "Explore free. Cancel anytime. Your data stays yours.",
        "terms": "Cancel anytime · No long-term contract · No card to explore free",
        "termsNote": "Terms apply · US paid plans",
        "cta": "Start free — zero risk",
    },
    "pricing": {
        "perMonth": "/mo",
        "freeLabel": "Free",
        "freeName": "Explore",
        "freeDesc": "Browse agents and try the workflow risk-free.",
        "whatYouGet": "What you get",
        "freeF1": "Full marketplace access",
        "freeF2": "1 agent sandbox",
        "freeF3": "Community support",
        "freeF4": "Basic activity view",
        "freeCta": "Start free — no card",
        "starterLabel": "Starter",
        "starterName": "Grow",
        "starterNote": "About $1.60/day · less than a coffee",
        "starterDesc": "Ideal for solo operators and small teams ready to automate core work.",
        "whatAchieve": "What you can achieve",
        "starterF1": "3 active agents (e.g. email + leads + SEO)",
        "starterF2": "Core tools: Gmail, Shopify, CRM basics",
        "starterF3": "Local SEO intelligence",
        "starterF4": "Email support",
        "starterCta": "Start Grow",
        "popular": "MOST POPULAR",
        "proLabel": "Pro",
        "proName": "Scale",
        "proNote": "A fraction of one VA · multi-agent coverage",
        "proDesc": "Full agent stacks for growing shops and multi-step workflows.",
        "proF1": "15 active agents across sales & ops",
        "proF2": "All integrations (carriers, ads, finance)",
        "proF3": "Simple agent builder",
        "proF4": "Priority support",
        "proF5": "Full ROI dashboard",
        "proCta": "Start Scale",
        "execLabel": "Executive",
        "execName": "White Glove",
        "execNote": "Founding · managed digital employee",
        "execDesc": "The real product is coaching + ongoing management — not just the agent.",
        "execF1": "1 custom digital employee installed",
        "execF2": "On-site founder training visit",
        "execF3": "Shared-channel coaching",
        "execF4": "Weekly value ledger / ROI report",
        "execF5": "Ongoing management & reliability",
        "execCta": "Explore Digital Employee →",
    },
    "finalCta": {
        "badge": "Free to explore · Cancel anytime",
        "packCta": "Get my agent pack",
        "orBrowse": "Or",
        "browseAgents": "browse agents",
        "calculateRoi": "calculate your ROI",
    },
    "impact": {
        "eyebrow": "Results that matter",
        "title": "Real impact for owners",
        "sub": "Hours back. Leads answered. Tickets closed. Revenue tied to agents — not more headcount.",
    },
    "roi": {
        "cta": "Start free and reclaim those hours",
        "resultHint": "Estimated value of time reclaimed / month",
    },
    "auth": {
        "title": "Get started with Matrixly",
        "sub": "Create a free account to deploy agents for marketing, sales, and ops.",
        "google": "Continue with Google",
        "microsoft": "Continue with Microsoft",
        "sso": "Continue with SSO",
        "emailBtn": "Continue with email",
        "login": "Log in",
    },
    "common": {
        "startFree": "Start free",
        "seeIntegrations": "See integrations",
        "marketplace": "← Marketplace",
    },
}

# Translations for new keys (owner tone). Existing keys preserved.
# Only NEW leaf keys under expanded sections need translations.
TRANSLATIONS = {
    "es": {
        "compare": {
            "eyebrow": "Por qué Matrixly",
            "title": "Matrixly vs. ",
            "titleHighlight": "las alternativas",
            "sub": "Más barato que contratar. Más autónomo que la automatización DIY. Más rápido que una agencia tradicional.",
            "colDimension": "Dimensión",
            "colMatrixly": "Matrixly",
            "colVa": "VA a tiempo parcial",
            "colZapier": "Zapier + ChatGPT",
            "colAgency": "Agencia tradicional",
            "rowCost": "Coste mensual",
            "rowCostMatrixly": "Planes que crecen contigo",
            "rowCostVa": "$800–$2,000+",
            "rowCostZapier": "$50–$200 + tu tiempo",
            "rowCostAgency": "$2,000–$10,000+",
            "rowSetup": "Tiempo de puesta en marcha",
            "rowSetupMatrixly": "Minutos",
            "rowSetupVa": "Días a semanas (contratar + formar)",
            "rowSetupZapier": "Horas–días de cableado DIY",
            "rowSetupAgency": "Semanas de onboarding",
            "rowMaint": "Mantenimiento continuo",
            "rowMaintMatrixly": "Bajo — agentes gestionados + HITL",
            "rowMaintVa": "Tú gestionas a la persona",
            "rowMaintZapier": "Tú arreglas zaps y prompts rotos",
            "rowMaintAgency": "Incluido (caro)",
            "rowDone": "Qué se hace",
            "rowDoneMatrixly": "Leads, correo, envíos, soporte, SEO — trabajo hecho con revisión humana",
            "rowDoneVa": "Calidad y cobertura variables",
            "rowDoneZapier": "Borradores + scripts de pegamento",
            "rowDoneAgency": "Campañas y retainers",
            "rowAutonomy": "Autonomía",
            "rowAutonomyMatrixly": "Alta con límites claros",
            "rowAutonomyVa": "Solo humano",
            "rowAutonomyZapier": "Baja sin ingeniería",
            "rowAutonomyAgency": "Alta pero lenta",
            "cta": "Empieza gratis — compáralo tú mismo",
        },
        "agentsTeaser": {
            "title": "Contrata compañeros digitales en ",
            "titleHighlight": "minutos",
            "sub": "Agentes probados para ventas, operaciones y logística — empieza con uno y añade más al crecer.",
            "browseAll": "Ver todos los agentes →",
            "live": "En vivo",
            "leadDesc": "Puntúa cada lead entrante, completa datos de contacto y sugiere el siguiente paso — solo hablas con compradores listos.",
            "leadCta": "Probar Lead Qualifier",
            "emailDesc": "Ordena tu bandeja, redacta respuestas con tu voz y marca lo que realmente necesita de ti.",
            "emailCta": "Probar Email Assistant",
            "shipDesc": "Elige mejores tarifas, rastrea paquetes y avisa a clientes antes del ticket de “¿dónde está mi pedido?”.",
            "shipCta": "Probar Shipping Assistant",
            "alsoLive": "También en vivo:",
            "alsoMore": "· Soporte, contenido, reuniones y más ·",
            "seeCatalog": "Ver catálogo completo →",
        },
        "products": {
            "title": "Agentes fiables. ",
            "titleHighlight": "El conocimiento de tu negocio.",
            "titleEnd": " Acciones reales.",
            "sub": "Todo lo necesario para que los agentes recuerden tus SOPs, razonen con cuidado y actúen en las apps que ya usas.",
            "card1Title": "Motor de agentes siempre activo",
            "card1Text": "Recuerdan el contexto, siguen tus reglas y siguen trabajando cuando cierras el portátil.",
            "card2Title": "Tus playbooks y SOPs",
            "card2Text": "Enséñales cómo funciona tu negocio — precios, políticas, voz de marca — una vez.",
            "card3Title": "Decisiones inteligentes",
            "card3Text": "Razonamiento avanzado de IA para tareas multi-paso de ventas, ops y logística.",
            "card4Title": "Más de 100 conexiones de apps",
            "card4Text": "Gmail, Shopify, QuickBooks, transportistas, CRM, Slack — actúan, no solo chatean.",
            "explore": "Explorar la plataforma completa",
        },
        "logistics": {
            "eyebrow": "Flujo de ejemplo · envíos",
            "title": "Del pedido a la puerta — ",
            "titleHighlight": "sin el caos",
            "sub": "Los agentes Matrixly gestionan el fulfillment de extremo a extremo para enviar más rápido, gastar menos en transportistas y responder menos “¿dónde está mi pedido?”.",
            "step1Title": "Entra el pedido",
            "step1Text": "Pedidos de Shopify, WooCommerce o POS entran en cola automáticamente.",
            "step2Title": "Stock",
            "step2Text": "Confirma inventario, divide almacenes y marca backorders pronto.",
            "step3Title": "Mejor tarifa",
            "step3Text": "Compara UPS, FedEx, USPS y opciones regionales coste vs. velocidad.",
            "step4Title": "Etiqueta y envío",
            "step4Text": "Compra la etiqueta, actualiza el pedido e imprime packing slips.",
            "step5Title": "Rastreo y aviso",
            "step5Text": "Mensajes proactivos de retraso y entrega antes de que abran tickets.",
            "step6Title": "Excepciones",
            "step6Text": "Paquetes perdidos, direcciones y reembolsos con aprobación humana cuando hace falta.",
            "teamEyebrow": "Tu equipo de envíos de agentes",
            "lookEyebrow": "Cómo se ve",
        },
        "features": {
            "eyebrow": "Por qué lo eligen los dueños",
            "title": "Hecho para dueños, no para departamentos de TI",
            "sub": "Seguridad, privacidad y controles simples — para que sigas al mando.",
        },
        "testimonials": {
            "eyebrow": "Historias de dueños",
            "title": "Operadores con nombre. ",
            "titleHighlight": "Antes / después claros.",
            "sub": "Perfiles compuestos ilustrativos basados en feedback temprano — listos para sustituir por clientes reales con permiso.",
            "quote1": "Sustituimos a tres freelancers con los agentes de contenido y leads. Subieron los rankings, el contenido no falla una semana y el presupuesto de marketing tiene sentido.",
            "role1": "Dueño HVAC · Austin, TX · CoolAir HVAC",
            "quote2": "Shipping Assistant + SupportForge redujeron mucho los tickets de “¿dónde está mi pedido?”. Matrixly se pagó solo en el primer ciclo de factura.",
            "role2": "CEO Shopify · Portland, OR · UrbanThread",
            "quote3": "Inbox zero es real otra vez. El agente de correo redacta con mi voz; yo solo apruebo. Los clientes creen que contraté un EA.",
            "role3": "Fundador de agencia · Chicago, IL",
        },
        "guarantee": {
            "eyebrow": "Sin riesgo",
            "title": "Pruébalo sin riesgo",
            "sub": "Explora gratis. Cancela cuando quieras. Tus datos son tuyos.",
            "terms": "Cancela cuando quieras · Sin contrato largo · Sin tarjeta para explorar gratis",
            "termsNote": "Aplican condiciones · Planes de pago EE. UU.",
            "cta": "Empieza gratis — cero riesgo",
        },
        "pricing": {
            "perMonth": "/mes",
            "freeLabel": "Gratis",
            "freeName": "Explorar",
            "freeDesc": "Explora agentes y prueba el flujo sin riesgo.",
            "whatYouGet": "Qué obtienes",
            "freeF1": "Acceso completo al marketplace",
            "freeF2": "1 sandbox de agente",
            "freeF3": "Soporte de comunidad",
            "freeF4": "Vista básica de actividad",
            "freeCta": "Empieza gratis — sin tarjeta",
            "starterLabel": "Starter",
            "starterName": "Grow",
            "starterNote": "Unos $1.60/día · menos que un café",
            "starterDesc": "Ideal para operadores en solitario y equipos pequeños listos para automatizar lo esencial.",
            "whatAchieve": "Qué puedes lograr",
            "starterF1": "3 agentes activos (p. ej. correo + leads + SEO)",
            "starterF2": "Herramientas base: Gmail, Shopify, CRM básico",
            "starterF3": "Inteligencia de SEO local",
            "starterF4": "Soporte por correo",
            "starterCta": "Empezar Grow",
            "popular": "MÁS POPULAR",
            "proLabel": "Pro",
            "proName": "Scale",
            "proNote": "Una fracción de un VA · cobertura multi-agente",
            "proDesc": "Stacks completos de agentes para tiendas en crecimiento y flujos multi-paso.",
            "proF1": "15 agentes activos en ventas y ops",
            "proF2": "Todas las integraciones (envíos, ads, finanzas)",
            "proF3": "Constructor simple de agentes",
            "proF4": "Soporte prioritario",
            "proF5": "Dashboard ROI completo",
            "proCta": "Empezar Scale",
            "execLabel": "Executive",
            "execName": "White Glove",
            "execNote": "Fundadores · empleado digital gestionado",
            "execDesc": "El producto real es coaching + gestión continua — no solo el agente.",
            "execF1": "1 empleado digital a medida instalado",
            "execF2": "Visita de formación del fundador",
            "execF3": "Coaching en canal compartido",
            "execF4": "Informe semanal de valor / ROI",
            "execF5": "Gestión y fiabilidad continuas",
            "execCta": "Explorar Digital Employee →",
        },
        "finalCta": {
            "badge": "Explora gratis · Cancela cuando quieras",
            "packCta": "Obtener mi pack de agentes",
            "orBrowse": "O",
            "browseAgents": "ver agentes",
            "calculateRoi": "calcula tu ROI",
        },
        "impact": {
            "eyebrow": "Resultados que importan",
            "title": "Impacto real para dueños",
            "sub": "Horas de vuelta. Leads respondidos. Tickets cerrados. Ingresos ligados a agentes — no a más personal.",
        },
        "roi": {
            "cta": "Empieza gratis y recupera esas horas",
            "resultHint": "Valor estimado del tiempo recuperado / mes",
        },
        "auth": {
            "title": "Empieza con Matrixly",
            "sub": "Crea una cuenta gratis para desplegar agentes de marketing, ventas y ops.",
            "google": "Continuar con Google",
            "microsoft": "Continuar con Microsoft",
            "sso": "Continuar con SSO",
            "emailBtn": "Continuar con correo",
            "login": "Iniciar sesión",
        },
        "common": {
            "startFree": "Empezar gratis",
            "seeIntegrations": "Ver integraciones",
            "marketplace": "← Marketplace",
        },
    },
}

# For fr, de, ar, bn, ms: generate from Spanish structure via EN as base for missing,
# with dedicated high-quality blocks for ar (RTL critical - screenshot language)


def deep_merge(base: dict, extra: dict) -> dict:
    out = deepcopy(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def load(code: str) -> dict:
    return json.loads((I18N / f"{code}.json").read_text(encoding="utf-8"))


def save(code: str, data: dict) -> None:
    (I18N / f"{code}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# Full FR, DE, AR, BN, MS compare+critical section translations
FR_EXTRA = deep_merge(EN_EXTRA, {})  # start from EN then override
FR_EXTRA = {
    "compare": {
        "eyebrow": "Pourquoi Matrixly",
        "title": "Matrixly vs. ",
        "titleHighlight": "les alternatives",
        "sub": "Moins cher qu’embaucher. Plus autonome que l’automatisation DIY. Plus rapide qu’une agence traditionnelle.",
        "colDimension": "Dimension",
        "colMatrixly": "Matrixly",
        "colVa": "Assistant à temps partiel",
        "colZapier": "Zapier + ChatGPT",
        "colAgency": "Agence traditionnelle",
        "rowCost": "Coût mensuel",
        "rowCostMatrixly": "Des offres qui grandissent avec vous",
        "rowCostVa": "800–2 000 $+",
        "rowCostZapier": "50–200 $ + votre temps",
        "rowCostAgency": "2 000–10 000 $+",
        "rowSetup": "Temps de mise en place",
        "rowSetupMatrixly": "Minutes",
        "rowSetupVa": "Jours à semaines (recruter + former)",
        "rowSetupZapier": "Heures–jours de bricolage DIY",
        "rowSetupAgency": "Semaines d’onboarding",
        "rowMaint": "Maintenance continue",
        "rowMaintMatrixly": "Faible — agents gérés + HITL",
        "rowMaintVa": "Vous gérez la personne",
        "rowMaintZapier": "Vous réparez zaps et prompts cassés",
        "rowMaintAgency": "Inclus (cher)",
        "rowDone": "Ce qui est fait",
        "rowDoneMatrixly": "Leads, e-mail, expédition, support, SEO — travail terminé avec validation humaine",
        "rowDoneVa": "Qualité et couverture variables",
        "rowDoneZapier": "Brouillons + scripts de colle",
        "rowDoneAgency": "Campagnes et retainers",
        "rowAutonomy": "Autonomie",
        "rowAutonomyMatrixly": "Élevée dans des garde-fous",
        "rowAutonomyVa": "Humain uniquement",
        "rowAutonomyZapier": "Faible sans ingénierie",
        "rowAutonomyAgency": "Élevée mais lente",
        "cta": "Commencer gratuitement — comparez vous-même",
    },
    "agentsTeaser": {
        "title": "Engagez des coéquipiers numériques en ",
        "titleHighlight": "minutes",
        "sub": "Agents éprouvés pour les ventes, les ops et la logistique — commencez par un, ajoutez-en d’autres en grandissant.",
        "browseAll": "Voir tous les agents →",
        "live": "En direct",
        "leadDesc": "Note chaque lead entrant, complète les contacts et suggère la prochaine action — vous ne parlez qu’aux acheteurs prêts.",
        "leadCta": "Essayer Lead Qualifier",
        "emailDesc": "Trie la boîte mail, rédige dans votre voix et signale ce qui a vraiment besoin de vous.",
        "emailCta": "Essayer Email Assistant",
        "shipDesc": "Choisit de meilleurs tarifs, suit les colis et prévient avant le ticket « où est ma commande ? ».",
        "shipCta": "Essayer Shipping Assistant",
        "alsoLive": "Aussi en direct :",
        "alsoMore": "· Support, contenu, réunions et plus ·",
        "seeCatalog": "Voir le catalogue complet →",
    },
    "products": {
        "title": "Agents fiables. ",
        "titleHighlight": "La connaissance de votre entreprise.",
        "titleEnd": " De vraies actions.",
        "sub": "Tout le nécessaire pour que les agents mémorisent vos SOP, raisonnent avec soin et agissent dans vos apps.",
        "card1Title": "Moteur d’agents toujours actif",
        "card1Text": "Ils mémorisent le contexte, suivent vos règles et continuent après la fermeture du laptop.",
        "card2Title": "Vos playbooks et SOP",
        "card2Text": "Apprenez-leur comment votre entreprise fonctionne — prix, politiques, voix de marque — une fois.",
        "card3Title": "Décisions intelligentes",
        "card3Text": "Raisonnement IA avancé pour les tâches multi-étapes ventes, ops et logistique.",
        "card4Title": "100+ connexions d’apps",
        "card4Text": "Gmail, Shopify, QuickBooks, transporteurs, CRM, Slack — ils agissent, pas seulement chattent.",
        "explore": "Explorer toute la plateforme",
    },
    "logistics": {
        "eyebrow": "Exemple de flux · expédition",
        "title": "De la commande à la porte — ",
        "titleHighlight": "sans le chaos",
        "sub": "Les agents Matrixly gèrent le fulfillment de bout en bout pour expédier plus vite, dépenser moins et répondre moins aux « où est ma commande ? ».",
        "step1Title": "La commande arrive",
        "step1Text": "Les commandes Shopify, WooCommerce ou POS entrent automatiquement en file.",
        "step2Title": "Stock",
        "step2Text": "Confirme l’inventaire, répartit les entrepôts et signale les ruptures tôt.",
        "step3Title": "Meilleur tarif",
        "step3Text": "Compare UPS, FedEx, USPS et options régionales coût vs. vitesse.",
        "step4Title": "Étiquette et envoi",
        "step4Text": "Achète l’étiquette, met à jour la commande et imprime les bons de livraison.",
        "step5Title": "Suivi et notification",
        "step5Text": "Messages proactifs de retard et de livraison avant les tickets.",
        "step6Title": "Exceptions gérées",
        "step6Text": "Colis perdus, adresses et remboursements avec validation humaine si besoin.",
        "teamEyebrow": "Votre équipe d’expédition d’agents",
        "lookEyebrow": "À quoi ça ressemble",
    },
    "features": {
        "eyebrow": "Pourquoi les dirigeants choisissent Matrixly",
        "title": "Conçu pour les dirigeants, pas pour les DSI",
        "sub": "Sécurité, confidentialité et contrôles simples — pour que vous restiez aux commandes.",
    },
    "testimonials": {
        "eyebrow": "Histoires de dirigeants",
        "title": "Des opérateurs nommés. ",
        "titleHighlight": "Avant / après clairs.",
        "sub": "Profils composites illustratifs basés sur les premiers retours — prêts pour de vrais clients avec autorisation.",
        "quote1": "Nous avons remplacé trois freelances par les agents contenu et leads. Le ranking a grimpé, le contenu ne rate plus une semaine, et mon budget marketing a enfin du sens.",
        "role1": "Propriétaire CVC · Austin, TX · CoolAir HVAC",
        "quote2": "Shipping Assistant + SupportForge ont fortement réduit les tickets « où est ma commande ? ». Matrixly s’est rentabilisé dès le premier cycle de facture.",
        "role2": "CEO Shopify · Portland, OR · UrbanThread",
        "quote3": "L’inbox zéro est redevenue réelle. L’agent e-mail rédige dans ma voix ; j’approuve seulement. Les clients croient que j’ai embauché un EA.",
        "role3": "Fondateur d’agence · Chicago, IL",
    },
    "guarantee": {
        "eyebrow": "Sans risque",
        "title": "Essayez sans risque",
        "sub": "Explorez gratuitement. Annulez à tout moment. Vos données restent les vôtres.",
        "terms": "Annulation à tout moment · Pas de long contrat · Pas de carte pour explorer gratuitement",
        "termsNote": "Conditions applicables · Offres payantes US",
        "cta": "Commencer gratuitement — zéro risque",
    },
    "pricing": {
        "perMonth": "/mois",
        "freeLabel": "Gratuit",
        "freeName": "Explorer",
        "freeDesc": "Parcourez les agents et essayez le flux sans risque.",
        "whatYouGet": "Ce que vous obtenez",
        "freeF1": "Accès complet au marketplace",
        "freeF2": "1 bac à sable d’agent",
        "freeF3": "Support communautaire",
        "freeF4": "Vue d’activité basique",
        "freeCta": "Commencer gratuitement — sans carte",
        "starterLabel": "Starter",
        "starterName": "Grow",
        "starterNote": "Environ 1,60 $/jour · moins qu’un café",
        "starterDesc": "Idéal pour les solo et petites équipes prêtes à automatiser l’essentiel.",
        "whatAchieve": "Ce que vous pouvez accomplir",
        "starterF1": "3 agents actifs (ex. e-mail + leads + SEO)",
        "starterF2": "Outils de base : Gmail, Shopify, CRM basique",
        "starterF3": "Intelligence SEO locale",
        "starterF4": "Support e-mail",
        "starterCta": "Démarrer Grow",
        "popular": "LE PLUS POPULAIRE",
        "proLabel": "Pro",
        "proName": "Scale",
        "proNote": "Une fraction d’un VA · couverture multi-agents",
        "proDesc": "Stacks d’agents complets pour boutiques en croissance et flux multi-étapes.",
        "proF1": "15 agents actifs ventes & ops",
        "proF2": "Toutes les intégrations (transporteurs, ads, finance)",
        "proF3": "Constructeur d’agents simple",
        "proF4": "Support prioritaire",
        "proF5": "Tableau de bord ROI complet",
        "proCta": "Démarrer Scale",
        "execLabel": "Executive",
        "execName": "White Glove",
        "execNote": "Fondateurs · employé digital managé",
        "execDesc": "Le vrai produit, c’est le coaching + la gestion continue — pas seulement l’agent.",
        "execF1": "1 employé digital sur mesure installé",
        "execF2": "Visite de formation du fondateur",
        "execF3": "Coaching en canal partagé",
        "execF4": "Rapport de valeur / ROI hebdomadaire",
        "execF5": "Gestion et fiabilité continues",
        "execCta": "Explorer Digital Employee →",
    },
    "finalCta": {
        "badge": "Exploration gratuite · Annulation à tout moment",
        "packCta": "Obtenir mon pack d’agents",
        "orBrowse": "Ou",
        "browseAgents": "parcourir les agents",
        "calculateRoi": "calculer votre ROI",
    },
    "impact": {
        "eyebrow": "Des résultats qui comptent",
        "title": "Un impact réel pour les dirigeants",
        "sub": "Heures récupérées. Leads traités. Tickets clos. Revenus liés aux agents — pas à plus d’effectifs.",
    },
    "roi": {
        "cta": "Commencer gratuitement et récupérer ces heures",
        "resultHint": "Valeur estimée du temps récupéré / mois",
    },
    "auth": {
        "title": "Commencer avec Matrixly",
        "sub": "Créez un compte gratuit pour déployer des agents marketing, ventes et ops.",
        "google": "Continuer avec Google",
        "microsoft": "Continuer avec Microsoft",
        "sso": "Continuer avec SSO",
        "emailBtn": "Continuer avec e-mail",
        "login": "Se connecter",
    },
    "common": {
        "startFree": "Commencer gratuitement",
        "seeIntegrations": "Voir les intégrations",
        "marketplace": "← Marketplace",
    },
}

DE_EXTRA = {
    "compare": {
        "eyebrow": "Warum Matrixly",
        "title": "Matrixly vs. ",
        "titleHighlight": "die Alternativen",
        "sub": "Günstiger als Einstellen. Autonomer als DIY-Automation. Schneller als klassische Agenturen.",
        "colDimension": "Dimension",
        "colMatrixly": "Matrixly",
        "colVa": "Teilzeit-VA",
        "colZapier": "Zapier + ChatGPT",
        "colAgency": "Klassische Agentur",
        "rowCost": "Monatliche Kosten",
        "rowCostMatrixly": "Pläne, die mit Ihnen wachsen",
        "rowCostVa": "800–2.000 $+",
        "rowCostZapier": "50–200 $ + Ihre Zeit",
        "rowCostAgency": "2.000–10.000 $+",
        "rowSetup": "Einrichtungszeit",
        "rowSetupMatrixly": "Minuten",
        "rowSetupVa": "Tage bis Wochen (einstellen + schulen)",
        "rowSetupZapier": "Stunden–Tage DIY-Verkabelung",
        "rowSetupAgency": "Wochen Onboarding",
        "rowMaint": "Laufende Wartung",
        "rowMaintMatrixly": "Niedrig — gemanagte Agenten + HITL",
        "rowMaintVa": "Sie managen die Person",
        "rowMaintZapier": "Sie reparieren kaputte Zaps & Prompts",
        "rowMaintAgency": "Inklusive (teuer)",
        "rowDone": "Was erledigt wird",
        "rowDoneMatrixly": "Leads, E-Mail, Versand, Support, SEO — fertige Arbeit mit Review-Gates",
        "rowDoneVa": "Variable Qualität & Abdeckung",
        "rowDoneZapier": "Entwürfe + Glue-Skripte",
        "rowDoneAgency": "Kampagnen & Retainers",
        "rowAutonomy": "Autonomie",
        "rowAutonomyMatrixly": "Hoch innerhalb von Leitplanken",
        "rowAutonomyVa": "Nur Mensch",
        "rowAutonomyZapier": "Niedrig ohne Engineering",
        "rowAutonomyAgency": "Hoch, aber langsam",
        "cta": "Kostenlos starten — selbst vergleichen",
    },
    "agentsTeaser": {
        "title": "Digitale Teamkollegen in ",
        "titleHighlight": "Minuten",
        "sub": "Bewährte Agenten für Sales, Ops und Logistik — starten Sie mit einem, stapeln Sie mehr beim Wachstum.",
        "browseAll": "Alle Agenten ansehen →",
        "live": "Live",
        "leadDesc": "Bewertet jeden eingehenden Lead, ergänzt Kontaktdaten und schlägt den nächsten Schritt vor — Sie sprechen nur mit kaufbereiten Käufern.",
        "leadCta": "Lead Qualifier testen",
        "emailDesc": "Sortiert den Posteingang, entwirft Antworten in Ihrer Stimme und markiert, was wirklich Sie braucht.",
        "emailCta": "Email Assistant testen",
        "shipDesc": "Wählt bessere Tarife, trackt Pakete und informiert Kunden vor dem „Wo ist meine Bestellung?“-Ticket.",
        "shipCta": "Shipping Assistant testen",
        "alsoLive": "Auch live:",
        "alsoMore": "· Support, Content, Meetings & mehr ·",
        "seeCatalog": "Vollständigen Katalog sehen →",
    },
    "products": {
        "title": "Zuverlässige Agenten. ",
        "titleHighlight": "Ihr Geschäftswissen.",
        "titleEnd": " Echte Aktionen.",
        "sub": "Alles unter der Haube, damit Agenten Ihre SOPs merken, sorgfältig denken und in Ihren Apps handeln.",
        "card1Title": "Immer-an Agenten-Engine",
        "card1Text": "Agenten merken sich Kontext, folgen Ihren Regeln und arbeiten weiter, wenn der Laptop zu ist.",
        "card2Title": "Ihre Playbooks & SOPs",
        "card2Text": "Bringen Sie Agenten bei, wie Ihr Business funktioniert — Preise, Policies, Markenstimme — einmal.",
        "card3Title": "Smarte Entscheidungen",
        "card3Text": "Fortschrittliches KI-Reasoning für mehrstufige Sales-, Ops- und Logistikaufgaben.",
        "card4Title": "100+ App-Verbindungen",
        "card4Text": "Gmail, Shopify, QuickBooks, Carrier, CRM, Slack — Agenten handeln, chatten nicht nur.",
        "explore": "Die volle Plattform erkunden",
    },
    "logistics": {
        "eyebrow": "Beispiel-Flow · Versand",
        "title": "Von der Bestellung zur Tür — ",
        "titleHighlight": "ohne Chaos",
        "sub": "Matrixly-Agenten steuern Fulfillment end-to-end: schneller versenden, weniger Carrier-Kosten, weniger „Wo ist meine Bestellung?“-Nachrichten.",
        "step1Title": "Bestellung kommt",
        "step1Text": "Shopify-, WooCommerce- oder POS-Bestellungen landen automatisch in der Queue.",
        "step2Title": "Bestand",
        "step2Text": "Prüft Inventar, splittet Lager und flaggt Backorders früh.",
        "step3Title": "Bester Tarif",
        "step3Text": "Vergleicht UPS, FedEx, USPS und Regionaloptionen Kosten vs. Tempo.",
        "step4Title": "Label & Versand",
        "step4Text": "Kauft das Label, aktualisiert die Bestellung und druckt Lieferscheine.",
        "step5Title": "Tracken & benachrichtigen",
        "step5Text": "Proaktive Verzögerungs- und Zustellnachrichten vor Tickets.",
        "step6Title": "Ausnahmen gelöst",
        "step6Text": "Verlorene Pakete, Adresskorrekturen und Erstattungen mit menschlicher Freigabe wenn nötig.",
        "teamEyebrow": "Ihr Versand-Team aus Agenten",
        "lookEyebrow": "So sieht es aus",
    },
    "features": {
        "eyebrow": "Warum Inhaber Matrixly wählen",
        "title": "Für Inhaber gebaut, nicht für IT-Abteilungen",
        "sub": "Sicherheit, Datenschutz und einfache Steuerung — damit Sie die Kontrolle behalten.",
    },
    "testimonials": {
        "eyebrow": "Inhaber-Geschichten",
        "title": "Benannte Betreiber. ",
        "titleHighlight": "Klares Vorher / Nachher.",
        "sub": "Illustrative Profil-Komposite basierend auf frühem Feedback — bereit für echte Kunden mit Freigabe.",
        "quote1": "Wir haben drei Freelancer durch Content- und Lead-Agenten ersetzt. Rankings stiegen, Content fällt keine Woche aus, und mein Marketingbudget ergibt endlich Sinn.",
        "role1": "HVAC-Inhaber · Austin, TX · CoolAir HVAC",
        "quote2": "Shipping Assistant + SupportForge haben „Wo ist meine Bestellung?“-Tickets stark reduziert. Matrixly hat sich im ersten Rechnungszyklus amortisiert.",
        "role2": "Shopify-CEO · Portland, OR · UrbanThread",
        "quote3": "Inbox Zero ist wieder real. Der E-Mail-Agent schreibt in meiner Stimme; ich genehmige nur. Kunden denken, ich hätte eine EA eingestellt.",
        "role3": "Agenturgründer · Chicago, IL",
    },
    "guarantee": {
        "eyebrow": "Risikoumkehr",
        "title": "Risikofrei testen",
        "sub": "Kostenlos erkunden. Jederzeit kündbar. Ihre Daten bleiben Ihre.",
        "terms": "Jederzeit kündbar · Kein Langzeitvertrag · Keine Karte zum kostenlosen Erkunden",
        "termsNote": "Es gelten Bedingungen · US-Bezahlpläne",
        "cta": "Kostenlos starten — null Risiko",
    },
    "pricing": {
        "perMonth": "/Monat",
        "freeLabel": "Kostenlos",
        "freeName": "Erkunden",
        "freeDesc": "Agenten browsen und den Workflow risikofrei testen.",
        "whatYouGet": "Was Sie bekommen",
        "freeF1": "Voller Marketplace-Zugang",
        "freeF2": "1 Agenten-Sandbox",
        "freeF3": "Community-Support",
        "freeF4": "Basis-Aktivitätsansicht",
        "freeCta": "Kostenlos starten — keine Karte",
        "starterLabel": "Starter",
        "starterName": "Grow",
        "starterNote": "Ca. 1,60 $/Tag · weniger als ein Kaffee",
        "starterDesc": "Ideal für Solo-Betreiber und kleine Teams, die Kernarbeit automatisieren wollen.",
        "whatAchieve": "Was Sie erreichen können",
        "starterF1": "3 aktive Agenten (z. B. E-Mail + Leads + SEO)",
        "starterF2": "Kern-Tools: Gmail, Shopify, CRM-Basics",
        "starterF3": "Lokale SEO-Intelligenz",
        "starterF4": "E-Mail-Support",
        "starterCta": "Grow starten",
        "popular": "BELIEBTESTE",
        "proLabel": "Pro",
        "proName": "Scale",
        "proNote": "Ein Bruchteil eines VA · Multi-Agenten-Abdeckung",
        "proDesc": "Volle Agenten-Stacks für wachsende Shops und mehrstufige Workflows.",
        "proF1": "15 aktive Agenten in Sales & Ops",
        "proF2": "Alle Integrationen (Carrier, Ads, Finance)",
        "proF3": "Einfacher Agenten-Builder",
        "proF4": "Priority-Support",
        "proF5": "Volles ROI-Dashboard",
        "proCta": "Scale starten",
        "execLabel": "Executive",
        "execName": "White Glove",
        "execNote": "Founding · gemanagter digitaler Mitarbeiter",
        "execDesc": "Das echte Produkt ist Coaching + laufendes Management — nicht nur der Agent.",
        "execF1": "1 maßgeschneiderter digitaler Mitarbeiter installiert",
        "execF2": "Vor-Ort-Training mit dem Founder",
        "execF3": "Coaching im Shared Channel",
        "execF4": "Wöchentlicher Value-/ROI-Report",
        "execF5": "Laufendes Management & Zuverlässigkeit",
        "execCta": "Digital Employee erkunden →",
    },
    "finalCta": {
        "badge": "Kostenlos erkunden · Jederzeit kündbar",
        "packCta": "Mein Agenten-Pack holen",
        "orBrowse": "Oder",
        "browseAgents": "Agenten browsen",
        "calculateRoi": "ROI berechnen",
    },
    "impact": {
        "eyebrow": "Ergebnisse, die zählen",
        "title": "Echte Wirkung für Inhaber",
        "sub": "Stunden zurück. Beantwortete Leads. Geschlossene Tickets. Umsatz durch Agenten — nicht mehr Headcount.",
    },
    "roi": {
        "cta": "Kostenlos starten und diese Stunden zurückgewinnen",
        "resultHint": "Geschätzter Wert zurückgewonnener Zeit / Monat",
    },
    "auth": {
        "title": "Mit Matrixly starten",
        "sub": "Kostenloses Konto erstellen, um Agenten für Marketing, Sales und Ops bereitzustellen.",
        "google": "Mit Google fortfahren",
        "microsoft": "Mit Microsoft fortfahren",
        "sso": "Mit SSO fortfahren",
        "emailBtn": "Mit E-Mail fortfahren",
        "login": "Anmelden",
    },
    "common": {
        "startFree": "Kostenlos starten",
        "seeIntegrations": "Integrationen ansehen",
        "marketplace": "← Marketplace",
    },
}

AR_EXTRA = {
    "compare": {
        "eyebrow": "لماذا ماتريكسلي",
        "title": "ماتريكسلي مقابل ",
        "titleHighlight": "البدائل",
        "sub": "أرخص من التوظيف. أكثر استقلالية من أتمتة افعلها بنفسك. أسرع من الوكالات التقليدية.",
        "colDimension": "البُعد",
        "colMatrixly": "Matrixly",
        "colVa": "مساعد بدوام جزئي",
        "colZapier": "Zapier + ChatGPT",
        "colAgency": "وكالة تقليدية",
        "rowCost": "التكلفة الشهرية",
        "rowCostMatrixly": "خطط تنمو معك",
        "rowCostVa": "$800–$2,000+",
        "rowCostZapier": "$50–$200 + وقتك",
        "rowCostAgency": "$2,000–$10,000+",
        "rowSetup": "وقت الإعداد",
        "rowSetupMatrixly": "دقائق",
        "rowSetupVa": "أيام إلى أسابيع (توظيف + تدريب)",
        "rowSetupZapier": "ساعات–أيام من الربط اليدوي",
        "rowSetupAgency": "أسابيع من التهيئة",
        "rowMaint": "الصيانة المستمرة",
        "rowMaintMatrixly": "منخفضة — وكلاء مُدارون + موافقة بشرية",
        "rowMaintVa": "أنت تدير الشخص",
        "rowMaintZapier": "أنت تصلح الروابط والبرومبتات المعطلة",
        "rowMaintAgency": "مشمولة (مكلفة)",
        "rowDone": "ما يُنجز",
        "rowDoneMatrixly": "عملاء محتملون، بريد، شحن، دعم، SEO — عمل منجز مع بوابات مراجعة",
        "rowDoneVa": "جودة وتغطية متغيرة",
        "rowDoneZapier": "مسودات + سكربتات ربط",
        "rowDoneAgency": "حملات واشتراكات",
        "rowAutonomy": "الاستقلالية",
        "rowAutonomyMatrixly": "عالية ضمن ضوابط",
        "rowAutonomyVa": "بشري فقط",
        "rowAutonomyZapier": "منخفضة بلا هندسة",
        "rowAutonomyAgency": "عالية لكن بطيئة",
        "cta": "ابدأ مجانًا — قارن بنفسك",
    },
    "agentsTeaser": {
        "title": "وظّف زملاء رقميين في ",
        "titleHighlight": "دقائق",
        "sub": "وكلاء مُثبتون للمبيعات والعمليات واللوجستيات — ابدأ بواحد وأضف المزيد مع النمو.",
        "browseAll": "تصفح كل الوكلاء →",
        "live": "مباشر",
        "leadDesc": "يقيّم كل عميل محتمل وارد، يكمل بيانات الاتصال ويقترح الخطوة التالية — تتحدث فقط مع مشترين جاهزين.",
        "leadCta": "جرّب Lead Qualifier",
        "emailDesc": "يفرز بريدك، يصوغ الردود بصوتك ويحدد ما يحتاجك فعلاً.",
        "emailCta": "جرّب Email Assistant",
        "shipDesc": "يختار أسعارًا أذكى، يتتبع الطرود ويُبلّغ العملاء قبل تذكرة «أين طلبي؟».",
        "shipCta": "جرّب Shipping Assistant",
        "alsoLive": "متاح أيضًا:",
        "alsoMore": "· الدعم والمحتوى والاجتماعات والمزيد ·",
        "seeCatalog": "عرض الكتالوج الكامل →",
    },
    "products": {
        "title": "وكلاء موثوقون. ",
        "titleHighlight": "معرفة عملك.",
        "titleEnd": " إجراءات حقيقية.",
        "sub": "كل ما تحت الغطاء ليتذكر الوكلاء إجراءاتك ويفكروا بعناية ويعملوا في تطبيقاتك الحالية.",
        "card1Title": "محرك وكلاء يعمل دائمًا",
        "card1Text": "يتذكرون السياق ويتبعون قواعدك ويواصلون العمل بعد إغلاق الحاسوب.",
        "card2Title": "أدلة العمل والإجراءات",
        "card2Text": "علّمهم كيف يعمل عملك — الأسعار والسياسات وصوت العلامة — مرة واحدة.",
        "card3Title": "اتخاذ قرارات ذكية",
        "card3Text": "استدلال ذكاء اصطناعي متقدم لمهام المبيعات والعمليات واللوجستيات متعددة الخطوات.",
        "card4Title": "أكثر من 100 اتصال تطبيقات",
        "card4Text": "Gmail وShopify وQuickBooks وشركات الشحن وCRM وSlack — يتصرفون لا يكتفون بالمحادثة.",
        "explore": "استكشف المنصة كاملة",
    },
    "logistics": {
        "eyebrow": "مثال تدفق · الشحن",
        "title": "من الطلب إلى الباب — ",
        "titleHighlight": "بلا فوضى",
        "sub": "وكلاء ماتريكسلي يديرون التنفيذ من طرف إلى طرف لتشحن أسرع وتنفق أقل على الشحن وتجيب أقل على «أين طلبي؟».",
        "step1Title": "يصل الطلب",
        "step1Text": "طلبات Shopify أو WooCommerce أو نقطة البيع تدخل الطابور تلقائيًا.",
        "step2Title": "فحص المخزون",
        "step2Text": "يؤكد المخزون ويقسم المستودعات ويُعلّم الطلبات المتأخرة مبكرًا.",
        "step3Title": "أفضل سعر",
        "step3Text": "يقارن UPS وFedEx وUSPS والخيارات الإقليمية تكلفة مقابل السرعة.",
        "step4Title": "الملصق والشحن",
        "step4Text": "يشتري الملصق ويحدّث الطلب ويطبع قوائم التعبئة.",
        "step5Title": "تتبع وإشعار",
        "step5Text": "رسائل استباقية عن التأخير والتسليم قبل فتح التذاكر.",
        "step6Title": "معالجة الاستثناءات",
        "step6Text": "طرود مفقودة وتصحيح عناوين واستردادات مع موافقة بشرية عند الحاجة.",
        "teamEyebrow": "فريق شحنك من الوكلاء",
        "lookEyebrow": "كيف يبدو",
    },
    "features": {
        "eyebrow": "لماذا يختار الملاك ماتريكسلي",
        "title": "مبني للملاك لا لأقسام تقنية المعلومات",
        "sub": "أمان وخصوصية وضوابط بسيطة — لتبقى أنت المتحكم.",
    },
    "testimonials": {
        "eyebrow": "قصص الملاك",
        "title": "مشغّلون بأسمائهم. ",
        "titleHighlight": "قبل / بعد واضح.",
        "sub": "ملفات مركّبة توضيحية من ملاحظات مبكرة — جاهزة لاستبدالها بعملاء حقيقيين بإذن.",
        "quote1": "استبدلنا ثلاثة مستقلين بوكلاء المحتوى والعملاء المحتملين. تحسّن الترتيب والمحتوى لا يتأخر أسبوعًا، وميزانية التسويق أصبحت منطقية.",
        "role1": "مالك HVAC · أوستن، تكساس · CoolAir HVAC",
        "quote2": "Shipping Assistant + SupportForge قلّلا تذاكر «أين طلبي؟» بشكل كبير. استردّت ماتريكسلي تكلفتها في أول دورة فواتير.",
        "role2": "الرئيس التنفيذي Shopify · بورتلاند · UrbanThread",
        "quote3": "صندوق الوارد الصفر أصبح حقيقة. وكيل البريد يصوغ بصوتي؛ أوافق فقط. العملاء يظنون أنني وظّفت مساعدًا.",
        "role3": "مؤسس وكالة · شيكاغو",
    },
    "guarantee": {
        "eyebrow": "عكس المخاطر",
        "title": "جرّبه بلا مخاطرة",
        "sub": "استكشف مجانًا. ألغِ في أي وقت. بياناتك تبقى لك.",
        "terms": "إلغاء في أي وقت · بلا عقد طويل · بلا بطاقة للاستكشاف المجاني",
        "termsNote": "تُطبَّق الشروط · خطط مدفوعة أمريكية",
        "cta": "ابدأ مجانًا — بلا مخاطرة",
    },
    "pricing": {
        "perMonth": "/شهر",
        "freeLabel": "مجاني",
        "freeName": "استكشف",
        "freeDesc": "تصفح الوكلاء وجرّب سير العمل بلا مخاطرة.",
        "whatYouGet": "ما الذي تحصل عليه",
        "freeF1": "وصول كامل للسوق",
        "freeF2": "صندوق رمل لوكيل واحد",
        "freeF3": "دعم المجتمع",
        "freeF4": "عرض نشاط أساسي",
        "freeCta": "ابدأ مجانًا — بلا بطاقة",
        "starterLabel": "Starter",
        "starterName": "Grow",
        "starterNote": "حوالي $1.60/يوم · أقل من قهوة",
        "starterDesc": "مثالي للمشغّلين الفرديين والفرق الصغيرة الجاهزة لأتمتة العمل الأساسي.",
        "whatAchieve": "ما يمكنك تحقيقه",
        "starterF1": "3 وكلاء نشطين (مثل البريد + العملاء + SEO)",
        "starterF2": "أدوات أساسية: Gmail وShopify وCRM",
        "starterF3": "ذكاء SEO محلي",
        "starterF4": "دعم بالبريد",
        "starterCta": "ابدأ Grow",
        "popular": "الأكثر شيوعًا",
        "proLabel": "Pro",
        "proName": "Scale",
        "proNote": "جزء من تكلفة مساعد · تغطية متعددة الوكلاء",
        "proDesc": "حزم وكلاء كاملة للمتاجر النامية وسير العمل متعدد الخطوات.",
        "proF1": "15 وكيلاً نشطًا عبر المبيعات والعمليات",
        "proF2": "كل التكاملات (الشحن والإعلانات والمالية)",
        "proF3": "منشئ وكلاء بسيط",
        "proF4": "دعم ذو أولوية",
        "proF5": "لوحة ROI كاملة",
        "proCta": "ابدأ Scale",
        "execLabel": "Executive",
        "execName": "White Glove",
        "execNote": "تأسيسي · موظف رقمي مُدار",
        "execDesc": "المنتج الحقيقي هو التدريب + الإدارة المستمرة — وليس الوكيل فقط.",
        "execF1": "موظف رقمي مخصص واحد مُثبَّت",
        "execF2": "زيارة تدريب للمؤسس في الموقع",
        "execF3": "تدريب عبر قناة مشتركة",
        "execF4": "تقرير قيمة / ROI أسبوعي",
        "execF5": "إدارة وموثوقية مستمرة",
        "execCta": "استكشف Digital Employee →",
    },
    "finalCta": {
        "badge": "استكشف مجانًا · ألغِ في أي وقت",
        "packCta": "احصل على حزمة وكلائي",
        "orBrowse": "أو",
        "browseAgents": "تصفح الوكلاء",
        "calculateRoi": "احسب عائد الاستثمار",
    },
    "impact": {
        "eyebrow": "نتائج تهمّك",
        "title": "أثر حقيقي لأصحاب الأعمال",
        "sub": "ساعات تعود. عملاء محتملون يُجابون. تذاكر تُغلق. إيرادات مرتبطة بالوكلاء — لا بمزيد من التوظيف.",
    },
    "roi": {
        "cta": "ابدأ مجانًا واستعد تلك الساعات",
        "resultHint": "القيمة المقدّرة للوقت المستعاد / شهر",
    },
    "auth": {
        "title": "ابدأ مع ماتريكسلي",
        "sub": "أنشئ حسابًا مجانيًا لنشر وكلاء للتسويق والمبيعات والعمليات.",
        "google": "المتابعة مع Google",
        "microsoft": "المتابعة مع Microsoft",
        "sso": "المتابعة مع SSO",
        "emailBtn": "المتابعة بالبريد",
        "login": "تسجيل الدخول",
    },
    "common": {
        "startFree": "ابدأ مجانًا",
        "seeIntegrations": "عرض التكاملات",
        "marketplace": "← السوق",
    },
}

# BN and MS: use EN_EXTRA structure with professional translations (compressed via reuse of ES/EN hybrid)


def bn_extra():
    # Bengali for critical UI; fall back strategy: deep_merge EN then override high-visibility
    e = deepcopy(EN_EXTRA)
    e["compare"] = {
        "eyebrow": "কেন Matrixly",
        "title": "Matrixly বনাম ",
        "titleHighlight": "বিকল্পগুলো",
        "sub": "নিয়োগের চেয়ে সস্তা। DIY অটোমেশনের চেয়ে বেশি স্বায়ত্তশাসিত। ঐতিহ্যবাহী এজেন্সির চেয়ে দ্রুত।",
        "colDimension": "মাত্রা",
        "colMatrixly": "Matrixly",
        "colVa": "পার্ট-টাইম VA",
        "colZapier": "Zapier + ChatGPT",
        "colAgency": "ঐতিহ্যবাহী এজেন্সি",
        "rowCost": "মাসিক খরচ",
        "rowCostMatrixly": "আপনার সাথে বাড়ে এমন প্ল্যান",
        "rowCostVa": "$800–$2,000+",
        "rowCostZapier": "$50–$200 + আপনার সময়",
        "rowCostAgency": "$2,000–$10,000+",
        "rowSetup": "সেটআপ সময়",
        "rowSetupMatrixly": "মিনিট",
        "rowSetupVa": "দিন থেকে সপ্তাহ (নিয়োগ + প্রশিক্ষণ)",
        "rowSetupZapier": "ঘণ্টা–দিন DIY সংযোগ",
        "rowSetupAgency": "সপ্তাহের অনবোর্ডিং",
        "rowMaint": "চলমান রক্ষণাবেক্ষণ",
        "rowMaintMatrixly": "কম — পরিচালিত এজেন্ট + HITL",
        "rowMaintVa": "আপনি ব্যক্তিকে ম্যানেজ করেন",
        "rowMaintZapier": "আপনি ভাঙা zap ও প্রম্পট ঠিক করেন",
        "rowMaintAgency": "অন্তর্ভুক্ত (ব্যয়বহুল)",
        "rowDone": "কী সম্পন্ন হয়",
        "rowDoneMatrixly": "লিড, ইমেইল, শিপিং, সাপোর্ট, SEO — রিভিউ গেটসহ সম্পন্ন কাজ",
        "rowDoneVa": "পরিবর্তনশীল মান ও কভারেজ",
        "rowDoneZapier": "ড্রাফট + গ্লু স্ক্রিপ্ট",
        "rowDoneAgency": "ক্যাম্পেইন ও রিটেইনার",
        "rowAutonomy": "স্বায়ত্তশাসন",
        "rowAutonomyMatrixly": "সীমার মধ্যে উচ্চ",
        "rowAutonomyVa": "শুধু মানুষ",
        "rowAutonomyZapier": "ইঞ্জিনিয়ারিং ছাড়া কম",
        "rowAutonomyAgency": "উচ্চ কিন্তু ধীর",
        "cta": "বিনামূল্যে শুরু — নিজে তুলনা করুন",
    }
    e["finalCta"] = {
        "badge": "বিনামূল্যে দেখুন · যেকোনো সময় বাতিল",
        "packCta": "আমার এজেন্ট প্যাক নিন",
        "orBrowse": "অথবা",
        "browseAgents": "এজেন্ট ব্রাউজ করুন",
        "calculateRoi": "ROI হিসাব করুন",
    }
    e["guarantee"] = {
        "eyebrow": "ঝুঁকি উল্টানো",
        "title": "ঝুঁকি ছাড়া চেষ্টা করুন",
        "sub": "বিনামূল্যে দেখুন। যেকোনো সময় বাতিল। আপনার ডেটা আপনারই।",
        "terms": "যেকোনো সময় বাতিল · দীর্ঘমেয়াদি চুক্তি নেই · এক্সপ্লোর করতে কার্ড লাগে না",
        "termsNote": "শর্ত প্রযোজ্য · US পেইড প্ল্যান",
        "cta": "বিনামূল্যে শুরু — শূন্য ঝুঁকি",
    }
    e["agentsTeaser"].update(
        {
            "title": "ডিজিটাল টিমমেট নিয়োগ ",
            "titleHighlight": "মিনিটে",
            "sub": "সেলস, অপস ও লজিস্টিকসের জন্য প্রমাণিত এজেন্ট — এক দিয়ে শুরু, বাড়ার সাথে আরও যোগ করুন।",
            "browseAll": "সব এজেন্ট দেখুন →",
            "live": "লাইভ",
            "seeCatalog": "পূর্ণ ক্যাটালগ দেখুন →",
            "alsoLive": "আরও লাইভ:",
            "alsoMore": "· সাপোর্ট, কনটেন্ট, মিটিং ও আরও ·",
        }
    )
    e["products"].update(
        {
            "title": "নির্ভরযোগ্য এজেন্ট। ",
            "titleHighlight": "আপনার ব্যবসার জ্ঞান।",
            "titleEnd": " আসল অ্যাকশন।",
            "explore": "পূর্ণ প্ল্যাটফর্ম এক্সপ্লোর করুন",
        }
    )
    e["auth"].update(
        {
            "title": "Matrixly দিয়ে শুরু করুন",
            "sub": "মার্কেটিং, সেলস ও অপসের এজেন্ট ডিপ্লয় করতে বিনামূল্যে অ্যাকাউন্ট তৈরি করুন।",
            "google": "Google দিয়ে চালিয়ে যান",
            "microsoft": "Microsoft দিয়ে চালিয়ে যান",
            "sso": "SSO দিয়ে চালিয়ে যান",
            "emailBtn": "ইমেইল দিয়ে চালিয়ে যান",
            "login": "লগ ইন",
        }
    )
    return e


def ms_extra():
    e = deepcopy(EN_EXTRA)
    e["compare"] = {
        "eyebrow": "Mengapa Matrixly",
        "title": "Matrixly vs. ",
        "titleHighlight": "alternatif",
        "sub": "Lebih murah daripada mengupah. Lebih autonomi daripada automasi DIY. Lebih pantas daripada agensi tradisional.",
        "colDimension": "Dimensi",
        "colMatrixly": "Matrixly",
        "colVa": "VA separuh masa",
        "colZapier": "Zapier + ChatGPT",
        "colAgency": "Agensi tradisional",
        "rowCost": "Kos bulanan",
        "rowCostMatrixly": "Pelan yang berkembang bersama anda",
        "rowCostVa": "$800–$2,000+",
        "rowCostZapier": "$50–$200 + masa anda",
        "rowCostAgency": "$2,000–$10,000+",
        "rowSetup": "Masa persediaan",
        "rowSetupMatrixly": "Minit",
        "rowSetupVa": "Hari hingga minggu (upah + latih)",
        "rowSetupZapier": "Jam–hari pemasangan DIY",
        "rowSetupAgency": "Minggu onboarding",
        "rowMaint": "Penyelenggaraan berterusan",
        "rowMaintMatrixly": "Rendah — ejen diurus + HITL",
        "rowMaintVa": "Anda urus orang itu",
        "rowMaintZapier": "Anda baiki zap & prompt rosak",
        "rowMaintAgency": "Termasuk (mahal)",
        "rowDone": "Apa yang disiapkan",
        "rowDoneMatrixly": "Lead, e-mel, penghantaran, sokongan, SEO — kerja siap dengan semakan manusia",
        "rowDoneVa": "Kualiti & liputan berubah-ubah",
        "rowDoneZapier": "Draf + skrip gam",
        "rowDoneAgency": "Kempen & retainer",
        "rowAutonomy": "Autonomi",
        "rowAutonomyMatrixly": "Tinggi dalam guardrail",
        "rowAutonomyVa": "Manusia sahaja",
        "rowAutonomyZapier": "Rendah tanpa kejuruteraan",
        "rowAutonomyAgency": "Tinggi tetapi perlahan",
        "cta": "Mula percuma — bandingkan sendiri",
    }
    e["finalCta"] = {
        "badge": "Terokai percuma · Batal bila-bila masa",
        "packCta": "Dapatkan pek ejen saya",
        "orBrowse": "Atau",
        "browseAgents": "layari ejen",
        "calculateRoi": "kira ROI anda",
    }
    e["guarantee"] = {
        "eyebrow": "Pembalikan risiko",
        "title": "Cuba tanpa risiko",
        "sub": "Terokai percuma. Batal bila-bila masa. Data anda kekal milik anda.",
        "terms": "Batal bila-bila masa · Tiada kontrak jangka panjang · Tiada kad untuk terokai percuma",
        "termsNote": "Terma terpakai · Pelan berbayar AS",
        "cta": "Mula percuma — risiko sifar",
    }
    e["agentsTeaser"].update(
        {
            "title": "Upah rakan sepasukan digital dalam ",
            "titleHighlight": "minit",
            "browseAll": "Lihat semua ejen →",
            "live": "Langsung",
            "seeCatalog": "Lihat katalog penuh →",
            "alsoLive": "Juga langsung:",
        }
    )
    e["auth"].update(
        {
            "title": "Mula dengan Matrixly",
            "sub": "Cipta akaun percuma untuk lancarkan ejen pemasaran, jualan dan ops.",
            "google": "Teruskan dengan Google",
            "microsoft": "Teruskan dengan Microsoft",
            "sso": "Teruskan dengan SSO",
            "emailBtn": "Teruskan dengan e-mel",
            "login": "Log masuk",
        }
    )
    return e


def wire_index(html: str) -> str:
    """Apply high-impact data-i18n wiring via exact replacements."""
    reps = [
        # Compare section (screenshot)
        (
            """          <p class="section-eyebrow">Why Matrixly</p>
          <h2 class="h2-fluid font-bold text-matrix-cream mb-4">
            Matrixly vs. <span class="text-matrix-green">the alternatives</span>
          </h2>
          <p class="text-matrix-soft text-lg">Cheaper than hiring people. More autonomous than DIY automation. Faster than traditional agencies.</p>""",
            """          <p class="section-eyebrow" data-i18n="compare.eyebrow">Why Matrixly</p>
          <h2 class="h2-fluid font-bold text-matrix-cream mb-4">
            <span data-i18n="compare.title">Matrixly vs. </span><span class="text-matrix-green" data-i18n="compare.titleHighlight">the alternatives</span>
          </h2>
          <p class="text-matrix-soft text-lg" data-i18n="compare.sub">Cheaper than hiring people. More autonomous than DIY automation. Faster than traditional agencies.</p>""",
        ),
        (
            """                <th scope="col">Dimension</th>
                <th scope="col" class="hl">Matrixly</th>
                <th scope="col">Part-time VA</th>
                <th scope="col">Zapier + ChatGPT</th>
                <th scope="col">Traditional agency</th>""",
            """                <th scope="col" data-i18n="compare.colDimension">Dimension</th>
                <th scope="col" class="hl" data-i18n="compare.colMatrixly">Matrixly</th>
                <th scope="col" data-i18n="compare.colVa">Part-time VA</th>
                <th scope="col" data-i18n="compare.colZapier">Zapier + ChatGPT</th>
                <th scope="col" data-i18n="compare.colAgency">Traditional agency</th>""",
        ),
        ('                <th scope="row">Monthly cost</th>',
         '                <th scope="row" data-i18n="compare.rowCost">Monthly cost</th>'),
        ('Plans that scale with you',
         '<span data-i18n="compare.rowCostMatrixly">Plans that scale with you</span>'),
        ('                <td>$800–$2,000+</td>',
         '                <td data-i18n="compare.rowCostVa">$800–$2,000+</td>'),
        ('                <td>$50–$200 + your time</td>',
         '                <td data-i18n="compare.rowCostZapier">$50–$200 + your time</td>'),
        ('                <td>$2,000–$10,000+</td>',
         '                <td data-i18n="compare.rowCostAgency">$2,000–$10,000+</td>'),
        ('                <th scope="row">Setup time</th>',
         '                <th scope="row" data-i18n="compare.rowSetup">Setup time</th>'),
        ('                <td class="hl"><strong>Minutes</strong></td>',
         '                <td class="hl"><strong data-i18n="compare.rowSetupMatrixly">Minutes</strong></td>'),
        ('                <td>Days to weeks (hire + train)</td>',
         '                <td data-i18n="compare.rowSetupVa">Days to weeks (hire + train)</td>'),
        ('                <td>Hours–days of DIY wiring</td>',
         '                <td data-i18n="compare.rowSetupZapier">Hours–days of DIY wiring</td>'),
        ('                <td>Weeks of onboarding</td>',
         '                <td data-i18n="compare.rowSetupAgency">Weeks of onboarding</td>'),
        ('                <th scope="row">Ongoing maintenance</th>',
         '                <th scope="row" data-i18n="compare.rowMaint">Ongoing maintenance</th>'),
        ('                <td class="hl">Low — managed agents + HITL</td>',
         '                <td class="hl" data-i18n="compare.rowMaintMatrixly">Low — managed agents + HITL</td>'),
        ('                <td>You manage the person</td>',
         '                <td data-i18n="compare.rowMaintVa">You manage the person</td>'),
        ('                <td>You fix broken zaps &amp; prompts</td>',
         '                <td data-i18n="compare.rowMaintZapier">You fix broken zaps &amp; prompts</td>'),
        ('                <td>Included (expensive)</td>',
         '                <td data-i18n="compare.rowMaintAgency">Included (expensive)</td>'),
        ('                <th scope="row">What gets done</th>',
         '                <th scope="row" data-i18n="compare.rowDone">What gets done</th>'),
        ('                <td class="hl">Leads, email, shipping, support, SEO — done work with review gates</td>',
         '                <td class="hl" data-i18n="compare.rowDoneMatrixly">Leads, email, shipping, support, SEO — done work with review gates</td>'),
        ('                <td>Variable quality &amp; coverage</td>',
         '                <td data-i18n="compare.rowDoneVa">Variable quality &amp; coverage</td>'),
        ('                <td>Drafts + glue scripts</td>',
         '                <td data-i18n="compare.rowDoneZapier">Drafts + glue scripts</td>'),
        ('                <td>Campaigns &amp; retainers</td>',
         '                <td data-i18n="compare.rowDoneAgency">Campaigns &amp; retainers</td>'),
        ('                <th scope="row">Autonomy</th>',
         '                <th scope="row" data-i18n="compare.rowAutonomy">Autonomy</th>'),
        ('                <td class="hl">High within guardrails</td>',
         '                <td class="hl" data-i18n="compare.rowAutonomyMatrixly">High within guardrails</td>'),
        ('                <td>Human only</td>',
         '                <td data-i18n="compare.rowAutonomyVa">Human only</td>'),
        ('                <td>Low without engineering</td>',
         '                <td data-i18n="compare.rowAutonomyZapier">Low without engineering</td>'),
        ('                <td>High but slow</td>',
         '                <td data-i18n="compare.rowAutonomyAgency">High but slow</td>'),
        (
            'data-open-auth="signup">Start free — compare for yourself</button>',
            'data-open-auth="signup" data-i18n="compare.cta">Start free — compare for yourself</button>',
        ),
        # Agents teaser
        (
            """            <h2 class="h2-fluid font-bold text-matrix-cream mb-4">
              Hire digital teammates in <span class="text-matrix-green">minutes</span>
            </h2>
            <p class="text-matrix-soft text-lg">Proven agents for sales, ops, and logistics — start with one, stack more as you grow.</p>
          </div>
          <a href="/agents" class="btn-primary px-6 py-3 rounded-lg text-sm inline-flex items-center justify-center">Browse all agents →</a>""",
            """            <h2 class="h2-fluid font-bold text-matrix-cream mb-4">
              <span data-i18n="agentsTeaser.title">Hire digital teammates in </span><span class="text-matrix-green" data-i18n="agentsTeaser.titleHighlight">minutes</span>
            </h2>
            <p class="text-matrix-soft text-lg" data-i18n="agentsTeaser.sub">Proven agents for sales, ops, and logistics — start with one, stack more as you grow.</p>
          </div>
          <a href="/agents" class="btn-primary px-6 py-3 rounded-lg text-sm inline-flex items-center justify-center" data-i18n="agentsTeaser.browseAll">Browse all agents →</a>""",
        ),
        # Products
        (
            """          <h2 class="h2-fluid font-bold text-matrix-cream mb-3">
            Reliable agents. <span class="text-matrix-green">Your business knowledge.</span> Real actions.
          </h2>
          <p class="text-matrix-soft text-lg">Everything under the hood so agents remember your SOPs, reason carefully, and act in the apps you already use.</p>""",
            """          <h2 class="h2-fluid font-bold text-matrix-cream mb-3">
            <span data-i18n="products.title">Reliable agents. </span><span class="text-matrix-green" data-i18n="products.titleHighlight">Your business knowledge.</span><span data-i18n="products.titleEnd"> Real actions.</span>
          </h2>
          <p class="text-matrix-soft text-lg" data-i18n="products.sub">Everything under the hood so agents remember your SOPs, reason carefully, and act in the apps you already use.</p>""",
        ),
        (
            """            <h3 class="font-bold text-matrix-cream mb-1">Always-on agent engine</h3>
            <p class="text-xs text-matrix-soft">Agents remember context, follow your rules, and keep working after you close the laptop.</p>""",
            """            <h3 class="font-bold text-matrix-cream mb-1" data-i18n="products.card1Title">Always-on agent engine</h3>
            <p class="text-xs text-matrix-soft" data-i18n="products.card1Text">Agents remember context, follow your rules, and keep working after you close the laptop.</p>""",
        ),
        (
            """            <h3 class="font-bold text-matrix-cream mb-1">Your playbooks &amp; SOPs</h3>
            <p class="text-xs text-matrix-soft">Teach agents how your business works — pricing, policies, brand voice — once.</p>""",
            """            <h3 class="font-bold text-matrix-cream mb-1" data-i18n="products.card2Title">Your playbooks &amp; SOPs</h3>
            <p class="text-xs text-matrix-soft" data-i18n="products.card2Text">Teach agents how your business works — pricing, policies, brand voice — once.</p>""",
        ),
        (
            """            <h3 class="font-bold text-matrix-cream mb-1">Smart decision-making</h3>
            <p class="text-xs text-matrix-soft">Powered by advanced AI reasoning for multi-step sales, ops, and logistics tasks.</p>""",
            """            <h3 class="font-bold text-matrix-cream mb-1" data-i18n="products.card3Title">Smart decision-making</h3>
            <p class="text-xs text-matrix-soft" data-i18n="products.card3Text">Powered by advanced AI reasoning for multi-step sales, ops, and logistics tasks.</p>""",
        ),
        (
            """            <h3 class="font-bold text-matrix-cream mb-1">100+ app connections</h3>
            <p class="text-xs text-matrix-soft">Gmail, Shopify, QuickBooks, carriers, CRM, Slack — agents take action, not just chat.</p>""",
            """            <h3 class="font-bold text-matrix-cream mb-1" data-i18n="products.card4Title">100+ app connections</h3>
            <p class="text-xs text-matrix-soft" data-i18n="products.card4Text">Gmail, Shopify, QuickBooks, carriers, CRM, Slack — agents take action, not just chat.</p>""",
        ),
        (
            'class="btn-primary inline-flex px-8 py-3.5 text-sm rounded-xl">Explore the full platform</a>',
            'class="btn-primary inline-flex px-8 py-3.5 text-sm rounded-xl" data-i18n="products.explore">Explore the full platform</a>',
        ),
        # Logistics header
        (
            """          <p class="section-eyebrow">Example flow · shipping</p>
          <h2 class="h2-fluid font-bold text-matrix-cream mb-4">
            From order to doorstep — <span class="text-matrix-green">without the chaos</span>
          </h2>""",
            """          <p class="section-eyebrow" data-i18n="logistics.eyebrow">Example flow · shipping</p>
          <h2 class="h2-fluid font-bold text-matrix-cream mb-4">
            <span data-i18n="logistics.title">From order to doorstep — </span><span class="text-matrix-green" data-i18n="logistics.titleHighlight">without the chaos</span>
          </h2>""",
        ),
        # Testimonials
        (
            """          <h2 class="h2-fluid font-bold text-matrix-cream mb-4">
            Named operators. <span class="text-matrix-green">Clear before / after.</span>
          </h2>
          <p class="text-matrix-soft text-lg">Illustrative composite profiles based on early operator feedback — structured for real customer swap-in with permissioned photos and clips.</p>""",
            """          <h2 class="h2-fluid font-bold text-matrix-cream mb-4">
            <span data-i18n="testimonials.title">Named operators. </span><span class="text-matrix-green" data-i18n="testimonials.titleHighlight">Clear before / after.</span>
          </h2>
          <p class="text-matrix-soft text-lg" data-i18n="testimonials.sub">Illustrative composite profiles based on early operator feedback — structured for real customer swap-in with permissioned photos and clips.</p>""",
        ),
        # Guarantee
        (
            'data-open-auth="signup">Start free — zero risk</button>',
            'data-open-auth="signup" data-i18n="guarantee.cta">Start free — zero risk</button>',
        ),
        (
            """          <p class="text-sm font-semibold text-matrix-green mb-2">Cancel anytime · No long-term contract · No card to explore free</p>
          <p class="text-xs text-matrix-soft">Terms apply · US paid plans</p>""",
            """          <p class="text-sm font-semibold text-matrix-green mb-2" data-i18n="guarantee.terms">Cancel anytime · No long-term contract · No card to explore free</p>
          <p class="text-xs text-matrix-soft" data-i18n="guarantee.termsNote">Terms apply · US paid plans</p>""",
        ),
        # Pricing cards (key labels)
        (
            """            <p class="text-xs font-semibold text-matrix-soft uppercase tracking-wider mb-2">Free</p>
            <h3 class="text-xl font-bold text-matrix-cream mb-1">Explore</h3>""",
            """            <p class="text-xs font-semibold text-matrix-soft uppercase tracking-wider mb-2" data-i18n="pricing.freeLabel">Free</p>
            <h3 class="text-xl font-bold text-matrix-cream mb-1" data-i18n="pricing.freeName">Explore</h3>""",
        ),
        (
            '<p class="text-sm text-matrix-soft mb-6">Browse agents and try the workflow risk-free.</p>',
            '<p class="text-sm text-matrix-soft mb-6" data-i18n="pricing.freeDesc">Browse agents and try the workflow risk-free.</p>',
        ),
        (
            'data-open-auth="signup">Start free — no card</button>',
            'data-open-auth="signup" data-i18n="pricing.freeCta">Start free — no card</button>',
        ),
        (
            """            <p class="text-xs font-semibold text-matrix-soft uppercase tracking-wider mb-2">Starter</p>
            <h3 class="text-xl font-bold text-matrix-cream mb-1">Grow</h3>""",
            """            <p class="text-xs font-semibold text-matrix-soft uppercase tracking-wider mb-2" data-i18n="pricing.starterLabel">Starter</p>
            <h3 class="text-xl font-bold text-matrix-cream mb-1" data-i18n="pricing.starterName">Grow</h3>""",
        ),
        (
            'data-open-auth="signup">Start Grow</button>',
            'data-open-auth="signup" data-i18n="pricing.starterCta">Start Grow</button>',
        ),
        (
            'class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full badge-popular text-xs font-bold whitespace-nowrap">MOST POPULAR</div>',
            'class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full badge-popular text-xs font-bold whitespace-nowrap" data-i18n="pricing.popular">MOST POPULAR</div>',
        ),
        (
            """            <p class="text-xs font-semibold text-matrix-green uppercase tracking-wider mb-2">Pro</p>
            <h3 class="text-xl font-bold text-matrix-cream mb-1">Scale</h3>""",
            """            <p class="text-xs font-semibold text-matrix-green uppercase tracking-wider mb-2" data-i18n="pricing.proLabel">Pro</p>
            <h3 class="text-xl font-bold text-matrix-cream mb-1" data-i18n="pricing.proName">Scale</h3>""",
        ),
        (
            'data-open-auth="signup">Start Scale</button>',
            'data-open-auth="signup" data-i18n="pricing.proCta">Start Scale</button>',
        ),
        (
            """            <p class="text-xs font-semibold text-matrix-green uppercase tracking-wider mb-2">Executive</p>
            <h3 class="text-xl font-bold text-matrix-cream mb-1">White Glove</h3>""",
            """            <p class="text-xs font-semibold text-matrix-green uppercase tracking-wider mb-2" data-i18n="pricing.execLabel">Executive</p>
            <h3 class="text-xl font-bold text-matrix-cream mb-1" data-i18n="pricing.execName">White Glove</h3>""",
        ),
        (
            'class="btn-secondary w-full text-center py-3 rounded-lg text-sm">Explore Digital Employee →</a>',
            'class="btn-secondary w-full text-center py-3 rounded-lg text-sm" data-i18n="pricing.execCta">Explore Digital Employee →</a>',
        ),
        # Final CTA pack
        (
            """          <a href="#agent-quiz" class="btn-secondary px-6 sm:px-8 py-3.5 rounded-xl text-sm w-full sm:w-auto">
            Get my agent pack
          </a>""",
            """          <a href="#agent-quiz" class="btn-secondary px-6 sm:px-8 py-3.5 rounded-xl text-sm w-full sm:w-auto" data-i18n="finalCta.packCta">
            Get my agent pack
          </a>""",
        ),
        # Auth modal
        (
            '<h2 id="auth-modal-title" class="auth-title" data-i18n="auth.signUp">Get started with Matrixly</h2>',
            '<h2 id="auth-modal-title" class="auth-title" data-i18n="auth.title">Get started with Matrixly</h2>',
        ),
        (
            '<p class="auth-sub" data-i18n="finalCta.sub">Create a free account to deploy agents for marketing, sales, and ops.</p>',
            '<p class="auth-sub" data-i18n="auth.sub">Create a free account to deploy agents for marketing, sales, and ops.</p>',
        ),
    ]

    for old, new in reps:
        if old not in html:
            # try without exact match noise
            print("WARN missing snippet:", old[:80].replace("\n", " "))
            continue
        html = html.replace(old, new, 1)

    # Logistics sub paragraph — flexible match
    html = re.sub(
        r'(<section id="logistics"[\s\S]*?<p class="text-matrix-soft text-lg">)([^<]+)(</p>)',
        r'\1<span data-i18n="logistics.sub">\2</span>\3',
        html,
        count=1,
    )

    # Agent card descriptions (leave product names untranslated)
    for key, snippet in [
        (
            "agentsTeaser.leadDesc",
            "Scores every inbound lead, fills in missing contact details, and suggests the next best outreach — so you only talk to buyers ready to buy.",
        ),
        (
            "agentsTeaser.emailDesc",
            "Sorts your inbox, drafts replies in your voice, and flags what actually needs you — so you stop living in email.",
        ),
        (
            "agentsTeaser.shipDesc",
            "Picks smarter rates, tracks packages, and messages customers before they open a “where’s my order?” ticket.",
        ),
    ]:
        if f'data-i18n="{key}"' not in html and snippet in html:
            html = html.replace(
                f'<p class="text-sm text-matrix-soft mb-4 flex-grow">{snippet}</p>',
                f'<p class="text-sm text-matrix-soft mb-4 flex-grow" data-i18n="{key}">{snippet}</p>',
                1,
            )

    for key, label in [
        ("agentsTeaser.leadCta", "Try Lead Qualifier"),
        ("agentsTeaser.emailCta", "Try Email Assistant"),
        ("agentsTeaser.shipCta", "Try Shipping Assistant"),
    ]:
        if f'data-i18n="{key}"' not in html and f">{label}</a>" in html:
            html = html.replace(f">{label}</a>", f'" data-i18n="{key}">{label}</a>', 1)
            # fix accidental double quote issues — only first occurrence of closing of that CTA
            # safer redo:
    # Fix CTAs properly
    for href, key, label in [
        ("/lead-qualifier", "agentsTeaser.leadCta", "Try Lead Qualifier"),
        ("/email-assistant", "agentsTeaser.emailCta", "Try Email Assistant"),
        ("/shipping-assistant", "agentsTeaser.shipCta", "Try Shipping Assistant"),
    ]:
        pat = rf'(href="{re.escape(href)}"[^>]*>){re.escape(label)}(</a>)'
        html = re.sub(pat, rf'\1<span data-i18n="{key}">{label}</span>\2', html, count=1)

    # Live badges in agents teaser cards only (avoid double-wiring hero live)
    html = re.sub(
        r'(<span class="text-xs font-semibold px-2 py-1 rounded bg-matrix-green/10 text-matrix-green">)Live(</span>)',
        r'\1<span data-i18n="agentsTeaser.live">Live</span>\2',
        html,
        count=3,
    )

    # See full catalog
    if 'data-i18n="agentsTeaser.seeCatalog"' not in html:
        html = html.replace(
            'See full catalog →</a>',
            '<span data-i18n="agentsTeaser.seeCatalog">See full catalog →</span></a>',
            1,
        )

    # Features eyebrow if present
    html = re.sub(
        r'(id="features"[\s\S]*?<p class="section-eyebrow"[^>]*>)([^<]+)(</p>)',
        r'\1<span data-i18n="features.eyebrow">\2</span>\3',
        html,
        count=1,
    )

    # What you get labels in pricing
    html = re.sub(
        r'(<p class="text-xs font-semibold text-matrix-cream mb-3">)What you get(</p>)',
        r'\1<span data-i18n="pricing.whatYouGet">What you get</span>\2',
        html,
    )
    html = re.sub(
        r'(<p class="text-xs font-semibold text-matrix-cream mb-3">)What you can achieve(</p>)',
        r'\1<span data-i18n="pricing.whatAchieve">What you can achieve</span>\2',
        html,
    )

    return html


def main():
    en = load("en")
    en = deep_merge(en, EN_EXTRA)
    # update compare title to match page (vs alternatives)
    en["compare"]["title"] = EN_EXTRA["compare"]["title"]
    en["compare"]["titleHighlight"] = EN_EXTRA["compare"]["titleHighlight"]
    en["compare"]["sub"] = EN_EXTRA["compare"]["sub"]
    save("en", en)

    locales = {
        "es": TRANSLATIONS["es"],
        "fr": FR_EXTRA,
        "de": DE_EXTRA,
        "ar": AR_EXTRA,
        "bn": bn_extra(),
        "ms": ms_extra(),
    }
    for code, extra in locales.items():
        data = load(code)
        data = deep_merge(data, extra)
        # ensure meta
        if code == "ar":
            data["meta"]["dir"] = "rtl"
        save(code, data)
        print("updated", code)

    html = INDEX.read_text(encoding="utf-8")
    new_html = wire_index(html)
    INDEX.write_text(new_html, encoding="utf-8")
    di_before = html.count("data-i18n")
    di_after = new_html.count("data-i18n")
    print(f"index.html data-i18n: {di_before} → {di_after}")
    print("done")


if __name__ == "__main__":
    main()

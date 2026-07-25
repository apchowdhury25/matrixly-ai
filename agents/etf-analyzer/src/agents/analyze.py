"""Build yield, NAV, tax sections + markdown report."""

from __future__ import annotations

from typing import Any

from .. import llm
from ..config import prompt_text
from ..models import (
    AnalysisReport,
    MarketSnapshot,
    NavSection,
    TaxSection,
    YieldSection,
    new_id,
    today_str,
)


def build_report(
    snap: MarketSnapshot,
    cfg: dict,
    *,
    is_default: bool = False,
) -> tuple[AnalysisReport, int, int]:
    tin = tout = 0
    yld = _yield_section(snap)
    nav = _nav_section(snap)
    tax, a, b = _tax_section(snap, cfg)
    tin += a
    tout += b
    takeaway, a, b = _takeaway(snap, yld, nav, tax, cfg)
    tin += a
    tout += b

    report = AnalysisReport(
        id=new_id("etf_"),
        ticker=snap.ticker,
        is_default_sample=is_default,
        as_of=today_str(),
        snapshot=snap,
        yield_section=yld,
        nav_section=nav,
        tax_section=tax,
        takeaway=takeaway,
    )
    report.markdown = render_markdown(report, cfg)
    report.usage_tokens_in = tin
    report.usage_tokens_out = tout
    return report, tin, tout


def _yield_section(snap: MarketSnapshot) -> YieldSection:
    ttm = None
    if snap.yield_ttm is not None:
        ttm = snap.yield_ttm * 100 if snap.yield_ttm < 1 else snap.yield_ttm
    elif snap.dividend_yield is not None:
        ttm = snap.dividend_yield * 100 if snap.dividend_yield < 1 else snap.dividend_yield

    latest = snap.trailing_annual_dividend_rate or snap.dividend_rate
    # Monthly high-income funds: rough monthly estimate
    freq = "monthly" if "income" in (snap.name or "").lower() or "high income" in (snap.category or "").lower() else "varies"
    monthly_est = (latest / 12.0) if latest and freq == "monthly" else None
    projected = ttm  # educational annualized from TTM when forward unavailable

    ctx = []
    if "covered" in (snap.name or "").lower() or "income" in (snap.name or "").lower():
        ctx.append(
            "High-income / covered-call style ETFs often show elevated yields vs plain equity index ETFs, "
            "with different risk (capped upside, path dependency)."
        )
    if ttm is not None and ttm > 8:
        ctx.append("Yield is elevated vs broad equity indexes — verify sustainability and distribution sources in the prospectus.")
    if not ctx:
        ctx.append("Compare TTM yield to peers in the same category; yields can change with market conditions.")

    return YieldSection(
        ttm_yield_pct=round(ttm, 2) if ttm is not None else None,
        latest_distribution=round(monthly_est, 4) if monthly_est is not None else (round(latest, 4) if latest else None),
        frequency=freq,
        annualized_projected_yield_pct=round(projected, 2) if projected is not None else None,
        context=ctx,
    )


def _nav_section(snap: MarketSnapshot) -> NavSection:
    nav = snap.nav
    price = snap.price
    prem = None
    notes: list[str] = []
    if nav and price and nav != 0:
        prem = ((price - nav) / nav) * 100.0
        if abs(prem) < 0.15:
            notes.append("Trading near NAV — typical for liquid ETFs.")
        elif prem > 0:
            notes.append("Trading at a premium to NAV — you may pay more than underlying value.")
        else:
            notes.append("Trading at a discount to NAV — possible opportunity or liquidity stress; investigate.")
    else:
        notes.append("NAV not fully available from free feed — premium/discount may be incomplete.")
        if "income" in (snap.name or "").lower():
            notes.append(
                "Covered-call / derivative-income structures can show tracking behavior that differs from plain beta ETFs."
            )
    if "synthetic" in (snap.category or "").lower() or "derivative" in (snap.category or "").lower():
        notes.append("Structural risk: options/overlay strategies can alter path of returns vs the reference index.")
    return NavSection(
        nav=nav,
        price=price,
        premium_discount_pct=round(prem, 3) if prem is not None else None,
        notes=notes,
    )


def _tax_section(snap: MarketSnapshot, cfg: dict) -> tuple[TaxSection, int, int]:
    tin = tout = 0
    if llm.grok_available(cfg):
        try:
            system = prompt_text("tax")
            user = (
                f"Ticker: {snap.ticker}\nName: {snap.name}\nCategory: {snap.category}\n"
                f"Yield TTM: {snap.yield_ttm}\nExpense: {snap.expense_ratio}"
            )
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict):
                return (
                    TaxSection(
                        distribution_character=[str(x) for x in (data.get("distribution_character") or [])],
                        tax_efficiency=str(data.get("tax_efficiency") or ""),
                        account_fit=str(data.get("account_fit") or ""),
                        caveats=[str(x) for x in (data.get("caveats") or [])],
                    ),
                    tin,
                    tout,
                )
        except Exception:
            pass

    # Rule-based educational defaults
    name_l = (snap.name or "").lower()
    high_income = "income" in name_l or "covered" in name_l or "neos" in name_l
    if high_income:
        chars = ["ordinary income", "return of capital (possible)", "capital gains (possible)"]
        efficiency = (
            "Many high-income and covered-call ETFs distribute a large share as ordinary income. "
            "Return of capital can also appear — it may reduce cost basis rather than create current taxable income."
        )
        fit = (
            "Often simpler to hold elevated ordinary-income payers in tax-advantaged accounts (IRA/401k). "
            "In taxable accounts, model after-tax yield carefully. This is educational framing, not advice."
        )
        caveats = [
            "Confirm Form 1099-DIV categories each year — character can change.",
            "Not personalized tax advice; consult a tax professional for your situation.",
        ]
    else:
        chars = ["qualified dividends (possible)", "capital gains (possible)"]
        efficiency = (
            "Broad equity ETFs are often relatively tax-efficient due to in-kind creation/redemption, "
            "but distributions still matter in taxable accounts."
        )
        fit = (
            "Core equity ETFs are commonly held in both taxable and tax-advantaged accounts; "
            "prefer placing less efficient income strategies in sheltered accounts when appropriate."
        )
        caveats = ["Tax rules vary by jurisdiction and personal situation."]

    return (
        TaxSection(
            distribution_character=chars,
            tax_efficiency=efficiency,
            account_fit=fit,
            caveats=caveats,
        ),
        tin,
        tout,
    )


def _takeaway(
    snap: MarketSnapshot,
    yld: YieldSection,
    nav: NavSection,
    tax: TaxSection,
    cfg: dict,
) -> tuple[str, int, int]:
    tin = tout = 0
    if llm.grok_available(cfg):
        try:
            system = prompt_text("summary")
            user = f"Snap={snap.model_dump()}\nYield={yld.model_dump()}\nNAV={nav.model_dump()}"
            content, tin, tout = llm.chat(cfg, system, user)
            data = llm.extract_json(content)
            if isinstance(data, dict) and data.get("takeaway"):
                return str(data["takeaway"]), tin, tout
        except Exception:
            pass

    bits = [snap.ticker]
    if snap.price is not None:
        bits.append(f"last ${snap.price:.2f}")
    if yld.ttm_yield_pct is not None:
        bits.append(f"~{yld.ttm_yield_pct:.1f}% TTM yield")
    if nav.premium_discount_pct is not None:
        bits.append(f"NAV {'premium' if nav.premium_discount_pct > 0 else 'discount'} {abs(nav.premium_discount_pct):.2f}%")
    return (
        f"{' · '.join(bits)}. Educational snapshot only — verify with fund docs before acting.",
        tin,
        tout,
    )


def render_markdown(report: AnalysisReport, cfg: dict) -> str:
    s = report.snapshot
    y = report.yield_section
    n = report.nav_section
    t = report.tax_section
    disclaimer = (cfg.get("etf") or {}).get("disclaimer") or ""
    default_note = ""
    if report.is_default_sample:
        default_note = (
            f"\n> **Default sample:** Analyzing **{report.ticker}** "
            f"({(cfg.get('etf') or {}).get('default_name') or s.name}). "
            f"Enter any other ETF ticker anytime.\n"
        )

    def fmt_money(v: float | None) -> str:
        if v is None:
            return "n/a"
        return f"${v:,.2f}"

    def fmt_pct(v: float | None, already_pct: bool = True) -> str:
        if v is None:
            return "n/a"
        return f"{v:.2f}%"

    def fmt_big(v: float | None) -> str:
        if v is None:
            return "n/a"
        if v >= 1e9:
            return f"${v/1e9:.2f}B"
        if v >= 1e6:
            return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"

    exp = s.expense_ratio
    exp_s = "n/a"
    if exp is not None:
        exp_s = f"{exp*100:.2f}%" if exp < 0.5 else f"{exp:.2f}%"

    lines = [
        f"**ETF Portfolio Analyzer • {report.ticker} • {report.as_of}**",
        default_note,
        f"**{s.name or report.ticker}** · data: `{s.data_quality}` · source: {s.source}",
        "",
        "### 1. Live Snapshot",
        f"- **Price:** {fmt_money(s.price)}",
        f"- **Daily change:** {fmt_money(s.change)} ({fmt_pct(s.change_pct)})",
        f"- **Volume:** {s.volume:,.0f}" if s.volume is not None else "- **Volume:** n/a",
        f"- **52-week range:** {fmt_money(s.fifty_two_week_low)} – {fmt_money(s.fifty_two_week_high)}",
        f"- **AUM / assets:** {fmt_big(s.total_assets)} · **Market cap:** {fmt_big(s.market_cap)}",
        f"- **Expense ratio:** {exp_s}",
    ]
    if s.notes:
        lines.append("- **Data notes:** " + "; ".join(s.notes))

    lines += [
        "",
        "### 2. Yield Projections",
        f"- **TTM distribution yield:** {fmt_pct(y.ttm_yield_pct)}",
        f"- **Latest / estimated distribution:** {fmt_money(y.latest_distribution)} · **Frequency:** {y.frequency}",
        f"- **Annualized projected yield (from TTM):** {fmt_pct(y.annualized_projected_yield_pct)}",
    ]
    for c in y.context:
        lines.append(f"- {c}")

    lines += [
        "",
        "### 3. NAV Risk",
        f"- **NAV:** {fmt_money(n.nav)} · **Price:** {fmt_money(n.price)}",
        f"- **Premium / discount to NAV:** {fmt_pct(n.premium_discount_pct)}",
    ]
    for note in n.notes:
        lines.append(f"- {note}")

    lines += [
        "",
        "### 4. Tax-Aware Strategies",
        f"- **Likely distribution character:** {', '.join(t.distribution_character) or 'see fund docs'}",
        f"- **Tax efficiency:** {t.tax_efficiency}",
        f"- **Account framing:** {t.account_fit}",
    ]
    for c in t.caveats:
        lines.append(f"- ⚠ {c}")

    lines += [
        "",
        "### 5. Notion Knowledge Layer",
        "Would you like me to save this report to your Notion workspace?",
        "(If Notion is not connected, a local structured copy is stored under `data/notion/`.)",
        "",
        f"**Takeaway:** {report.takeaway}",
        "",
        f"_{disclaimer.strip()}_",
        "",
        "---",
        "Analyze another ticker (e.g. `JEPI`, `QYLD`, `SPY`) or reply **save to Notion**.",
    ]
    return "\n".join(lines)

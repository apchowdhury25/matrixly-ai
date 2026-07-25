"""Free Yahoo Finance public endpoints (no API key)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ..models import MarketSnapshot


class YahooFinanceClient:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = cfg.get("data") or {}
        self.timeout = float(data.get("timeout_sec") or 20)
        self.ua = data.get("user_agent") or "MatrixlyETFAnalyzer/1.0"
        self.quote_url = data.get("yahoo_quote_url") or (
            "https://query1.finance.yahoo.com/v7/finance/quote"
        )
        self.chart_url = data.get("yahoo_chart_url") or (
            "https://query1.finance.yahoo.com/v8/finance/chart"
        )
        self.summary_url = data.get("yahoo_summary_url") or (
            "https://query2.finance.yahoo.com/v10/finance/quoteSummary"
        )
        self.samples = Path(cfg["paths"]["samples"])

    def fetch(self, ticker: str) -> MarketSnapshot:
        t = (ticker or "QQQI").strip().upper()
        notes: list[str] = []
        quality = "live"
        quote: dict[str, Any] = {}
        summary: dict[str, Any] = {}
        chart_meta: dict[str, Any] = {}

        try:
            quote = self._quote(t)
        except Exception as e:
            notes.append(f"Quote endpoint issue: {e}")
            quality = "partial"

        try:
            summary = self._summary(t)
        except Exception as e:
            notes.append(f"Fundamentals endpoint issue: {e}")
            quality = "partial" if quote else "partial"

        try:
            chart_meta = self._chart_meta(t)
        except Exception as e:
            notes.append(f"Chart endpoint issue: {e}")

        if not quote and not summary and not chart_meta:
            return self._fallback(t, notes + ["All live endpoints failed or blocked."])

        # merge fields
        price = _f(quote.get("regularMarketPrice") or chart_meta.get("regularMarketPrice"))
        prev = _f(quote.get("regularMarketPreviousClose") or chart_meta.get("previousClose"))
        change = _f(quote.get("regularMarketChange"))
        change_pct = _f(quote.get("regularMarketChangePercent"))
        if change is None and price is not None and prev is not None:
            change = price - prev
        if change_pct is None and change is not None and prev:
            change_pct = (change / prev) * 100.0

        # summary modules
        summary_profile = (summary.get("summaryProfile") or {}) if summary else {}
        summary_detail = (summary.get("summaryDetail") or {}) if summary else {}
        default_key = (summary.get("defaultKeyStatistics") or {}) if summary else {}
        price_mod = (summary.get("price") or {}) if summary else {}
        fund_profile = (summary.get("fundProfile") or {}) if summary else {}
        top_holdings = (summary.get("topHoldings") or {}) if summary else {}

        expense = _f(
            _unwrap(default_key.get("annualReportExpenseRatio"))
            or _unwrap(fund_profile.get("feesExpensesInvestment", {}).get("annualReportExpenseRatio") if isinstance(fund_profile.get("feesExpensesInvestment"), dict) else None)
            or quote.get("annualReportExpenseRatio")
        )
        # sometimes expense is already ratio like 0.0068
        nav = _f(
            quote.get("navPrice")
            or _unwrap(default_key.get("navPrice"))
            or _unwrap(summary_detail.get("navPrice"))
            or price_mod.get("navPrice")
        )
        yield_ttm = _f(
            quote.get("trailingAnnualDividendYield")
            or _unwrap(summary_detail.get("trailingAnnualDividendYield"))
            or _unwrap(summary_detail.get("yield"))
            or quote.get("yield")
        )
        div_rate = _f(
            quote.get("trailingAnnualDividendRate")
            or _unwrap(summary_detail.get("trailingAnnualDividendRate"))
            or quote.get("dividendRate")
        )
        div_yield = _f(
            quote.get("dividendYield")
            or _unwrap(summary_detail.get("dividendYield"))
        )
        total_assets = _f(
            quote.get("totalAssets")
            or _unwrap(default_key.get("totalAssets"))
            or _unwrap(top_holdings.get("totalAssets") if isinstance(top_holdings, dict) else None)
        )
        market_cap = _f(quote.get("marketCap") or price_mod.get("marketCap"))
        name = str(
            quote.get("longName")
            or quote.get("shortName")
            or price_mod.get("longName")
            or price_mod.get("shortName")
            or t
        )
        category = str(
            summary_profile.get("category")
            or fund_profile.get("categoryName")
            or quote.get("quoteType")
            or ""
        )

        if price is None:
            quality = "partial"
            notes.append("Price missing — some fields incomplete.")

        # Yahoo free data is often delayed for some users
        if quote.get("marketState") in {"POST", "PRE", "CLOSED"}:
            notes.append("Market session not open — last trade/price may be delayed.")

        return MarketSnapshot(
            ticker=t,
            name=name,
            currency=str(quote.get("currency") or price_mod.get("currency") or "USD"),
            price=price,
            change=change,
            change_pct=change_pct,
            volume=_f(quote.get("regularMarketVolume") or chart_meta.get("regularMarketVolume")),
            fifty_two_week_low=_f(
                quote.get("fiftyTwoWeekLow") or _unwrap(summary_detail.get("fiftyTwoWeekLow"))
            ),
            fifty_two_week_high=_f(
                quote.get("fiftyTwoWeekHigh") or _unwrap(summary_detail.get("fiftyTwoWeekHigh"))
            ),
            market_cap=market_cap,
            total_assets=total_assets,
            expense_ratio=expense,
            nav=nav,
            yield_ttm=yield_ttm,
            dividend_rate=div_rate,
            dividend_yield=div_yield,
            trailing_annual_dividend_rate=div_rate,
            category=category,
            data_quality=quality,
            notes=notes,
            source="yahoo",
            raw={"quote_keys": list(quote.keys())[:40], "summary_modules": list(summary.keys())},
        )

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.ua,
            "Accept": "application/json",
        }

    def _quote(self, ticker: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout, headers=self._headers(), follow_redirects=True) as client:
            r = client.get(self.quote_url, params={"symbols": ticker})
            r.raise_for_status()
            data = r.json()
        results = ((data.get("quoteResponse") or {}).get("result")) or []
        if not results:
            # try chart-only path
            return {}
        return results[0] or {}

    def _summary(self, ticker: str) -> dict[str, Any]:
        modules = ",".join(
            [
                "summaryDetail",
                "defaultKeyStatistics",
                "price",
                "summaryProfile",
                "fundProfile",
                "topHoldings",
            ]
        )
        with httpx.Client(timeout=self.timeout, headers=self._headers(), follow_redirects=True) as client:
            r = client.get(
                f"{self.summary_url}/{ticker}",
                params={"modules": modules},
            )
            if r.status_code >= 400:
                return {}
            data = r.json()
        result = ((data.get("quoteSummary") or {}).get("result")) or []
        if not result:
            return {}
        return result[0] or {}

    def _chart_meta(self, ticker: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout, headers=self._headers(), follow_redirects=True) as client:
            r = client.get(
                f"{self.chart_url}/{ticker}",
                params={"range": "5d", "interval": "1d"},
            )
            if r.status_code >= 400:
                return {}
            data = r.json()
        result = ((data.get("chart") or {}).get("result")) or []
        if not result:
            return {}
        return result[0].get("meta") or {}

    def _fallback(self, ticker: str, notes: list[str]) -> MarketSnapshot:
        path = self.samples / "qqqi_fallback.json"
        if ticker == "QQQI" and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data["notes"] = list(data.get("notes") or []) + notes
            data["data_quality"] = "fallback_sample"
            return MarketSnapshot(**{k: v for k, v in data.items() if k in MarketSnapshot.model_fields})
        return MarketSnapshot(
            ticker=ticker,
            name=ticker,
            data_quality="fallback_sample",
            notes=notes
            + [
                "Live data unavailable from free endpoints.",
                "Try again later or verify the ticker symbol.",
            ],
            source="fallback",
        )


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _unwrap(v: Any) -> Any:
    if isinstance(v, dict) and "raw" in v:
        return v.get("raw")
    return v

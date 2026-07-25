"""ETF Portfolio Analyzer orchestrator."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .agents.analyze import build_report
from .integrations.notion_export import NotionExporter
from .integrations.yahoo import YahooFinanceClient
from .llm import cost_usd, grok_available
from .models import AnalysisReport, ChatResponse, new_id, today_str
from .services.audit import AuditLog
from .services.store import ReportStore
from .services.usage import UsageMeter


class ETFAnalyzer:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        data = Path(cfg["paths"]["data"])
        self.yahoo = YahooFinanceClient(cfg)
        self.store = ReportStore(data)
        self.audit = AuditLog(data)
        self.usage = UsageMeter(data, cfg)
        self.notion = NotionExporter(data, cfg)
        self.default = (cfg.get("etf") or {}).get("default_ticker") or "QQQI"
        self.default_name = (cfg.get("etf") or {}).get("default_name") or "NEOS Nasdaq-100 High Income ETF"

    def analyze(self, ticker: str = "", *, save_to_notion: bool = False) -> AnalysisReport:
        t = (ticker or "").strip().upper()
        is_default = not t
        if not t:
            t = self.default.upper()

        self.audit.write("analyze_start", ticker=t, default=is_default)
        snap = self.yahoo.fetch(t)
        report, tin, tout = build_report(snap, self.cfg, is_default=is_default)
        report.usage_tokens_in = tin
        report.usage_tokens_out = tout
        report.estimated_cost_usd = round(cost_usd(self.cfg, tin, tout), 6)

        if save_to_notion:
            result = self.notion.save(report)
            if result.get("page_id"):
                report.notion_page_id = result.get("page_id")
                report.notion_url = result.get("url")
            self.audit.write("notion_save", report_id=report.id, result=result)
            note = result.get("note") or result.get("url") or result.get("path") or result.get("local_path")
            if note:
                report.markdown += f"\n\n**Notion:** {note}\n"

        self.store.save(report)
        self.usage.record("analyze", tin, tout, report_id=report.id)
        self.audit.write(
            "analyze_complete",
            report_id=report.id,
            ticker=t,
            quality=snap.data_quality,
        )
        return report

    def chat(self, message: str, session_id: str = "", save_to_notion: bool = False) -> ChatResponse:
        sid = session_id or new_id("ses_")
        sess = self.store.get_session(sid) or {"id": sid, "history": []}
        text = (message or "").strip()

        # detect save intent
        want_save = save_to_notion or bool(
            re.search(r"\b(save|notion|store|export)\b", text, re.I)
        )
        ticker = _extract_ticker(text)
        last_ticker = (sess.get("last_ticker") or "").upper()

        if want_save and not ticker:
            # save last report
            last_id = sess.get("last_report_id")
            if last_id:
                report = self.store.get(last_id)
                if report:
                    result = self.notion.save(report)
                    if result.get("page_id"):
                        report.notion_page_id = result.get("page_id")
                        report.notion_url = result.get("url")
                        self.store.save(report)
                    reply = (
                        f"**ETF Portfolio Analyzer • {report.ticker} • {today_str()}**\n\n"
                        f"Saved analysis for **{report.ticker}**.\n"
                        f"- Backend: {result.get('backend')}\n"
                        f"- Detail: {result.get('url') or result.get('path') or result.get('note')}\n\n"
                        "Analyze another ticker or ask for a fresh default **QQQI** report."
                    )
                    self.usage.record("notion_save", report_id=report.id)
                    self.store.save_session(sid, {**sess, "history": (sess.get("history") or [])[-20:]})
                    return ChatResponse(session_id=sid, reply=reply, report=report)
            reply = (
                f"**ETF Portfolio Analyzer • — • {today_str()}**\n\n"
                "No prior analysis in this session to save. "
                "I'll run the default **QQQI** sample first."
            )
            report = self.analyze("", save_to_notion=True)
            sess["last_ticker"] = report.ticker
            sess["last_report_id"] = report.id
            self.store.save_session(sid, sess)
            return ChatResponse(
                session_id=sid,
                reply=self._opening(report) if not text else report.markdown,
                report=report,
            )

        # first message / empty → default QQQI
        if not text or text.lower() in {"hi", "hello", "start", "help"}:
            report = self.analyze("")
            sess["last_ticker"] = report.ticker
            sess["last_report_id"] = report.id
            self.store.save_session(sid, sess)
            return ChatResponse(session_id=sid, reply=self._opening(report), report=report)

        if not ticker and last_ticker and re.search(r"\b(again|refresh|update|rerun)\b", text, re.I):
            ticker = last_ticker

        if not ticker:
            # free text without ticker → default + note
            report = self.analyze("")
            sess["last_ticker"] = report.ticker
            sess["last_report_id"] = report.id
            self.store.save_session(sid, sess)
            reply = (
                "No ticker detected — defaulting to **QQQI**.\n\n" + report.markdown
            )
            return ChatResponse(session_id=sid, reply=reply, report=report)

        report = self.analyze(ticker, save_to_notion=want_save)
        sess["last_ticker"] = report.ticker
        sess["last_report_id"] = report.id
        self.store.save_session(sid, sess)
        return ChatResponse(session_id=sid, reply=report.markdown, report=report)

    def _opening(self, report: AnalysisReport) -> str:
        return (
            "ETF Portfolio Analyzer ready.\n"
            f"Defaulting to **{report.ticker}** "
            f"({self.default_name if report.ticker == self.default.upper() else report.snapshot.name}) "
            "as the sample.\n\n"
            "Here's the live analysis…\n\n"
            + report.markdown
        )

    def status(self) -> dict[str, Any]:
        reports = self.store.list(limit=200)
        return {
            "service": "etf-analyzer",
            "version": "1.0.0",
            "default_ticker": self.default,
            "reports": len(reports),
            "notion_enabled": self.notion.enabled,
            "grok": grok_available(self.cfg),
            "usage": self.usage.summary(),
        }


def _extract_ticker(text: str) -> str:
    if not text:
        return ""
    # $QQQI or plain tickers
    m = re.search(r"\$([A-Za-z]{1,5})\b", text)
    if m:
        return m.group(1).upper()
    # "analyze SPY" / "ticker: JEPI"
    m = re.search(
        r"\b(?:analyze|ticker|etf|for|on)\s+([A-Za-z]{1,5})\b",
        text,
        re.I,
    )
    if m:
        cand = m.group(1).upper()
        if cand not in {"SAVE", "NOTION", "THIS", "THAT", "HELP", "PLEASE", "WITH", "FROM"}:
            return cand
    # bare ticker-only message
    m = re.fullmatch(r"\s*([A-Za-z]{1,5})\s*", text)
    if m:
        return m.group(1).upper()
    return ""

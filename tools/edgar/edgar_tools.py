"""MCP tools for SEC EDGAR financial data and ratio analysis."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Annotated, Any, Dict, List

from edgar import Company

from claude_agent_sdk import tool

from tools.edgar.fetcher import EdgarFetcher
from tools.edgar.utils import EdgarUtils

logger = logging.getLogger(__name__)

_fetcher = EdgarFetcher()


# ------------------------------------------------------------------ #
# Shared helpers                                                       #
# ------------------------------------------------------------------ #

def _load_company(ticker: str):
    company = Company(ticker)
    if getattr(company, "not_found", False):
        raise ValueError(f"Company not found: {ticker}")
    return company


# ------------------------------------------------------------------ #
# Tools                                                                #
# ------------------------------------------------------------------ #

@tool(
    "analyze_income_statement",
    "Comprehensive income statement analysis using SEC EDGAR XBRL data. "
    "Provides 5 years of annual and 4 quarters of quarterly income statements, "
    "YoY/QoQ growth trends, revenue segment breakdown, margin analysis, "
    "CAGR calculations, and strategic profitability insights. "
    "Handles stock splits for correct EPS/per-share metrics.",
    {
        "ticker":           Annotated[str,  "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"],
        "num_years":        Annotated[int,  "Number of annual periods to analyze (default 5)"],
        "num_quarters":     Annotated[int,  "Number of quarterly periods to analyze (default 4)"],
        "include_segments": Annotated[bool, "Whether to include revenue segment breakdown (default true)"],
    },
)
async def analyze_income_statement(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker       = str(args["ticker"]).upper().strip()
    num_years    = int(args.get("num_years", 5))
    num_quarters = int(args.get("num_quarters", 4))
    include_segs = bool(args.get("include_segments", True))

    try:
        company = _load_company(ticker)
    except Exception as e:
        return EdgarUtils.err_response(str(e), ticker=ticker)

    try:
        report = _fetcher.fetch_income_data(company, num_years, num_quarters, include_segs)
    except Exception as e:
        logger.exception("fetch_income_data failed for %s", ticker)
        return EdgarUtils.err_response(str(e), ticker=ticker)

    path = EdgarUtils.asset_path(ticker, "income_statement")
    EdgarUtils.save_asset(path, {"success": True, "ticker": ticker, "company_name": company.name, "report": report})

    return EdgarUtils.ok_response(ticker, "income_statement", path, {
        "company_name":   company.name,
        "periods_covered": len(report.get("annual_statements", [])),
        **report.get("summary", {}),
    })


@tool(
    "analyze_balance_sheet",
    "Comprehensive balance sheet analysis using SEC EDGAR XBRL data. "
    "Provides multi-year annual balance sheets with assets, liabilities, equity breakdown, "
    "working capital, debt structure, and key ratios (current ratio, debt/equity, debt/assets).",
    {
        "ticker":    Annotated[str, "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"],
        "num_years": Annotated[int, "Number of annual periods to analyze (default 5)"],
    },
)
async def analyze_balance_sheet(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker    = str(args["ticker"]).upper().strip()
    num_years = int(args.get("num_years", 5))

    try:
        company = _load_company(ticker)
    except Exception as e:
        return EdgarUtils.err_response(str(e), ticker=ticker)

    try:
        statements = _fetcher.fetch_balance_sheet_data(company, num_years)
    except Exception as e:
        logger.exception("fetch_balance_sheet_data failed for %s", ticker)
        return EdgarUtils.err_response(str(e), ticker=ticker)

    if not statements:
        return EdgarUtils.err_response("No balance sheet data found", ticker=ticker)

    path = EdgarUtils.asset_path(ticker, "balance_sheet")
    EdgarUtils.save_asset(path, {"success": True, "ticker": ticker, "company_name": company.name, "balance_sheets": [asdict(s) for s in statements]})

    la = statements[0]
    return EdgarUtils.ok_response(ticker, "balance_sheet", path, {
        "company_name":           company.name,
        "periods_covered":        len(statements),
        "latest_period":          la.period,
        "latest_total_assets":    la.total_assets,
        "latest_total_liabilities": la.total_liabilities,
        "latest_equity":          la.total_stockholders_equity,
        "latest_total_debt":      la.total_debt,
        "latest_net_cash":        la.net_cash,
        "latest_current_ratio":   la.current_ratio,
        "latest_debt_to_equity":  la.debt_to_equity,
        "latest_book_value_per_share": la.book_value_per_share,
    })


@tool(
    "analyze_cash_flow",
    "Comprehensive cash flow statement analysis using SEC EDGAR XBRL data. "
    "Provides multi-year operating, investing, and financing cash flows, "
    "free cash flow, FCF margin, CapEx intensity, shareholder returns (dividends + buybacks), "
    "and debt activity.",
    {
        "ticker":    Annotated[str, "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"],
        "num_years": Annotated[int, "Number of annual periods to analyze (default 5)"],
    },
)
async def analyze_cash_flow(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker    = str(args["ticker"]).upper().strip()
    num_years = int(args.get("num_years", 5))

    try:
        company = _load_company(ticker)
    except Exception as e:
        return EdgarUtils.err_response(str(e), ticker=ticker)

    try:
        statements = _fetcher.fetch_cash_flow_data(company, num_years)
    except Exception as e:
        logger.exception("fetch_cash_flow_data failed for %s", ticker)
        return EdgarUtils.err_response(str(e), ticker=ticker)

    if not statements:
        return EdgarUtils.err_response("No cash flow data found", ticker=ticker)

    path = EdgarUtils.asset_path(ticker, "cash_flow")
    EdgarUtils.save_asset(path, {"success": True, "ticker": ticker, "company_name": company.name, "cash_flows": [asdict(s) for s in statements]})

    la = statements[0]
    return EdgarUtils.ok_response(ticker, "cash_flow", path, {
        "company_name":             company.name,
        "periods_covered":          len(statements),
        "latest_period":            la.period,
        "latest_operating_cf":      la.operating_cash_flow,
        "latest_free_cash_flow":    la.free_cash_flow,
        "latest_fcf_margin_pct":    la.fcf_margin_pct,
        "latest_capex":             la.capital_expenditures,
        "latest_shareholder_return":la.shareholder_return,
        "latest_dividends":         la.dividends_paid,
        "latest_buybacks":          la.share_buybacks,
    })


@tool(
    "analyze_company_profile",
    "Fetch comprehensive company profile from SEC EDGAR. "
    "Returns company identity (CIK, SIC, industry, exchange), "
    "shares outstanding, public float, business overview from 10-K, "
    "and risk factors.",
    {
        "ticker": Annotated[str, "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"],
    },
)
async def analyze_company_profile(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = str(args["ticker"]).upper().strip()

    try:
        company = _load_company(ticker)
    except Exception as e:
        return EdgarUtils.err_response(str(e), ticker=ticker)

    try:
        profile = _fetcher.fetch_company_profile_data(company)
    except Exception as e:
        logger.exception("fetch_company_profile_data failed for %s", ticker)
        return EdgarUtils.err_response(str(e), ticker=ticker)

    path = EdgarUtils.asset_path(ticker, "company_profile")
    EdgarUtils.save_asset(path, {"success": True, "ticker": ticker, "profile": profile})

    return EdgarUtils.ok_response(ticker, "company_profile", path, {
        "company_name":           profile.get("company_name"),
        "cik":                    profile.get("cik"),
        "industry":               profile.get("industry"),
        "exchanges":              profile.get("exchanges"),
        "latest_10k_filing_date": profile.get("latest_10k_filing_date"),
        "shares":                 profile.get("shares"),
    })


@tool(
    "analyze_financial_ratios",
    "Pure computation tool — does NOT fetch data. Takes pre-fetched income statement, "
    "balance sheet, and cash flow data (JSON from the other tools) and computes "
    "profitability ratios (ROE, ROA, ROIC, margins), leverage ratios (D/E, interest "
    "coverage, net debt/EBITDA), valuation metrics (BV/share, EPS, FCF/share), and "
    "operating efficiency ratios (asset turnover, DSO, DIO, DPO, cash conversion cycle). "
    "Call analyze_income_statement, analyze_balance_sheet, and analyze_cash_flow FIRST, "
    "then pass their JSON outputs here.",
    {
        "income_data":       Annotated[str, "JSON string from analyze_income_statement tool output"],
        "balance_sheet_data":Annotated[str, "JSON string from analyze_balance_sheet tool output"],
        "cash_flow_data":    Annotated[str, "JSON string from analyze_cash_flow tool output"],
    },
)
async def analyze_financial_ratios(args: Dict[str, Any]) -> Dict[str, Any]:
    def parse(v):
        return json.loads(v) if isinstance(v, str) else v

    try:
        income_raw   = parse(args["income_data"])
        balance_raw  = parse(args["balance_sheet_data"])
        cashflow_raw = parse(args["cash_flow_data"])
    except (json.JSONDecodeError, KeyError) as e:
        return EdgarUtils.err_response(f"Invalid input data: {e}")

    income_statements = income_raw.get("report", {}).get("annual_statements", [])
    balance_sheets    = balance_raw.get("balance_sheets", [])
    cash_flows        = cashflow_raw.get("cash_flows", [])

    if not income_statements:
        return EdgarUtils.err_response("No income statement data provided")

    ticker       = income_raw.get("ticker", "")
    company_name = income_raw.get("company_name", "")

    ratios: List[Dict[str, Any]] = []
    for inc in income_statements:
        fy = inc.get("fiscal_year")
        bs = next((b for b in balance_sheets if b.get("fiscal_year") == fy), {})
        cf = next((c for c in cash_flows    if c.get("fiscal_year") == fy), {})
        ratios.append(EdgarUtils.compute_ratios(inc, bs, cf))

    if not ratios:
        return EdgarUtils.err_response("Could not compute ratios — no matching periods")

    path = EdgarUtils.asset_path(ticker, "financial_ratios") if ticker else None
    if path:
        EdgarUtils.save_asset(path, {
            "success": True, "ticker": ticker, "company_name": company_name,
            "periods_analyzed": len(ratios), "ratios": ratios,
        })

    latest      = ratios[0]
    latest_prof = latest.get("profitability", {})
    latest_lev  = latest.get("leverage", {})
    latest_op   = latest.get("operating", {})

    return EdgarUtils.ok_response(ticker, "financial_ratios", path, {
        "company_name":                company_name,
        "periods_analyzed":            len(ratios),
        "latest_roe_pct":              latest_prof.get("return_on_equity_pct"),
        "latest_roa_pct":              latest_prof.get("return_on_assets_pct"),
        "latest_roic_pct":             latest_prof.get("return_on_invested_capital_pct"),
        "latest_fcf_margin_pct":       latest_prof.get("free_cash_flow_margin_pct"),
        "latest_debt_to_equity":       latest_lev.get("debt_to_equity"),
        "latest_interest_coverage":    latest_lev.get("interest_coverage"),
        "latest_net_debt_to_ebitda":   latest_lev.get("net_debt_to_ebitda"),
        "latest_current_ratio":        latest_lev.get("current_ratio"),
        "latest_quick_ratio":          latest_lev.get("quick_ratio"),
        "latest_asset_turnover":       latest_op.get("asset_turnover"),
        "latest_cash_conversion_cycle":latest_op.get("cash_conversion_cycle"),
    }) if path else EdgarUtils.ok_response("", "financial_ratios", Path("."), {
        "company_name": company_name, "periods_analyzed": len(ratios),
        "latest_roe_pct": latest_prof.get("return_on_equity_pct"),
    })

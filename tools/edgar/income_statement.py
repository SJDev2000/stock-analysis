import json
import re
from dataclasses import asdict
from typing import Annotated, Any, Dict, List, Optional

import pandas as pd
from edgar import Company, set_identity

from claude_agent_sdk import tool

from tools.edgar.models import (
    CoreIncomeMetrics,
    GrowthMetrics,
    GrowthMomentum,
    IncomeMetrics,
    IncomeStatementReport,
    SegmentRevenue,
)
from tools.edgar.xbrl import (
    COGS_CONCEPTS,
    REVENUE_CONCEPTS,
    detect_fiscal_period,
    detect_split_ratio,
    get_all_periods_in_filing,
    get_current_period_value,
    get_period_value,
    round_val,
    safe_pct,
)

set_identity("Stock Analysis Tool contact@example.com")

PER_SHARE_FIELDS = ["eps_basic", "eps_diluted"]
SHARE_COUNT_FIELDS = ["shares_outstanding_basic", "shares_outstanding_diluted"]


def _apply_split_adjustment(metrics: IncomeMetrics, split_ratio: float):
    if metrics.eps_basic is not None:
        metrics.eps_basic = round_val(metrics.eps_basic / split_ratio, 4)
    if metrics.eps_diluted is not None:
        metrics.eps_diluted = round_val(metrics.eps_diluted / split_ratio, 4)
    if metrics.shares_outstanding_basic is not None:
        metrics.shares_outstanding_basic = metrics.shares_outstanding_basic * split_ratio
    if metrics.shares_outstanding_diluted is not None:
        metrics.shares_outstanding_diluted = metrics.shares_outstanding_diluted * split_ratio


def _extract_metrics_for_period(
    facts_view, period_end: str, fiscal_period: str,
    period_type: str, filing_date: str, fiscal_year: Optional[int] = None
) -> Optional[IncomeMetrics]:
    display_year = int(period_end[:4]) if period_end else fiscal_year
    period_label = f"FY{display_year}" if fiscal_period == "FY" else f"{display_year}-{fiscal_period}"

    def get_val(concepts):
        return get_period_value(
            facts_view, concepts if isinstance(concepts, list) else [concepts],
            fiscal_period, period_end
        )

    revenue = get_val(REVENUE_CONCEPTS)
    cost_of_revenue = get_val(COGS_CONCEPTS)
    gross_profit = get_val(["GrossProfit"])
    operating_income = get_val(["OperatingIncomeLoss"])
    net_income = get_val(["NetIncomeLoss"])
    rd_expense = get_val(["ResearchAndDevelopmentExpense"])
    sga_expense = get_val(["SellingGeneralAndAdministrativeExpense"])
    interest_expense = get_val(["InterestExpense"])
    other_income = get_val(["NonoperatingIncomeExpense"])
    income_before_tax = get_val(["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"])
    income_tax = get_val(["IncomeTaxExpenseBenefit"])
    eps_basic = get_val(["EarningsPerShareBasic"])
    eps_diluted = get_val(["EarningsPerShareDiluted"])
    shares_basic = get_val(["WeightedAverageNumberOfSharesOutstandingBasic"])
    shares_diluted = get_val(["WeightedAverageNumberOfDilutedSharesOutstanding"])
    depreciation = get_val([
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
    ])

    if revenue is None and net_income is None:
        return None

    if gross_profit is None and revenue is not None and cost_of_revenue is not None:
        gross_profit = revenue - cost_of_revenue

    operating_expenses = None
    if gross_profit is not None and operating_income is not None:
        operating_expenses = gross_profit - operating_income

    ebitda = None
    if operating_income is not None:
        ebitda = operating_income + (depreciation if depreciation else 0)

    return IncomeMetrics(
        period=period_label,
        period_type=period_type,
        fiscal_year=display_year,
        fiscal_period=fiscal_period,
        filing_date=filing_date,
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
        gross_profit=gross_profit,
        gross_margin_pct=round_val(safe_pct(gross_profit, revenue)),
        operating_expenses=operating_expenses,
        research_and_development=rd_expense,
        selling_general_admin=sga_expense,
        operating_income=operating_income,
        operating_margin_pct=round_val(safe_pct(operating_income, revenue)),
        interest_expense=interest_expense,
        other_income_expense=other_income,
        income_before_tax=income_before_tax,
        income_tax_expense=income_tax,
        net_income=net_income,
        net_margin_pct=round_val(safe_pct(net_income, revenue)),
        ebitda=ebitda,
        ebitda_margin_pct=round_val(safe_pct(ebitda, revenue)),
        eps_basic=eps_basic,
        eps_diluted=eps_diluted,
        shares_outstanding_basic=shares_basic,
        shares_outstanding_diluted=shares_diluted,
    )


def _fetch_annual_income_statements(company: Company, num_years: int = 5) -> List[IncomeMetrics]:
    num_filings_needed = max(num_years, (num_years // 2) + 1)
    filings = company.get_filings(form="10-K").head(num_filings_needed)
    if not filings or len(filings) == 0:
        return []

    latest_xbrl = None
    split_ratio = None
    for filing in filings:
        xbrl = filing.xbrl()
        if xbrl:
            latest_xbrl = xbrl
            split_ratio = detect_split_ratio(xbrl)
            break

    collected_periods: Dict[str, IncomeMetrics] = {}
    periods_in_latest: set = set()

    for idx, filing in enumerate(filings):
        xbrl = filing.xbrl()
        if not xbrl:
            continue

        facts = xbrl.facts
        available_periods = get_all_periods_in_filing(facts, "FY")

        if idx == 0:
            periods_in_latest = {p["period_end"] for p in available_periods}

        for period_info in available_periods:
            pe = period_info["period_end"]
            if pe in collected_periods:
                continue

            metrics = _extract_metrics_for_period(
                facts, pe, "FY", "annual", str(filing.filing_date), period_info["fiscal_year"]
            )
            if metrics:
                collected_periods[pe] = metrics

        if len(collected_periods) >= num_years:
            break

    if split_ratio and latest_xbrl:
        for pe, metrics in collected_periods.items():
            if pe not in periods_in_latest:
                _apply_split_adjustment(metrics, split_ratio)

    statements = sorted(collected_periods.values(), key=lambda m: m.period, reverse=True)
    return statements[:num_years]


def _fetch_quarterly_income_statements(company: Company, num_quarters: int = 4) -> List[IncomeMetrics]:
    filings = company.get_filings(form="10-Q").head(num_quarters + 2)
    if not filings or len(filings) == 0:
        return []

    tenk_filings = company.get_filings(form="10-K").head(1)
    split_ratio = None
    reference_shares = None
    if tenk_filings and len(tenk_filings) > 0:
        xbrl_10k = tenk_filings[0].xbrl()
        if xbrl_10k:
            split_ratio = detect_split_ratio(xbrl_10k)
            if split_ratio:
                reference_shares = get_current_period_value(
                    xbrl_10k.facts,
                    ["WeightedAverageNumberOfDilutedSharesOutstanding",
                     "WeightedAverageNumberOfSharesOutstandingBasic"],
                    "FY"
                )

    collected: List[IncomeMetrics] = []
    seen_period_ends: set = set()

    for filing in filings:
        xbrl = filing.xbrl()
        if not xbrl:
            continue

        fp = detect_fiscal_period(xbrl)
        facts = xbrl.facts
        quarterly_periods = get_all_periods_in_filing(facts, fp)
        if not quarterly_periods:
            continue

        period_info = quarterly_periods[0]
        pe = period_info["period_end"]
        if pe in seen_period_ends:
            continue
        seen_period_ends.add(pe)

        metrics = _extract_metrics_for_period(
            facts, pe, fp, "quarterly", str(filing.filing_date), period_info["fiscal_year"]
        )
        if metrics:
            if split_ratio and reference_shares and metrics.shares_outstanding_diluted:
                shares_ratio = reference_shares / metrics.shares_outstanding_diluted
                if shares_ratio > (split_ratio * 0.8):
                    _apply_split_adjustment(metrics, split_ratio)
            collected.append(metrics)

        if len(collected) >= num_quarters:
            break

    return collected[:num_quarters]


def _abs_change(current: Optional[float], prior: Optional[float]) -> Optional[float]:
    if current is not None and prior is not None:
        return round(current - prior, 2)
    return None


def _pct_change(current: Optional[float], prior: Optional[float]) -> Optional[float]:
    if current is not None and prior is not None and prior != 0:
        return round((current - prior) / abs(prior) * 100, 2)
    return None


def _margin_expansion_bps(current_margin: Optional[float], prior_margin: Optional[float]) -> Optional[float]:
    if current_margin is not None and prior_margin is not None:
        return round((current_margin - prior_margin) * 100, 1)
    return None


def _compute_growth(current: IncomeMetrics, prior: IncomeMetrics, growth_type: str) -> GrowthMetrics:
    return GrowthMetrics(
        period=current.period,
        comparison_period=prior.period,
        growth_type=growth_type,
        revenue_growth_abs=_abs_change(current.revenue, prior.revenue),
        revenue_growth_pct=_pct_change(current.revenue, prior.revenue),
        gross_profit_growth_abs=_abs_change(current.gross_profit, prior.gross_profit),
        gross_profit_growth_pct=_pct_change(current.gross_profit, prior.gross_profit),
        operating_income_growth_abs=_abs_change(current.operating_income, prior.operating_income),
        operating_income_growth_pct=_pct_change(current.operating_income, prior.operating_income),
        net_income_growth_abs=_abs_change(current.net_income, prior.net_income),
        net_income_growth_pct=_pct_change(current.net_income, prior.net_income),
        ebitda_growth_abs=_abs_change(current.ebitda, prior.ebitda),
        ebitda_growth_pct=_pct_change(current.ebitda, prior.ebitda),
        eps_diluted_growth_abs=_abs_change(current.eps_diluted, prior.eps_diluted),
        eps_diluted_growth_pct=_pct_change(current.eps_diluted, prior.eps_diluted),
        margin_expansion_gross_bps=_margin_expansion_bps(current.gross_margin_pct, prior.gross_margin_pct),
        margin_expansion_operating_bps=_margin_expansion_bps(current.operating_margin_pct, prior.operating_margin_pct),
        margin_expansion_net_bps=_margin_expansion_bps(current.net_margin_pct, prior.net_margin_pct),
    )


def _compute_yoy_growth(annual_statements: List[IncomeMetrics]) -> List[GrowthMetrics]:
    return [
        _compute_growth(annual_statements[i], annual_statements[i + 1], "YoY")
        for i in range(len(annual_statements) - 1)
    ]


def _compute_qoq_growth(quarterly_statements: List[IncomeMetrics]) -> List[GrowthMetrics]:
    return [
        _compute_growth(quarterly_statements[i], quarterly_statements[i + 1], "QoQ")
        for i in range(len(quarterly_statements) - 1)
    ]


def _clean_segment_name(name: str) -> str:
    if ":" in name:
        name = name.split(":")[-1]
    name = name.replace("Member", "").replace("Segment", "")
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    result = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1 \2', result)
    result = re.sub(r'\s+', ' ', result).strip()
    result = result.replace(" And ", " & ").replace(" and ", " & ")
    return result if result else name


def _fetch_revenue_segments(company: Company) -> List[SegmentRevenue]:
    filings = company.get_filings(form="10-K").head(1)
    if not filings or len(filings) == 0:
        return []

    filing = filings[0]
    xbrl = filing.xbrl()
    if not xbrl:
        return []

    segments = []
    total_revenue = get_current_period_value(xbrl.facts, REVENUE_CONCEPTS, "FY")

    segment_axes = [
        "srt_ProductOrServiceAxis",
        "us-gaap_StatementBusinessSegmentsAxis",
    ]

    for axis in segment_axes:
        try:
            pivoted = xbrl.facts.pivot_by_dimension(axis)
            if pivoted is None or pivoted.empty:
                continue

            rev_mask = pd.Series([False] * len(pivoted), index=pivoted.index)
            for rc in REVENUE_CONCEPTS:
                rev_mask = rev_mask | pivoted["concept"].str.contains(rc, case=False, na=False)
            rev_data = pivoted[rev_mask]

            if rev_data.empty:
                continue

            member_cols = [c for c in rev_data.columns if c not in ("concept", "label")]

            for _, row in rev_data.iterrows():
                label = row.get("label", "")
                if label.lower() in ("products", "services", "product", "service"):
                    continue

                val = None
                for col in member_cols:
                    if pd.notna(row[col]):
                        val = float(row[col])
                        break

                if val is None or val <= 0:
                    continue

                seg_name = label if label else _clean_segment_name(member_cols[0])
                pct = (val / total_revenue * 100) if total_revenue and total_revenue > 0 else None

                segments.append(SegmentRevenue(
                    segment_name=seg_name,
                    revenue=val,
                    percentage_of_total=round_val(pct),
                    period=f"FY{xbrl.reporting_periods[0].get('fiscal_year', '')}",
                ))

            if segments:
                break
        except Exception:
            continue

    segments.sort(key=lambda s: s.revenue or 0, reverse=True)

    if segments and total_revenue and total_revenue > 0:
        total_pct = sum(s.percentage_of_total or 0 for s in segments)
        while total_pct > 110 and len(segments) > 1:
            removed = segments.pop(0)
            total_pct -= removed.percentage_of_total or 0
        remaining_total = sum(s.revenue or 0 for s in segments)
        if remaining_total > 0:
            for s in segments:
                if s.revenue:
                    s.percentage_of_total = round_val(s.revenue / total_revenue * 100)

    return segments


def _to_core_metrics(m: IncomeMetrics) -> CoreIncomeMetrics:
    return CoreIncomeMetrics(
        period=m.period,
        period_type=m.period_type,
        fiscal_year=m.fiscal_year,
        revenue=m.revenue,
        cost_of_revenue=m.cost_of_revenue,
        gross_income=m.gross_profit,
        gross_margin_pct=m.gross_margin_pct,
        operating_income=m.operating_income,
        operating_margin_pct=m.operating_margin_pct,
        net_income=m.net_income,
        net_profit_margin_pct=m.net_margin_pct,
        eps_diluted=m.eps_diluted,
    )


def _to_growth_momentum(current: IncomeMetrics, prior: IncomeMetrics, growth_type: str) -> GrowthMomentum:
    return GrowthMomentum(
        period=current.period,
        comparison_period=prior.period,
        growth_type=growth_type,
        revenue_growth_dollar=_abs_change(current.revenue, prior.revenue),
        revenue_growth_pct=_pct_change(current.revenue, prior.revenue),
        net_income_growth_dollar=_abs_change(current.net_income, prior.net_income),
        net_income_growth_pct=_pct_change(current.net_income, prior.net_income),
        eps_growth_dollar=_abs_change(current.eps_diluted, prior.eps_diluted),
        eps_growth_pct=_pct_change(current.eps_diluted, prior.eps_diluted),
    )


def _build_summary(
    annual: List[IncomeMetrics],
    quarterly: List[IncomeMetrics],
    yoy_growth: List[GrowthMetrics],
    qoq_growth: List[GrowthMetrics],
    segments: List[SegmentRevenue],
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    if annual:
        latest = annual[0]
        summary["latest_annual_period"] = latest.period
        summary["latest_annual_revenue"] = latest.revenue
        summary["latest_annual_net_income"] = latest.net_income
        summary["latest_gross_margin_pct"] = latest.gross_margin_pct
        summary["latest_operating_margin_pct"] = latest.operating_margin_pct
        summary["latest_net_margin_pct"] = latest.net_margin_pct
        summary["latest_ebitda"] = latest.ebitda

    if quarterly:
        latest_q = quarterly[0]
        summary["latest_quarter"] = latest_q.period
        summary["latest_quarter_revenue"] = latest_q.revenue
        summary["latest_quarter_net_income"] = latest_q.net_income

    if yoy_growth:
        latest_yoy = yoy_growth[0]
        summary["latest_yoy_revenue_growth_pct"] = latest_yoy.revenue_growth_pct
        summary["latest_yoy_net_income_growth_pct"] = latest_yoy.net_income_growth_pct
        summary["latest_yoy_eps_growth_pct"] = latest_yoy.eps_diluted_growth_pct

    if qoq_growth:
        summary["latest_qoq_revenue_growth_pct"] = qoq_growth[0].revenue_growth_pct

    if len(annual) >= 3:
        revenues = [s.revenue for s in annual if s.revenue and s.revenue > 0]
        if len(revenues) >= 3:
            cagr_years = len(revenues) - 1
            cagr = ((revenues[0] / revenues[-1]) ** (1 / cagr_years) - 1) * 100
            summary["revenue_cagr_pct"] = round_val(cagr)

        net_incomes = [s.net_income for s in annual if s.net_income and s.net_income > 0]
        if len(net_incomes) >= 3:
            ni_years = len(net_incomes) - 1
            ni_cagr = ((net_incomes[0] / net_incomes[-1]) ** (1 / ni_years) - 1) * 100
            summary["net_income_cagr_pct"] = round_val(ni_cagr)

    if len(annual) >= 2:
        first_margin = annual[0].gross_margin_pct
        last_margin = annual[-1].gross_margin_pct
        if first_margin is not None and last_margin is not None:
            if first_margin > last_margin + 0.5:
                summary["gross_margin_trend"] = "expanding"
            elif first_margin < last_margin - 0.5:
                summary["gross_margin_trend"] = "contracting"
            else:
                summary["gross_margin_trend"] = "stable"

    if annual:
        profitable_years = sum(1 for s in annual if s.net_income and s.net_income > 0)
        summary["profitable_years_out_of"] = f"{profitable_years}/{len(annual)}"

    if segments:
        summary["top_revenue_segment"] = segments[0].segment_name
        summary["top_segment_revenue"] = segments[0].revenue
        summary["top_segment_pct_of_total"] = segments[0].percentage_of_total
        summary["num_identified_segments"] = len(segments)
        if len(segments) >= 2:
            summary["revenue_concentration_top2_pct"] = round_val(
                (segments[0].percentage_of_total or 0) + (segments[1].percentage_of_total or 0)
            )

    return summary


# ---------------------------------------------------------------------------
# Tool (decorated for claude-agent-sdk MCP server)
# ---------------------------------------------------------------------------

@tool(
    "analyze_income_statement",
    "Comprehensive income statement analysis using SEC EDGAR XBRL data. "
    "Provides 5 years of annual and 4 quarters of quarterly income statements, "
    "YoY/QoQ growth trends, revenue segment breakdown, margin analysis, "
    "CAGR calculations, and strategic profitability insights. "
    "Handles stock splits for correct EPS/per-share metrics.",
    {
        "ticker": Annotated[str, "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"],
        "num_years": Annotated[int, "Number of annual periods to analyze (default 5)"],
        "num_quarters": Annotated[int, "Number of quarterly periods to analyze (default 4)"],
        "include_segments": Annotated[bool, "Whether to include revenue segment breakdown (default true)"],
    },
)
async def analyze_income_statement(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = args["ticker"]
    num_years = args.get("num_years", 5)
    num_quarters = args.get("num_quarters", 4)
    include_segments = args.get("include_segments", True)

    from tools.edgar._serialize import tool_error

    try:
        company = Company(ticker)
    except Exception as e:
        return tool_error(f"Company not found: {e}", ticker=ticker)

    annual = _fetch_annual_income_statements(company, num_years=num_years)
    quarterly = _fetch_quarterly_income_statements(company, num_quarters=num_quarters)

    yoy_growth = _compute_yoy_growth(annual)
    qoq_growth = _compute_qoq_growth(quarterly)

    annual_core = [_to_core_metrics(m) for m in annual]
    quarterly_core = [_to_core_metrics(m) for m in quarterly]
    yoy_momentum = [_to_growth_momentum(annual[i], annual[i + 1], "YoY") for i in range(len(annual) - 1)]
    qoq_momentum = [_to_growth_momentum(quarterly[i], quarterly[i + 1], "QoQ") for i in range(len(quarterly) - 1)]

    segments = []
    if include_segments:
        segments = _fetch_revenue_segments(company)

    summary = _build_summary(annual, quarterly, yoy_growth, qoq_growth, segments)

    from tools.edgar._serialize import tool_response

    result = {
        "success": True,
        "ticker": ticker.upper(),
        "company_name": company.name,
        "report": {
            "annual_statements": [asdict(s) for s in annual],
            "quarterly_statements": [asdict(s) for s in quarterly],
            "yoy_growth": [asdict(g) for g in yoy_momentum],
            "qoq_growth": [asdict(g) for g in qoq_momentum],
            "revenue_segments": [asdict(seg) for seg in segments],
            "summary": summary,
        },
    }
    return tool_response(result)

import json
from dataclasses import asdict, dataclass
from typing import Annotated, Any, Dict, List, Optional

from claude_agent_sdk import tool

from tools.edgar.xbrl import round_val, safe_pct


@dataclass
class ProfitabilityRatios:
    period: str
    fiscal_year: Optional[int] = None
    gross_margin_pct: Optional[float] = None
    operating_margin_pct: Optional[float] = None
    net_margin_pct: Optional[float] = None
    return_on_assets_pct: Optional[float] = None
    return_on_equity_pct: Optional[float] = None
    return_on_invested_capital_pct: Optional[float] = None
    free_cash_flow_margin_pct: Optional[float] = None


@dataclass
class LeverageRatios:
    period: str
    fiscal_year: Optional[int] = None
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    net_debt_to_ebitda: Optional[float] = None
    equity_multiplier: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None


@dataclass
class ValuationRatios:
    period: str
    fiscal_year: Optional[int] = None
    book_value_per_share: Optional[float] = None
    earnings_per_share: Optional[float] = None
    revenue_per_share: Optional[float] = None
    free_cash_flow_per_share: Optional[float] = None


@dataclass
class OperatingRatios:
    period: str
    fiscal_year: Optional[int] = None
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    receivables_turnover: Optional[float] = None
    payables_turnover: Optional[float] = None
    days_sales_outstanding: Optional[float] = None
    days_inventory_outstanding: Optional[float] = None
    days_payable_outstanding: Optional[float] = None
    cash_conversion_cycle: Optional[float] = None
    capex_to_revenue_pct: Optional[float] = None
    sbc_to_revenue_pct: Optional[float] = None


def _compute_period_ratios(
    income: Dict[str, Any],
    balance: Dict[str, Any],
    cashflow: Dict[str, Any],
) -> Dict[str, Any]:
    """Pure computation — no I/O. Takes a single period from each statement."""
    period = income.get("period") or balance.get("period") or "Unknown"
    fiscal_year = income.get("fiscal_year") or balance.get("fiscal_year")

    # Income statement
    revenue = income.get("revenue")
    cogs = income.get("cost_of_revenue")
    gross_profit = income.get("gross_profit")
    operating_income = income.get("operating_income")
    net_income = income.get("net_income")
    interest_expense = income.get("interest_expense")
    depreciation = income.get("ebitda", 0) - (operating_income or 0) if income.get("ebitda") and operating_income else None
    eps_diluted = income.get("eps_diluted")
    ebitda = income.get("ebitda")

    # Balance sheet
    total_assets = balance.get("total_assets")
    current_assets = balance.get("current_assets")
    current_liabilities = balance.get("current_liabilities")
    inventory = balance.get("inventory")
    receivables = balance.get("accounts_receivable")
    accounts_payable = balance.get("accounts_payable")
    long_term_debt = balance.get("long_term_debt")
    current_debt = balance.get("current_debt")
    equity = balance.get("total_stockholders_equity")
    cash = balance.get("cash_and_equivalents")
    securities = balance.get("marketable_securities")
    shares = balance.get("shares_outstanding")
    total_debt = balance.get("total_debt")

    # Cash flow
    operating_cf = cashflow.get("operating_cash_flow")
    capex = cashflow.get("capital_expenditures")
    fcf = cashflow.get("free_cash_flow")
    sbc = cashflow.get("stock_based_compensation")

    # --- Profitability ---
    gross_margin = round_val(safe_pct(gross_profit, revenue))
    if gross_margin is None and revenue and cogs:
        gross_margin = round_val(safe_pct(revenue - cogs, revenue))
    operating_margin = round_val(safe_pct(operating_income, revenue))
    net_margin = round_val(safe_pct(net_income, revenue))
    roa = round_val(safe_pct(net_income, total_assets)) if (net_income and total_assets) else None
    roe = round_val(safe_pct(net_income, equity)) if (net_income and equity and equity > 0) else None

    roic = None
    if net_income is not None and total_debt is not None and equity is not None:
        invested_capital = equity + total_debt
        if invested_capital > 0:
            roic = round_val(safe_pct(net_income, invested_capital))

    fcf_margin = round_val(safe_pct(fcf, revenue)) if fcf is not None else None

    profitability = asdict(ProfitabilityRatios(
        period=period, fiscal_year=fiscal_year,
        gross_margin_pct=gross_margin, operating_margin_pct=operating_margin,
        net_margin_pct=net_margin, return_on_assets_pct=roa,
        return_on_equity_pct=roe, return_on_invested_capital_pct=roic,
        free_cash_flow_margin_pct=fcf_margin,
    ))

    # --- Leverage ---
    d_to_e = round_val(total_debt / equity, 2) if (total_debt and equity and equity > 0) else None
    d_to_a = round_val(total_debt / total_assets, 2) if (total_debt and total_assets and total_assets > 0) else None

    interest_cov = None
    if operating_income and interest_expense and interest_expense > 0:
        interest_cov = round_val(operating_income / interest_expense, 2)

    net_debt_to_ebitda = None
    if total_debt is not None and cash is not None and ebitda and ebitda > 0:
        net_debt = total_debt - cash - (securities or 0)
        net_debt_to_ebitda = round_val(net_debt / ebitda, 2)

    equity_mult = round_val(total_assets / equity, 2) if (total_assets and equity and equity > 0) else None
    current_r = round_val(current_assets / current_liabilities, 2) if (current_assets and current_liabilities and current_liabilities > 0) else None

    quick_ratio = None
    if current_assets is not None and current_liabilities is not None and current_liabilities > 0:
        quick_assets = current_assets - (inventory or 0)
        quick_ratio = round_val(quick_assets / current_liabilities, 2)

    leverage = asdict(LeverageRatios(
        period=period, fiscal_year=fiscal_year,
        debt_to_equity=d_to_e, debt_to_assets=d_to_a,
        interest_coverage=interest_cov, net_debt_to_ebitda=net_debt_to_ebitda,
        equity_multiplier=equity_mult, current_ratio=current_r, quick_ratio=quick_ratio,
    ))

    # --- Valuation (per-share) ---
    bvps = round_val(equity / shares, 2) if (equity and shares and shares > 0) else None
    rev_per_share = round_val(revenue / shares, 2) if (revenue and shares and shares > 0) else None
    fcf_per_share = round_val(fcf / shares, 2) if (fcf is not None and shares and shares > 0) else None

    valuation = asdict(ValuationRatios(
        period=period, fiscal_year=fiscal_year,
        book_value_per_share=bvps, earnings_per_share=eps_diluted,
        revenue_per_share=rev_per_share, free_cash_flow_per_share=fcf_per_share,
    ))

    # --- Operating Efficiency ---
    asset_turnover = round_val(revenue / total_assets, 2) if (revenue and total_assets and total_assets > 0) else None

    inv_turnover = round_val(cogs / inventory, 2) if (cogs and inventory and inventory > 0) else None
    recv_turnover = round_val(revenue / receivables, 2) if (revenue and receivables and receivables > 0) else None
    pay_turnover = round_val(cogs / accounts_payable, 2) if (cogs and accounts_payable and accounts_payable > 0) else None

    dso = round_val(365 / recv_turnover, 1) if recv_turnover and recv_turnover > 0 else None
    dio = round_val(365 / inv_turnover, 1) if inv_turnover and inv_turnover > 0 else None
    dpo = round_val(365 / pay_turnover, 1) if pay_turnover and pay_turnover > 0 else None

    ccc = None
    if dso is not None and dio is not None and dpo is not None:
        ccc = round_val(dso + dio - dpo, 1)

    capex_to_rev = round_val(safe_pct(abs(capex), revenue)) if (capex and revenue and revenue > 0) else None
    sbc_to_rev = round_val(safe_pct(sbc, revenue)) if (sbc and revenue and revenue > 0) else None

    operating = asdict(OperatingRatios(
        period=period, fiscal_year=fiscal_year,
        asset_turnover=asset_turnover, inventory_turnover=inv_turnover,
        receivables_turnover=recv_turnover, payables_turnover=pay_turnover,
        days_sales_outstanding=dso, days_inventory_outstanding=dio,
        days_payable_outstanding=dpo, cash_conversion_cycle=ccc,
        capex_to_revenue_pct=capex_to_rev, sbc_to_revenue_pct=sbc_to_rev,
    ))

    return {
        "period": period,
        "fiscal_year": fiscal_year,
        "profitability": profitability,
        "leverage": leverage,
        "valuation": valuation,
        "operating": operating,
    }


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
        "income_data": Annotated[str, "JSON string from analyze_income_statement tool output"],
        "balance_sheet_data": Annotated[str, "JSON string from analyze_balance_sheet tool output"],
        "cash_flow_data": Annotated[str, "JSON string from analyze_cash_flow tool output"],
    },
)
async def analyze_financial_ratios(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        income_raw = json.loads(args["income_data"]) if isinstance(args["income_data"], str) else args["income_data"]
        balance_raw = json.loads(args["balance_sheet_data"]) if isinstance(args["balance_sheet_data"], str) else args["balance_sheet_data"]
        cashflow_raw = json.loads(args["cash_flow_data"]) if isinstance(args["cash_flow_data"], str) else args["cash_flow_data"]
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"success": False, "error": f"Invalid input data: {e}"})}],
            "is_error": True,
        }

    # Extract statement arrays
    income_statements = income_raw.get("report", {}).get("annual_statements", [])
    balance_sheets = balance_raw.get("balance_sheets", [])
    cash_flows = cashflow_raw.get("cash_flows", [])

    if not income_statements:
        return {
            "content": [{"type": "text", "text": json.dumps({"success": False, "error": "No income statement data provided"})}],
            "is_error": True,
        }

    ticker = income_raw.get("ticker", "")
    company_name = income_raw.get("report", {}).get("company_name", "")

    # Match periods across statements by fiscal_year
    ratios: List[Dict[str, Any]] = []

    for inc in income_statements:
        fy = inc.get("fiscal_year")
        period = inc.get("period", f"FY{fy}")

        # Find matching balance sheet and cash flow by fiscal year
        bs = next((b for b in balance_sheets if b.get("fiscal_year") == fy), {})
        cf = next((c for c in cash_flows if c.get("fiscal_year") == fy), {})

        period_ratios = _compute_period_ratios(inc, bs, cf)
        ratios.append(period_ratios)

    if not ratios:
        return {
            "content": [{"type": "text", "text": json.dumps({"success": False, "error": "Could not compute ratios — no matching periods"})}],
            "is_error": True,
        }

    latest = ratios[0]
    latest_prof = latest.get("profitability", {})
    latest_lev = latest.get("leverage", {})
    latest_op = latest.get("operating", {})

    result = {
        "success": True,
        "ticker": ticker,
        "company_name": company_name,
        "periods_analyzed": len(ratios),
        "ratios": ratios,
        "summary": {
            "latest_roe_pct": latest_prof.get("return_on_equity_pct"),
            "latest_roa_pct": latest_prof.get("return_on_assets_pct"),
            "latest_roic_pct": latest_prof.get("return_on_invested_capital_pct"),
            "latest_fcf_margin_pct": latest_prof.get("free_cash_flow_margin_pct"),
            "latest_debt_to_equity": latest_lev.get("debt_to_equity"),
            "latest_interest_coverage": latest_lev.get("interest_coverage"),
            "latest_net_debt_to_ebitda": latest_lev.get("net_debt_to_ebitda"),
            "latest_current_ratio": latest_lev.get("current_ratio"),
            "latest_quick_ratio": latest_lev.get("quick_ratio"),
            "latest_asset_turnover": latest_op.get("asset_turnover"),
            "latest_cash_conversion_cycle": latest_op.get("cash_conversion_cycle"),
        },
    }

    return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

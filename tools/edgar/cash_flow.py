import json
from dataclasses import asdict, dataclass, field
from typing import Annotated, Any, Dict, List, Optional

from edgar import Company, set_identity

from claude_agent_sdk import tool

from tools.edgar.xbrl import (
    get_all_periods_in_filing,
    get_period_value,
    round_val,
    safe_pct,
)

set_identity("Stock Analysis Tool contact@example.com")


OPERATING_CF_CONCEPTS = ["NetCashProvidedByUsedInOperatingActivities"]
INVESTING_CF_CONCEPTS = ["NetCashProvidedByUsedInInvestingActivities"]
FINANCING_CF_CONCEPTS = ["NetCashProvidedByUsedInFinancingActivities"]
DEPRECIATION_CONCEPTS = ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "Depreciation"]
CAPEX_CONCEPTS = ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpenditures"]
DIVIDENDS_CONCEPTS = ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"]
BUYBACKS_CONCEPTS = ["PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfEquity"]
DEBT_ISSUANCE_CONCEPTS = ["ProceedsFromIssuanceOfLongTermDebt", "ProceedsFromDebtNetOfIssuanceCosts"]
DEBT_REPAYMENT_CONCEPTS = ["RepaymentsOfLongTermDebt", "RepaymentsOfDebt"]
SBC_CONCEPTS = ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"]
ACQUISITIONS_CONCEPTS = ["PaymentsToAcquireBusinessesNetOfCashAcquired", "PaymentsToAcquireBusinessesAndInterestInAffiliates"]


@dataclass
class CashFlowMetrics:
    period: str
    period_type: str
    fiscal_year: Optional[int] = None
    filing_date: Optional[str] = None
    # Operating activities
    operating_cash_flow: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    stock_based_compensation: Optional[float] = None
    # Investing activities
    investing_cash_flow: Optional[float] = None
    capital_expenditures: Optional[float] = None
    acquisitions: Optional[float] = None
    # Financing activities
    financing_cash_flow: Optional[float] = None
    dividends_paid: Optional[float] = None
    share_buybacks: Optional[float] = None
    debt_issued: Optional[float] = None
    debt_repaid: Optional[float] = None
    # Derived
    free_cash_flow: Optional[float] = None
    fcf_margin_pct: Optional[float] = None
    capex_to_revenue_pct: Optional[float] = None
    shareholder_return: Optional[float] = None


def _extract_cash_flow(facts_view, period_end: str, fiscal_period: str, period_type: str,
                       filing_date: str, fiscal_year: Optional[int], revenue: Optional[float] = None) -> Optional[CashFlowMetrics]:
    def get_val(concepts):
        return get_period_value(facts_view, concepts, fiscal_period, period_end)

    operating_cf = get_val(OPERATING_CF_CONCEPTS)
    investing_cf = get_val(INVESTING_CF_CONCEPTS)
    financing_cf = get_val(FINANCING_CF_CONCEPTS)
    depreciation = get_val(DEPRECIATION_CONCEPTS)
    capex = get_val(CAPEX_CONCEPTS)
    dividends = get_val(DIVIDENDS_CONCEPTS)
    buybacks = get_val(BUYBACKS_CONCEPTS)
    debt_issued = get_val(DEBT_ISSUANCE_CONCEPTS)
    debt_repaid = get_val(DEBT_REPAYMENT_CONCEPTS)
    sbc = get_val(SBC_CONCEPTS)
    acquisitions = get_val(ACQUISITIONS_CONCEPTS)

    if operating_cf is None and investing_cf is None:
        return None

    # Free cash flow = Operating CF - CapEx
    free_cash_flow = None
    if operating_cf is not None and capex is not None:
        free_cash_flow = operating_cf - abs(capex)
    elif operating_cf is not None:
        free_cash_flow = operating_cf

    fcf_margin = None
    if free_cash_flow is not None and revenue is not None and revenue > 0:
        fcf_margin = round_val(safe_pct(free_cash_flow, revenue))

    capex_to_revenue = None
    if capex is not None and revenue is not None and revenue > 0:
        capex_to_revenue = round_val(safe_pct(abs(capex), revenue))

    shareholder_return = None
    if dividends is not None or buybacks is not None:
        shareholder_return = abs(dividends or 0) + abs(buybacks or 0)

    display_year = fiscal_year or (int(period_end[:4]) if period_end else None)
    period_label = f"FY{display_year}" if fiscal_period == "FY" else f"{display_year}-{fiscal_period}"

    return CashFlowMetrics(
        period=period_label,
        period_type=period_type,
        fiscal_year=display_year,
        filing_date=filing_date,
        operating_cash_flow=operating_cf,
        depreciation_amortization=depreciation,
        stock_based_compensation=sbc,
        investing_cash_flow=investing_cf,
        capital_expenditures=capex,
        acquisitions=acquisitions,
        financing_cash_flow=financing_cf,
        dividends_paid=dividends,
        share_buybacks=buybacks,
        debt_issued=debt_issued,
        debt_repaid=debt_repaid,
        free_cash_flow=free_cash_flow,
        fcf_margin_pct=fcf_margin,
        capex_to_revenue_pct=capex_to_revenue,
        shareholder_return=shareholder_return,
    )


def _fetch_cash_flows(company: Company, num_years: int = 5) -> List[CashFlowMetrics]:
    filings = company.get_filings(form="10-K").head(num_years)
    if not filings or len(filings) == 0:
        return []

    # Get revenue for FCF margin calculation
    from tools.edgar.xbrl import REVENUE_CONCEPTS
    collected: Dict[str, CashFlowMetrics] = {}

    for filing in filings:
        xbrl = filing.xbrl()
        if not xbrl:
            continue

        facts = xbrl.facts
        periods = get_all_periods_in_filing(facts, "FY")

        for period_info in periods:
            pe = period_info["period_end"]
            if pe in collected:
                continue

            revenue = get_period_value(facts, REVENUE_CONCEPTS, "FY", pe)
            metrics = _extract_cash_flow(
                facts, pe, "FY", "annual", str(filing.filing_date),
                period_info["fiscal_year"], revenue=revenue
            )
            if metrics:
                collected[pe] = metrics

        if len(collected) >= num_years:
            break

    statements = sorted(collected.values(), key=lambda m: m.period, reverse=True)
    return statements[:num_years]


@tool(
    "analyze_cash_flow",
    "Comprehensive cash flow statement analysis using SEC EDGAR XBRL data. "
    "Provides multi-year operating, investing, and financing cash flows, "
    "free cash flow, FCF margin, CapEx intensity, shareholder returns (dividends + buybacks), "
    "and debt activity.",
    {
        "ticker": Annotated[str, "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"],
        "num_years": Annotated[int, "Number of annual periods to analyze (default 5)"],
    },
)
async def analyze_cash_flow(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = args["ticker"]
    num_years = args.get("num_years", 5)

    try:
        company = Company(ticker)
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"success":False,"error":str(e)})}],
            "is_error": True,
        }

    statements = _fetch_cash_flows(company, num_years=num_years)

    if not statements:
        return {
            "content": [{"type": "text", "text": json.dumps({"success": False, "error": "No cash flow data found", "ticker": ticker.upper()})}],
            "is_error": True,
        }

    result = {
        "success": True,
        "ticker": ticker.upper(),
        "company_name": company.name,
        "cash_flows": [asdict(s) for s in statements],
        "latest": asdict(statements[0]),
        "summary": {
            "periods_covered": len(statements),
            "latest_operating_cf": statements[0].operating_cash_flow,
            "latest_free_cash_flow": statements[0].free_cash_flow,
            "latest_fcf_margin_pct": statements[0].fcf_margin_pct,
            "latest_capex": statements[0].capital_expenditures,
            "latest_shareholder_return": statements[0].shareholder_return,
            "latest_dividends": statements[0].dividends_paid,
            "latest_buybacks": statements[0].share_buybacks,
        },
    }

    from tools.edgar._serialize import tool_response
    return tool_response(result)

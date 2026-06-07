import json
from dataclasses import asdict, dataclass, field
from typing import Annotated, Any, Dict, List, Optional

from edgar import Company, set_identity

from claude_agent_sdk import tool

from tools.edgar.xbrl import (
    get_all_periods_in_filing,
    round_val,
    safe_pct,
)

set_identity("Stock Analysis Tool contact@example.com")


TOTAL_ASSETS_CONCEPTS = ["Assets"]
CURRENT_ASSETS_CONCEPTS = ["AssetsCurrent"]
NONCURRENT_ASSETS_CONCEPTS = ["AssetsNoncurrent"]
CASH_CONCEPTS = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments"]
MARKETABLE_SECURITIES_CONCEPTS = ["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesCurrent"]
RECEIVABLES_CONCEPTS = ["AccountsReceivableNetCurrent", "AccountsReceivableNet", "ReceivablesNetCurrent"]
INVENTORY_CONCEPTS = ["InventoryNet", "Inventories"]
PPE_CONCEPTS = ["PropertyPlantAndEquipmentNet"]
GOODWILL_CONCEPTS = ["Goodwill"]
INTANGIBLES_CONCEPTS = ["IntangibleAssetsNetExcludingGoodwill"]
TOTAL_LIABILITIES_CONCEPTS = ["Liabilities"]
CURRENT_LIABILITIES_CONCEPTS = ["LiabilitiesCurrent"]
NONCURRENT_LIABILITIES_CONCEPTS = ["LiabilitiesNoncurrent"]
LONG_TERM_DEBT_CONCEPTS = ["LongTermDebtNoncurrent", "LongTermDebt"]
CURRENT_DEBT_CONCEPTS = ["LongTermDebtCurrent", "ShortTermBorrowings", "CommercialPaper"]
ACCOUNTS_PAYABLE_CONCEPTS = ["AccountsPayableCurrent"]
STOCKHOLDERS_EQUITY_CONCEPTS = ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
RETAINED_EARNINGS_CONCEPTS = ["RetainedEarningsAccumulatedDeficit"]
SHARES_OUTSTANDING_CONCEPTS = ["CommonStockSharesOutstanding"]


@dataclass
class BalanceSheetMetrics:
    period: str
    period_instant: Optional[str] = None
    fiscal_year: Optional[int] = None
    filing_date: Optional[str] = None
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    noncurrent_assets: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    marketable_securities: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    property_plant_equipment: Optional[float] = None
    goodwill: Optional[float] = None
    intangible_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    noncurrent_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    current_debt: Optional[float] = None
    accounts_payable: Optional[float] = None
    total_stockholders_equity: Optional[float] = None
    retained_earnings: Optional[float] = None
    shares_outstanding: Optional[float] = None
    # Derived
    working_capital: Optional[float] = None
    total_debt: Optional[float] = None
    net_cash: Optional[float] = None
    book_value_per_share: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None


def _get_instant_value(facts_view, concepts: List[str], period_instant: str, use_max: bool = False) -> Optional[float]:
    """Get a balance sheet value for a specific instant date.

    For aggregates like total Assets, set use_max=True
    to pick the largest value (the true total, not a subtotal).
    """
    import pandas as pd
    for concept in concepts:
        try:
            df = facts_view.get_facts_by_concept(concept)
            if df is None or df.empty:
                continue
            filtered = df[
                (df["is_dimensioned"] == False) &
                (df["period_instant"] == period_instant)
            ]
            if filtered.empty:
                continue

            val_col = "numeric_value" if "numeric_value" in filtered.columns else "value"
            numeric_rows = filtered[filtered[val_col].apply(lambda x: isinstance(x, (int, float)) and pd.notna(x))]
            if numeric_rows.empty:
                continue

            if len(numeric_rows) > 1 and "statement_name" in numeric_rows.columns:
                bs_rows = numeric_rows[
                    numeric_rows["statement_name"].str.lower().apply(
                        lambda x: any(kw in str(x) for kw in ("balance", "position", "condition"))
                    )
                ]
                if not bs_rows.empty:
                    numeric_rows = bs_rows

            if use_max and len(numeric_rows) > 1:
                val = numeric_rows[val_col].max()
            else:
                val = numeric_rows.iloc[0][val_col]
            return float(val)
        except Exception:
            continue
    return None


def _get_total_assets(facts_view, period_instant: str) -> Optional[float]:
    """Get total assets — always the largest value for Assets concept."""
    return _get_instant_value(facts_view, TOTAL_ASSETS_CONCEPTS, period_instant, use_max=True)


def _get_total_liabilities(facts_view, period_instant: str) -> Optional[float]:
    """Get total liabilities, excluding the 'Liabilities + Equity' combined line."""
    import pandas as pd
    total_assets = _get_total_assets(facts_view, period_instant)

    for concept in TOTAL_LIABILITIES_CONCEPTS:
        try:
            df = facts_view.get_facts_by_concept(concept)
            if df is None or df.empty:
                continue
            filtered = df[
                (df["is_dimensioned"] == False) &
                (df["period_instant"] == period_instant)
            ]
            if filtered.empty:
                continue

            val_col = "numeric_value" if "numeric_value" in filtered.columns else "value"
            numeric_rows = filtered[filtered[val_col].apply(lambda x: isinstance(x, (int, float)) and pd.notna(x))]
            if numeric_rows.empty:
                continue

            if len(numeric_rows) > 1 and "statement_name" in numeric_rows.columns:
                bs_rows = numeric_rows[
                    numeric_rows["statement_name"].str.lower().apply(
                        lambda x: any(kw in str(x) for kw in ("balance", "position", "condition"))
                    )
                ]
                if not bs_rows.empty:
                    numeric_rows = bs_rows

            sorted_vals = numeric_rows[val_col].sort_values(ascending=False)
            for val in sorted_vals:
                fval = float(val)
                if total_assets and abs(fval - total_assets) < 1000:
                    continue
                return fval
            return float(sorted_vals.iloc[0])
        except Exception:
            continue
    return None


def _get_stockholders_equity(facts_view, period_instant: str) -> Optional[float]:
    """Get stockholders equity, excluding the 'Liabilities + Equity' combined line."""
    import pandas as pd
    total_assets = _get_total_assets(facts_view, period_instant)

    for concept in STOCKHOLDERS_EQUITY_CONCEPTS:
        try:
            df = facts_view.get_facts_by_concept(concept)
            if df is None or df.empty:
                continue
            filtered = df[
                (df["is_dimensioned"] == False) &
                (df["period_instant"] == period_instant)
            ]
            if filtered.empty:
                continue

            val_col = "numeric_value" if "numeric_value" in filtered.columns else "value"
            numeric_rows = filtered[filtered[val_col].apply(lambda x: isinstance(x, (int, float)) and pd.notna(x))]
            if numeric_rows.empty:
                continue

            if len(numeric_rows) > 1 and "statement_name" in numeric_rows.columns:
                bs_rows = numeric_rows[
                    numeric_rows["statement_name"].str.lower().apply(
                        lambda x: any(kw in str(x) for kw in ("balance", "position", "condition"))
                    )
                ]
                if not bs_rows.empty:
                    numeric_rows = bs_rows

            sorted_vals = numeric_rows[val_col].sort_values(ascending=False)
            for val in sorted_vals:
                fval = float(val)
                if total_assets and abs(fval - total_assets) < 1000:
                    continue
                return fval
            return float(sorted_vals.iloc[0])
        except Exception:
            continue
    return None


def _get_balance_sheet_dates(facts_view, num_periods: int = 5) -> List[Dict[str, Any]]:
    """Get available balance sheet instant dates from Assets concept."""
    import pandas as pd
    for concept in TOTAL_ASSETS_CONCEPTS + STOCKHOLDERS_EQUITY_CONCEPTS:
        try:
            df = facts_view.get_facts_by_concept(concept)
            if df is None or df.empty:
                continue
            val_col = "numeric_value" if "numeric_value" in df.columns else "value"
            filtered = df[
                (df["is_dimensioned"] == False) &
                (df[val_col].apply(lambda x: isinstance(x, (int, float)) and pd.notna(x)))
            ]
            if filtered.empty:
                continue

            periods = []
            seen = set()
            sorted_df = filtered.sort_values("period_instant", ascending=False)
            for _, row in sorted_df.iterrows():
                pi = row["period_instant"]
                if pi in seen or pd.isna(pi):
                    continue
                seen.add(pi)
                fy = int(row["fiscal_year"]) if pd.notna(row.get("fiscal_year")) else None
                periods.append({"period_instant": str(pi), "fiscal_year": fy})
            if periods:
                return periods[:num_periods]
        except Exception:
            continue
    return []


def _extract_balance_sheet(facts_view, period_instant: str, fiscal_year: Optional[int], filing_date: str) -> Optional[BalanceSheetMetrics]:
    def get_val(concepts, use_max=False):
        return _get_instant_value(facts_view, concepts, period_instant, use_max=use_max)

    total_assets = _get_total_assets(facts_view, period_instant)
    current_assets = get_val(CURRENT_ASSETS_CONCEPTS, use_max=True)
    noncurrent_assets = get_val(NONCURRENT_ASSETS_CONCEPTS, use_max=True)
    cash = get_val(CASH_CONCEPTS)
    securities = get_val(MARKETABLE_SECURITIES_CONCEPTS)
    receivables = get_val(RECEIVABLES_CONCEPTS)
    inventory = get_val(INVENTORY_CONCEPTS)
    ppe = get_val(PPE_CONCEPTS)
    goodwill = get_val(GOODWILL_CONCEPTS)
    intangibles = get_val(INTANGIBLES_CONCEPTS)
    total_liabilities = _get_total_liabilities(facts_view, period_instant)
    current_liabilities = get_val(CURRENT_LIABILITIES_CONCEPTS, use_max=True)
    noncurrent_liabilities = get_val(NONCURRENT_LIABILITIES_CONCEPTS, use_max=True)
    long_term_debt = get_val(LONG_TERM_DEBT_CONCEPTS, use_max=True)
    current_debt = get_val(CURRENT_DEBT_CONCEPTS)
    accounts_payable = get_val(ACCOUNTS_PAYABLE_CONCEPTS)
    equity = _get_stockholders_equity(facts_view, period_instant)
    retained_earnings = get_val(RETAINED_EARNINGS_CONCEPTS)
    shares = get_val(SHARES_OUTSTANDING_CONCEPTS, use_max=True)

    if total_assets is None and equity is None:
        return None

    # Derived metrics
    working_capital = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    total_debt = None
    if long_term_debt is not None or current_debt is not None:
        total_debt = (long_term_debt or 0) + (current_debt or 0)

    net_cash = None
    if cash is not None and total_debt is not None:
        net_cash = cash + (securities or 0) - total_debt

    book_value_per_share = None
    if equity is not None and shares is not None and shares > 0:
        book_value_per_share = round_val(equity / shares, 2)

    current_ratio = None
    if current_assets is not None and current_liabilities is not None and current_liabilities > 0:
        current_ratio = round_val(current_assets / current_liabilities, 2)

    debt_to_equity = None
    if total_debt is not None and equity is not None and equity > 0:
        debt_to_equity = round_val(total_debt / equity, 2)

    debt_to_assets = None
    if total_debt is not None and total_assets is not None and total_assets > 0:
        debt_to_assets = round_val(total_debt / total_assets, 2)

    period_label = f"FY{fiscal_year}" if fiscal_year else period_instant

    return BalanceSheetMetrics(
        period=period_label,
        period_instant=period_instant,
        fiscal_year=fiscal_year,
        filing_date=filing_date,
        total_assets=total_assets,
        current_assets=current_assets,
        noncurrent_assets=noncurrent_assets,
        cash_and_equivalents=cash,
        marketable_securities=securities,
        accounts_receivable=receivables,
        inventory=inventory,
        property_plant_equipment=ppe,
        goodwill=goodwill,
        intangible_assets=intangibles,
        total_liabilities=total_liabilities,
        current_liabilities=current_liabilities,
        noncurrent_liabilities=noncurrent_liabilities,
        long_term_debt=long_term_debt,
        current_debt=current_debt,
        accounts_payable=accounts_payable,
        total_stockholders_equity=equity,
        retained_earnings=retained_earnings,
        shares_outstanding=shares,
        working_capital=working_capital,
        total_debt=total_debt,
        net_cash=net_cash,
        book_value_per_share=book_value_per_share,
        current_ratio=current_ratio,
        debt_to_equity=debt_to_equity,
        debt_to_assets=debt_to_assets,
    )


def _fetch_balance_sheets(company: Company, num_years: int = 5) -> List[BalanceSheetMetrics]:
    filings = company.get_filings(form="10-K").head(num_years)
    if not filings or len(filings) == 0:
        return []

    collected: Dict[str, BalanceSheetMetrics] = {}

    for filing in filings:
        xbrl = filing.xbrl()
        if not xbrl:
            continue

        facts = xbrl.facts
        dates = _get_balance_sheet_dates(facts, num_periods=num_years)

        for date_info in dates:
            pi = date_info["period_instant"]
            if pi in collected:
                continue

            metrics = _extract_balance_sheet(facts, pi, date_info["fiscal_year"], str(filing.filing_date))
            if metrics:
                collected[pi] = metrics

        if len(collected) >= num_years:
            break

    statements = sorted(collected.values(), key=lambda m: m.period, reverse=True)
    return statements[:num_years]


@tool(
    "analyze_balance_sheet",
    "Comprehensive balance sheet analysis using SEC EDGAR XBRL data. "
    "Provides multi-year annual balance sheets with assets, liabilities, equity breakdown, "
    "working capital, debt structure, and key ratios (current ratio, debt/equity, debt/assets).",
    {
        "ticker": Annotated[str, "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"],
        "num_years": Annotated[int, "Number of annual periods to analyze (default 5)"],
    },
)
async def analyze_balance_sheet(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = args["ticker"]
    num_years = args.get("num_years", 5)

    try:
        company = Company(ticker)
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"success":False,"error":str(e)})}],
            "is_error": True,
        }

    statements = _fetch_balance_sheets(company, num_years=num_years)

    if not statements:
        return {
            "content": [{"type": "text", "text": json.dumps({"success": False, "error": "No balance sheet data found", "ticker": ticker.upper()})}],
            "is_error": True,
        }

    result = {
        "success": True,
        "ticker": ticker.upper(),
        "company_name": company.name,
        "balance_sheets": [asdict(s) for s in statements],
        "latest": asdict(statements[0]),
        "summary": {
            "periods_covered": len(statements),
            "latest_total_assets": statements[0].total_assets,
            "latest_total_liabilities": statements[0].total_liabilities,
            "latest_equity": statements[0].total_stockholders_equity,
            "latest_total_debt": statements[0].total_debt,
            "latest_net_cash": statements[0].net_cash,
            "latest_current_ratio": statements[0].current_ratio,
            "latest_debt_to_equity": statements[0].debt_to_equity,
            "latest_book_value_per_share": statements[0].book_value_per_share,
        },
    }

    from tools.edgar._serialize import tool_response
    return tool_response(result)

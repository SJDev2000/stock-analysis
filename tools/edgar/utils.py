"""
EdgarUtils — all stateless helpers for EDGAR data extraction and response building.

Covers: XBRL value extraction, income/balance-sheet/cash-flow parsing,
financial ratio computation, asset serialisation, and MCP response construction.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from tools.edgar.models import (
    BalanceSheetMetrics,
    CashFlowMetrics,
    GrowthMetrics,
    GrowthMomentum,
    IncomeMetrics,
    LeverageRatios,
    OperatingRatios,
    ProfitabilityRatios,
    SegmentRevenue,
    ValuationRatios,
)
from tools.edgar.xbrl import (
    COGS_CONCEPTS,
    REVENUE_CONCEPTS,
    get_period_value,
    round_val,
    safe_pct,
)

_ASSETS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "edgar"

# ---------------------------------------------------------------------------
# XBRL concept registries
# ---------------------------------------------------------------------------

BS_CONCEPTS: Dict[str, List[str]] = {
    "total_assets":        ["Assets"],
    "current_assets":      ["AssetsCurrent"],
    "noncurrent_assets":   ["AssetsNoncurrent"],
    "cash":                ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments"],
    "securities":          ["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesCurrent"],
    "receivables":         ["AccountsReceivableNetCurrent", "AccountsReceivableNet", "ReceivablesNetCurrent"],
    "inventory":           ["InventoryNet", "Inventories"],
    "ppe":                 ["PropertyPlantAndEquipmentNet"],
    "goodwill":            ["Goodwill"],
    "intangibles":         ["IntangibleAssetsNetExcludingGoodwill"],
    "total_liabilities":   ["Liabilities"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "noncurrent_liabilities": ["LiabilitiesNoncurrent"],
    "long_term_debt":      ["LongTermDebtNoncurrent", "LongTermDebt"],
    "current_debt":        ["LongTermDebtCurrent", "ShortTermBorrowings", "CommercialPaper"],
    "accounts_payable":    ["AccountsPayableCurrent"],
    "equity":              ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "retained_earnings":   ["RetainedEarningsAccumulatedDeficit"],
    "shares":              ["CommonStockSharesOutstanding"],
}

CF_CONCEPTS: Dict[str, List[str]] = {
    "operating":    ["NetCashProvidedByUsedInOperatingActivities"],
    "investing":    ["NetCashProvidedByUsedInInvestingActivities"],
    "financing":    ["NetCashProvidedByUsedInFinancingActivities"],
    "depreciation": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "Depreciation"],
    "capex":        ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpenditures"],
    "dividends":    ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "buybacks":     ["PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfEquity"],
    "debt_issued":  ["ProceedsFromIssuanceOfLongTermDebt", "ProceedsFromDebtNetOfIssuanceCosts"],
    "debt_repaid":  ["RepaymentsOfLongTermDebt", "RepaymentsOfDebt"],
    "sbc":          ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "acquisitions": ["PaymentsToAcquireBusinessesNetOfCashAcquired", "PaymentsToAcquireBusinessesAndInterestInAffiliates"],
}

# ---------------------------------------------------------------------------
# EdgarUtils
# ---------------------------------------------------------------------------

class EdgarUtils:
    """Stateless helpers — call as class methods."""

    # ------------------------------------------------------------------ #
    # Asset persistence                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def asset_path(ticker: str, report_type: str) -> Path:
        _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        return _ASSETS_DIR / f"{ticker.upper()}_edgar_{report_type}.json"

    @staticmethod
    def save_asset(path: Path, data: Any) -> None:
        # Overwrite any previous run — only one file per ticker+report_type
        path.unlink(missing_ok=True)
        path.write_text(
            json.dumps(EdgarUtils.strip_nulls(data), default=str, separators=(",", ":"))
        )

    # ------------------------------------------------------------------ #
    # MCP response builders                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ok_response(ticker: str, report_type: str, asset_path: Path, summary: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "success": True,
            "ticker": ticker,
            "report_type": report_type,
            "asset_path": str(asset_path),
            "summary": summary,
        }
        return {"content": [{"type": "text", "text": json.dumps(EdgarUtils.strip_nulls(payload), default=str, indent=2)}]}

    @staticmethod
    def err_response(error: str, **extra) -> Dict[str, Any]:
        payload = {"success": False, "error": error, **extra}
        return {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
            "is_error": True,
        }

    # ------------------------------------------------------------------ #
    # Serialisation                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def strip_nulls(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: EdgarUtils.strip_nulls(v) for k, v in obj.items() if v is not None}
        if isinstance(obj, list):
            return [EdgarUtils.strip_nulls(i) for i in obj]
        return obj

    # ------------------------------------------------------------------ #
    # XBRL instant-date value extraction (balance sheet)                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def instant_value(facts, concepts: List[str], instant: str, use_max: bool = False) -> Optional[float]:
        for concept in concepts:
            try:
                df = facts.get_facts_by_concept(concept)
                if df is None or df.empty:
                    continue
                rows = df[(df["is_dimensioned"] == False) & (df["period_instant"] == instant)]
                if rows.empty:
                    continue
                col = "numeric_value" if "numeric_value" in rows.columns else "value"
                rows = rows[rows[col].apply(lambda x: isinstance(x, (int, float)) and pd.notna(x))]
                if rows.empty:
                    continue
                if len(rows) > 1 and "statement_name" in rows.columns:
                    bs = rows[rows["statement_name"].str.lower().apply(
                        lambda x: any(kw in str(x) for kw in ("balance", "position", "condition"))
                    )]
                    if not bs.empty:
                        rows = bs
                val = rows[col].max() if (use_max and len(rows) > 1) else rows.iloc[0][col]
                return float(val)
            except Exception:
                continue
        return None

    @staticmethod
    def exclusive_instant(facts, concepts: List[str], instant: str, exclude_near: Optional[float]) -> Optional[float]:
        """Largest value not suspiciously close to exclude_near — avoids L+E combined lines."""
        for concept in concepts:
            try:
                df = facts.get_facts_by_concept(concept)
                if df is None or df.empty:
                    continue
                rows = df[(df["is_dimensioned"] == False) & (df["period_instant"] == instant)]
                if rows.empty:
                    continue
                col = "numeric_value" if "numeric_value" in rows.columns else "value"
                rows = rows[rows[col].apply(lambda x: isinstance(x, (int, float)) and pd.notna(x))]
                if rows.empty:
                    continue
                if len(rows) > 1 and "statement_name" in rows.columns:
                    bs = rows[rows["statement_name"].str.lower().apply(
                        lambda x: any(kw in str(x) for kw in ("balance", "position", "condition"))
                    )]
                    if not bs.empty:
                        rows = bs
                for val in rows[col].sort_values(ascending=False):
                    fval = float(val)
                    if exclude_near and abs(fval - exclude_near) < 1000:
                        continue
                    return fval
                return float(rows[col].iloc[0])
            except Exception:
                continue
        return None

    @staticmethod
    def balance_sheet_dates(facts, num_periods: int) -> List[Dict[str, Any]]:
        for key in ("total_assets", "equity"):
            try:
                df = facts.get_facts_by_concept(BS_CONCEPTS[key][0])
                if df is None or df.empty:
                    continue
                col = "numeric_value" if "numeric_value" in df.columns else "value"
                rows = df[(df["is_dimensioned"] == False) & (
                    df[col].apply(lambda x: isinstance(x, (int, float)) and pd.notna(x))
                )]
                if rows.empty:
                    continue
                seen, periods = set(), []
                for _, row in rows.sort_values("period_instant", ascending=False).iterrows():
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

    # ------------------------------------------------------------------ #
    # Balance sheet extraction                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def extract_balance_sheet(facts, instant: str, fiscal_year: Optional[int], filing_date: str) -> Optional[BalanceSheetMetrics]:
        get = lambda key, use_max=False: EdgarUtils.instant_value(facts, BS_CONCEPTS[key], instant, use_max)

        ta  = EdgarUtils.instant_value(facts, BS_CONCEPTS["total_assets"], instant, use_max=True)
        tl  = EdgarUtils.exclusive_instant(facts, BS_CONCEPTS["total_liabilities"], instant, ta)
        eq  = EdgarUtils.exclusive_instant(facts, BS_CONCEPTS["equity"], instant, ta)
        ca  = get("current_assets", True)
        cl  = get("current_liabilities", True)
        ltd = get("long_term_debt", True)
        cd  = get("current_debt")

        if ta is None and eq is None:
            return None

        total_debt = (ltd or 0) + (cd or 0) if (ltd is not None or cd is not None) else None
        cash, sec  = get("cash"), get("securities")
        net_cash   = cash + (sec or 0) - total_debt if (cash is not None and total_debt is not None) else None
        shares     = get("shares", True)

        return BalanceSheetMetrics(
            period          = f"FY{fiscal_year}" if fiscal_year else instant,
            period_instant  = instant,
            fiscal_year     = fiscal_year,
            filing_date     = filing_date,
            total_assets    = ta,
            current_assets  = ca,
            noncurrent_assets       = get("noncurrent_assets", True),
            cash_and_equivalents    = cash,
            marketable_securities   = sec,
            accounts_receivable     = get("receivables"),
            inventory               = get("inventory"),
            property_plant_equipment= get("ppe"),
            goodwill                = get("goodwill"),
            intangible_assets       = get("intangibles"),
            total_liabilities       = tl,
            current_liabilities     = cl,
            noncurrent_liabilities  = get("noncurrent_liabilities", True),
            long_term_debt          = ltd,
            current_debt            = cd,
            accounts_payable        = get("accounts_payable"),
            total_stockholders_equity = eq,
            retained_earnings       = get("retained_earnings"),
            shares_outstanding      = shares,
            working_capital         = ca - cl if (ca is not None and cl is not None) else None,
            total_debt              = total_debt,
            net_cash                = net_cash,
            book_value_per_share    = round_val(eq / shares, 2)    if (eq and shares and shares > 0)                else None,
            current_ratio           = round_val(ca / cl, 2)        if (ca and cl and cl > 0)                        else None,
            debt_to_equity          = round_val(total_debt / eq, 2) if (total_debt and eq and eq > 0)               else None,
            debt_to_assets          = round_val(total_debt / ta, 2) if (total_debt and ta and ta > 0)               else None,
        )

    # ------------------------------------------------------------------ #
    # Income statement extraction                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def extract_income(facts, period_end: str, fiscal_period: str, period_type: str,
                       filing_date: str, fiscal_year: Optional[int] = None) -> Optional[IncomeMetrics]:
        display_year  = int(period_end[:4]) if period_end else fiscal_year
        period_label  = f"FY{display_year}" if fiscal_period == "FY" else f"{display_year}-{fiscal_period}"

        def get(concepts):
            return get_period_value(facts, concepts, fiscal_period, period_end)

        revenue    = get(REVENUE_CONCEPTS)
        net_income = get(["NetIncomeLoss"])
        if revenue is None and net_income is None:
            return None

        cogs        = get(COGS_CONCEPTS)
        gross_profit = get(["GrossProfit"]) or (revenue - cogs if (revenue and cogs) else None)
        op_income   = get(["OperatingIncomeLoss"])
        depreciation = get(["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "Depreciation"])
        ebitda      = op_income + (depreciation or 0) if op_income is not None else None

        return IncomeMetrics(
            period              = period_label,
            period_type         = period_type,
            fiscal_year         = display_year,
            fiscal_period       = fiscal_period,
            filing_date         = filing_date,
            revenue             = revenue,
            cost_of_revenue     = cogs,
            gross_profit        = gross_profit,
            gross_margin_pct    = round_val(safe_pct(gross_profit, revenue)),
            operating_expenses  = gross_profit - op_income if (gross_profit and op_income is not None) else None,
            research_and_development = get(["ResearchAndDevelopmentExpense"]),
            selling_general_admin    = get(["SellingGeneralAndAdministrativeExpense"]),
            operating_income    = op_income,
            operating_margin_pct= round_val(safe_pct(op_income, revenue)),
            interest_expense    = get(["InterestExpense"]),
            other_income_expense= get(["NonoperatingIncomeExpense"]),
            income_before_tax   = get(["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"]),
            income_tax_expense  = get(["IncomeTaxExpenseBenefit"]),
            net_income          = net_income,
            net_margin_pct      = round_val(safe_pct(net_income, revenue)),
            ebitda              = ebitda,
            ebitda_margin_pct   = round_val(safe_pct(ebitda, revenue)),
            eps_basic           = get(["EarningsPerShareBasic"]),
            eps_diluted         = get(["EarningsPerShareDiluted"]),
            shares_outstanding_basic    = get(["WeightedAverageNumberOfSharesOutstandingBasic"]),
            shares_outstanding_diluted  = get(["WeightedAverageNumberOfDilutedSharesOutstanding"]),
        )

    @staticmethod
    def apply_split(m: IncomeMetrics, ratio: float) -> None:
        if m.eps_basic is not None:
            m.eps_basic = round_val(m.eps_basic / ratio, 4)
        if m.eps_diluted is not None:
            m.eps_diluted = round_val(m.eps_diluted / ratio, 4)
        if m.shares_outstanding_basic is not None:
            m.shares_outstanding_basic *= ratio
        if m.shares_outstanding_diluted is not None:
            m.shares_outstanding_diluted *= ratio

    # ------------------------------------------------------------------ #
    # Growth / momentum metrics                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _delta(a, b) -> Optional[float]:
        return round(a - b, 2) if (a is not None and b is not None) else None

    @staticmethod
    def _pct(a, b) -> Optional[float]:
        return round((a - b) / abs(b) * 100, 2) if (a is not None and b is not None and b != 0) else None

    @staticmethod
    def _bps(a, b) -> Optional[float]:
        return round((a - b) * 100, 1) if (a is not None and b is not None) else None

    @staticmethod
    def growth_metrics(cur: IncomeMetrics, prior: IncomeMetrics, gtype: str) -> GrowthMetrics:
        d, p, b = EdgarUtils._delta, EdgarUtils._pct, EdgarUtils._bps
        return GrowthMetrics(
            period=cur.period, comparison_period=prior.period, growth_type=gtype,
            revenue_growth_abs              = d(cur.revenue,          prior.revenue),
            revenue_growth_pct              = p(cur.revenue,          prior.revenue),
            gross_profit_growth_abs         = d(cur.gross_profit,     prior.gross_profit),
            gross_profit_growth_pct         = p(cur.gross_profit,     prior.gross_profit),
            operating_income_growth_abs     = d(cur.operating_income, prior.operating_income),
            operating_income_growth_pct     = p(cur.operating_income, prior.operating_income),
            net_income_growth_abs           = d(cur.net_income,       prior.net_income),
            net_income_growth_pct           = p(cur.net_income,       prior.net_income),
            ebitda_growth_abs               = d(cur.ebitda,           prior.ebitda),
            ebitda_growth_pct               = p(cur.ebitda,           prior.ebitda),
            eps_diluted_growth_abs          = d(cur.eps_diluted,      prior.eps_diluted),
            eps_diluted_growth_pct          = p(cur.eps_diluted,      prior.eps_diluted),
            margin_expansion_gross_bps      = b(cur.gross_margin_pct,     prior.gross_margin_pct),
            margin_expansion_operating_bps  = b(cur.operating_margin_pct, prior.operating_margin_pct),
            margin_expansion_net_bps        = b(cur.net_margin_pct,       prior.net_margin_pct),
        )

    @staticmethod
    def growth_momentum(cur: IncomeMetrics, prior: IncomeMetrics, gtype: str) -> GrowthMomentum:
        d, p = EdgarUtils._delta, EdgarUtils._pct
        return GrowthMomentum(
            period=cur.period, comparison_period=prior.period, growth_type=gtype,
            revenue_growth_dollar      = d(cur.revenue,     prior.revenue),
            revenue_growth_pct         = p(cur.revenue,     prior.revenue),
            net_income_growth_dollar   = d(cur.net_income,  prior.net_income),
            net_income_growth_pct      = p(cur.net_income,  prior.net_income),
            eps_growth_dollar          = d(cur.eps_diluted, prior.eps_diluted),
            eps_growth_pct             = p(cur.eps_diluted, prior.eps_diluted),
        )

    # ------------------------------------------------------------------ #
    # Cash flow extraction                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def extract_cash_flow(facts, period_end: str, fiscal_year: Optional[int], filing_date: str) -> Optional[CashFlowMetrics]:
        def get(key):
            return get_period_value(facts, CF_CONCEPTS[key], "FY", period_end)

        ocf = get("operating")
        inv = get("investing")
        if ocf is None and inv is None:
            return None

        capex   = get("capex")
        revenue = get_period_value(facts, REVENUE_CONCEPTS, "FY", period_end)
        fcf     = ocf - abs(capex) if (ocf is not None and capex is not None) else ocf
        divs    = get("dividends")
        buybacks = get("buybacks")

        return CashFlowMetrics(
            period                  = f"FY{fiscal_year}",
            period_type             = "annual",
            fiscal_year             = fiscal_year,
            filing_date             = filing_date,
            operating_cash_flow     = ocf,
            depreciation_amortization = get("depreciation"),
            stock_based_compensation  = get("sbc"),
            investing_cash_flow     = inv,
            capital_expenditures    = capex,
            acquisitions            = get("acquisitions"),
            financing_cash_flow     = get("financing"),
            dividends_paid          = divs,
            share_buybacks          = buybacks,
            debt_issued             = get("debt_issued"),
            debt_repaid             = get("debt_repaid"),
            free_cash_flow          = fcf,
            fcf_margin_pct          = round_val(safe_pct(fcf, revenue))        if (fcf is not None and revenue)   else None,
            capex_to_revenue_pct    = round_val(safe_pct(abs(capex), revenue)) if (capex and revenue)             else None,
            shareholder_return      = abs(divs or 0) + abs(buybacks or 0)      if (divs or buybacks)              else None,
        )

    # ------------------------------------------------------------------ #
    # Segment name cleaning                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def clean_segment_name(name: str) -> str:
        if ":" in name:
            name = name.split(":")[-1]
        name = name.replace("Member", "").replace("Segment", "")
        result = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
        result = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", result)
        result = re.sub(r"\s+", " ", result).strip()
        return result.replace(" And ", " & ").replace(" and ", " & ") or name

    # ------------------------------------------------------------------ #
    # Financial ratio computation                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_ratios(income: Dict[str, Any], balance: Dict[str, Any], cashflow: Dict[str, Any]) -> Dict[str, Any]:
        period     = income.get("period") or balance.get("period") or "Unknown"
        fiscal_year = income.get("fiscal_year") or balance.get("fiscal_year")

        # Inputs
        revenue       = income.get("revenue")
        cogs          = income.get("cost_of_revenue")
        gross_profit  = income.get("gross_profit")
        op_income     = income.get("operating_income")
        net_income    = income.get("net_income")
        interest_exp  = income.get("interest_expense")
        eps_diluted   = income.get("eps_diluted")
        ebitda        = income.get("ebitda")

        total_assets  = balance.get("total_assets")
        ca            = balance.get("current_assets")
        cl            = balance.get("current_liabilities")
        inventory     = balance.get("inventory")
        receivables   = balance.get("accounts_receivable")
        payables      = balance.get("accounts_payable")
        equity        = balance.get("total_stockholders_equity")
        cash          = balance.get("cash_and_equivalents")
        securities    = balance.get("marketable_securities")
        shares        = balance.get("shares_outstanding")
        total_debt    = balance.get("total_debt")

        fcf   = cashflow.get("free_cash_flow")
        capex = cashflow.get("capital_expenditures")
        sbc   = cashflow.get("stock_based_compensation")

        gm = round_val(safe_pct(gross_profit, revenue))
        if gm is None and revenue and cogs:
            gm = round_val(safe_pct(revenue - cogs, revenue))

        roic = None
        if net_income is not None and total_debt is not None and equity is not None:
            ic = equity + total_debt
            if ic > 0:
                roic = round_val(safe_pct(net_income, ic))

        profitability = asdict(ProfitabilityRatios(
            period=period, fiscal_year=fiscal_year,
            gross_margin_pct                = gm,
            operating_margin_pct            = round_val(safe_pct(op_income, revenue)),
            net_margin_pct                  = round_val(safe_pct(net_income, revenue)),
            return_on_assets_pct            = round_val(safe_pct(net_income, total_assets)) if (net_income and total_assets) else None,
            return_on_equity_pct            = round_val(safe_pct(net_income, equity))       if (net_income and equity and equity > 0) else None,
            return_on_invested_capital_pct  = roic,
            free_cash_flow_margin_pct       = round_val(safe_pct(fcf, revenue))             if fcf is not None else None,
        ))

        nd_ebitda = None
        if total_debt is not None and cash is not None and ebitda and ebitda > 0:
            nd_ebitda = round_val((total_debt - cash - (securities or 0)) / ebitda, 2)

        quick = round_val((ca - (inventory or 0)) / cl, 2) if (ca is not None and cl and cl > 0) else None

        leverage = asdict(LeverageRatios(
            period=period, fiscal_year=fiscal_year,
            debt_to_equity   = round_val(total_debt / equity, 2)      if (total_debt and equity and equity > 0)         else None,
            debt_to_assets   = round_val(total_debt / total_assets, 2) if (total_debt and total_assets and total_assets > 0) else None,
            interest_coverage= round_val(op_income / interest_exp, 2)  if (op_income and interest_exp and interest_exp > 0) else None,
            net_debt_to_ebitda = nd_ebitda,
            equity_multiplier= round_val(total_assets / equity, 2)    if (total_assets and equity and equity > 0)       else None,
            current_ratio    = round_val(ca / cl, 2)                   if (ca and cl and cl > 0)                        else None,
            quick_ratio      = quick,
        ))

        inv_t  = round_val(cogs / inventory, 2)      if (cogs and inventory and inventory > 0)      else None
        recv_t = round_val(revenue / receivables, 2) if (revenue and receivables and receivables > 0) else None
        pay_t  = round_val(cogs / payables, 2)       if (cogs and payables and payables > 0)         else None
        dso = round_val(365 / recv_t, 1) if recv_t else None
        dio = round_val(365 / inv_t,  1) if inv_t  else None
        dpo = round_val(365 / pay_t,  1) if pay_t  else None

        operating = asdict(OperatingRatios(
            period=period, fiscal_year=fiscal_year,
            asset_turnover          = round_val(revenue / total_assets, 2) if (revenue and total_assets and total_assets > 0) else None,
            inventory_turnover      = inv_t,
            receivables_turnover    = recv_t,
            payables_turnover       = pay_t,
            days_sales_outstanding  = dso,
            days_inventory_outstanding = dio,
            days_payable_outstanding   = dpo,
            cash_conversion_cycle   = round_val(dso + dio - dpo, 1) if (dso and dio and dpo) else None,
            capex_to_revenue_pct    = round_val(safe_pct(abs(capex), revenue)) if (capex and revenue and revenue > 0) else None,
            sbc_to_revenue_pct      = round_val(safe_pct(sbc, revenue))        if (sbc and revenue and revenue > 0)   else None,
        ))

        valuation = asdict(ValuationRatios(
            period=period, fiscal_year=fiscal_year,
            book_value_per_share    = round_val(equity / shares, 2)  if (equity and shares and shares > 0)           else None,
            earnings_per_share      = eps_diluted,
            revenue_per_share       = round_val(revenue / shares, 2) if (revenue and shares and shares > 0)          else None,
            free_cash_flow_per_share= round_val(fcf / shares, 2)     if (fcf is not None and shares and shares > 0)  else None,
        ))

        return {
            "period": period,
            "fiscal_year": fiscal_year,
            "profitability": profitability,
            "leverage": leverage,
            "valuation": valuation,
            "operating": operating,
        }

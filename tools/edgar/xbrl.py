from typing import Any, Dict, List, Optional

import pandas as pd


REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "Revenue",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]

COGS_CONCEPTS = [
    "CostOfGoodsAndServicesSold",
    "CostOfRevenue",
    "CostOfGoodsSold",
]

INCOME_STATEMENT_NAMES = {"income", "operations", "earnings", "profit", "loss"}

SPLIT_RATIO_CONCEPTS = [
    "StockholdersEquityNoteStockSplitConversionRatio1",
    "StockSplitConversionRatio",
]


def get_period_value(facts_view, concepts: List[str], fiscal_period: str, period_end: str) -> Optional[float]:
    for concept in concepts:
        try:
            df = facts_view.get_facts_by_concept(concept)
            if df is None or df.empty:
                continue
            filtered = df[
                (df["is_dimensioned"] == False) &
                (df["fiscal_period"] == fiscal_period) &
                (df["period_end"] == period_end)
            ]
            if filtered.empty:
                continue

            if len(filtered) > 1 and "statement_name" in filtered.columns:
                income_rows = filtered[
                    filtered["statement_name"].str.lower().apply(
                        lambda x: any(kw in str(x) for kw in INCOME_STATEMENT_NAMES)
                    )
                ]
                if not income_rows.empty:
                    filtered = income_rows

            if len(filtered) > 1:
                filtered = filtered.sort_values("numeric_value", ascending=False, key=abs)

            val = filtered.iloc[0]["numeric_value"]
            if pd.notna(val):
                return float(val)
        except Exception:
            continue
    return None


def get_current_period_value(facts_view, concepts: List[str], fiscal_period: str = "FY") -> Optional[float]:
    for concept in concepts:
        try:
            df = facts_view.get_facts_by_concept(concept)
            if df is None or df.empty:
                continue
            filtered = df[(df["is_dimensioned"] == False) & (df["fiscal_period"] == fiscal_period)]
            if filtered.empty:
                continue
            sorted_df = filtered.sort_values("fiscal_year", ascending=False)
            val = sorted_df.iloc[0]["numeric_value"]
            if pd.notna(val):
                return float(val)
        except Exception:
            continue
    return None


def get_all_periods_in_filing(facts_view, fiscal_period: str = "FY") -> List[Dict[str, Any]]:
    for concepts in [REVENUE_CONCEPTS, ["NetIncomeLoss"]]:
        for concept in concepts:
            try:
                df = facts_view.get_facts_by_concept(concept)
                if df is None or df.empty:
                    continue
                filtered = df[(df["is_dimensioned"] == False) & (df["fiscal_period"] == fiscal_period)]
                if filtered.empty:
                    continue
                periods = []
                seen_ends = set()
                sorted_df = filtered.sort_values("period_end", ascending=False)
                for _, row in sorted_df.iterrows():
                    pe = row["period_end"]
                    if pe in seen_ends or pd.isna(pe):
                        continue
                    seen_ends.add(pe)
                    fy = int(row["fiscal_year"]) if pd.notna(row["fiscal_year"]) else None
                    periods.append({"period_end": str(pe), "fiscal_year": fy})
                if periods:
                    return periods
            except Exception:
                continue
    return []


def detect_split_ratio(xbrl) -> Optional[float]:
    facts = xbrl.facts
    for concept in SPLIT_RATIO_CONCEPTS:
        try:
            df = facts.get_facts_by_concept(concept)
            if df is not None and not df.empty:
                val = df.iloc[0]["numeric_value"]
                if pd.notna(val) and val > 1:
                    return float(val)
        except Exception:
            continue
    return None


def detect_fiscal_period(xbrl) -> str:
    try:
        for rp in xbrl.reporting_periods:
            if rp.get("period_type") == "Quarterly" and rp.get("fiscal_period"):
                return rp["fiscal_period"]
    except Exception:
        pass
    return "Q1"


def safe_pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is not None and denominator is not None and denominator != 0:
        return numerator / denominator * 100
    return None


def round_val(val: Optional[float], decimals: int = 2) -> Optional[float]:
    return round(val, decimals) if val is not None else None

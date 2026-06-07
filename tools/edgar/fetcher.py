"""EdgarFetcher — network I/O only, no MCP wiring."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

import pandas as pd
from edgar import Company, set_identity

from tools.edgar.models import (
    BalanceSheetMetrics,
    CashFlowMetrics,
    GrowthMomentum,
    IncomeMetrics,
    SegmentRevenue,
)
from tools.edgar.utils import BS_CONCEPTS, CF_CONCEPTS, EdgarUtils
from tools.edgar.xbrl import (
    REVENUE_CONCEPTS,
    detect_fiscal_period,
    detect_split_ratio,
    get_all_periods_in_filing,
    get_current_period_value,
    get_period_value,
    round_val,
)

set_identity("Stock Analysis Tool contact@example.com")


class EdgarFetcher:
    """Fetches structured financial data from SEC EDGAR XBRL filings."""

    # ------------------------------------------------------------------ #
    # Income statement                                                     #
    # ------------------------------------------------------------------ #

    def fetch_income_data(
        self,
        company: Company,
        num_years: int = 5,
        num_quarters: int = 4,
        include_segments: bool = True,
    ) -> Dict[str, Any]:
        annual, periods_in_latest, split_ratio, latest_xbrl = {}, set(), None, None

        for idx, filing in enumerate(company.get_filings(form="10-K").head(max(num_years, (num_years // 2) + 1))):
            xbrl = filing.xbrl()
            if not xbrl:
                continue
            if idx == 0:
                latest_xbrl = xbrl
                split_ratio = detect_split_ratio(xbrl)
            facts = xbrl.facts
            for pi in get_all_periods_in_filing(facts, "FY"):
                pe = pi["period_end"]
                if pe in annual:
                    continue
                if idx == 0:
                    periods_in_latest.add(pe)
                m = EdgarUtils.extract_income(facts, pe, "FY", "annual", str(filing.filing_date), pi["fiscal_year"])
                if m:
                    annual[pe] = m
            if len(annual) >= num_years:
                break

        annual_list: List[IncomeMetrics] = sorted(annual.values(), key=lambda m: m.period, reverse=True)[:num_years]

        if split_ratio:
            latest_pes = {pe for pe, m in annual.items() if pe in periods_in_latest}
            for pe, m in annual.items():
                if pe not in latest_pes:
                    EdgarUtils.apply_split(m, split_ratio)

        # Quarterly
        quarterly: List[IncomeMetrics] = []
        seen_q: set = set()
        ref_shares = None
        if split_ratio and latest_xbrl:
            ref_shares = get_current_period_value(
                latest_xbrl.facts,
                ["WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"],
                "FY",
            )
        for filing in company.get_filings(form="10-Q").head(num_quarters + 2):
            xbrl = filing.xbrl()
            if not xbrl:
                continue
            fp = detect_fiscal_period(xbrl)
            periods = get_all_periods_in_filing(xbrl.facts, fp)
            if not periods:
                continue
            pe = periods[0]["period_end"]
            if pe in seen_q:
                continue
            seen_q.add(pe)
            m = EdgarUtils.extract_income(xbrl.facts, pe, fp, "quarterly", str(filing.filing_date), periods[0]["fiscal_year"])
            if m:
                if split_ratio and ref_shares and m.shares_outstanding_diluted:
                    if ref_shares / m.shares_outstanding_diluted > split_ratio * 0.8:
                        EdgarUtils.apply_split(m, split_ratio)
                quarterly.append(m)
            if len(quarterly) >= num_quarters:
                break

        yoy_growth = [EdgarUtils.growth_momentum(annual_list[i], annual_list[i + 1], "YoY") for i in range(len(annual_list) - 1)]
        qoq_growth = [EdgarUtils.growth_momentum(quarterly[i], quarterly[i + 1], "QoQ") for i in range(len(quarterly) - 1)]
        segments   = self._fetch_segments(company) if include_segments else []
        summary    = self._income_summary(annual_list, quarterly, yoy_growth, qoq_growth, segments)

        return {
            "annual_statements":  [asdict(m) for m in annual_list],
            "quarterly_statements": [asdict(m) for m in quarterly],
            "yoy_growth":         [asdict(g) for g in yoy_growth],
            "qoq_growth":         [asdict(g) for g in qoq_growth],
            "revenue_segments":   [asdict(s) for s in segments],
            "summary":            summary,
        }

    def _fetch_segments(self, company: Company) -> List[SegmentRevenue]:
        segments: List[SegmentRevenue] = []
        try:
            filing = company.get_filings(form="10-K").head(1)[0]
            xbrl   = filing.xbrl()
            if not xbrl:
                return []
            total_rev = get_current_period_value(xbrl.facts, REVENUE_CONCEPTS, "FY")
            for axis in ["srt_ProductOrServiceAxis", "us-gaap_StatementBusinessSegmentsAxis"]:
                try:
                    pivoted = xbrl.facts.pivot_by_dimension(axis)
                    if pivoted is None or pivoted.empty:
                        continue
                    mask = pd.Series([False] * len(pivoted), index=pivoted.index)
                    for rc in REVENUE_CONCEPTS:
                        mask |= pivoted["concept"].str.contains(rc, case=False, na=False)
                    rev_data = pivoted[mask]
                    if rev_data.empty:
                        continue
                    member_cols = [c for c in rev_data.columns if c not in ("concept", "label")]
                    for _, row in rev_data.iterrows():
                        label = row.get("label", "")
                        if label.lower() in ("products", "services", "product", "service"):
                            continue
                        val = next((float(row[c]) for c in member_cols if pd.notna(row[c])), None)
                        if not val or val <= 0:
                            continue
                        pct = (val / total_rev * 100) if total_rev else None
                        segments.append(SegmentRevenue(
                            segment_name       = label or EdgarUtils.clean_segment_name(member_cols[0]),
                            revenue            = val,
                            percentage_of_total= round_val(pct),
                            period             = f"FY{xbrl.reporting_periods[0].get('fiscal_year', '')}",
                        ))
                    if segments:
                        break
                except Exception:
                    continue
            segments.sort(key=lambda s: s.revenue or 0, reverse=True)
            if segments and total_rev:
                total_pct = sum(s.percentage_of_total or 0 for s in segments)
                while total_pct > 110 and len(segments) > 1:
                    removed = segments.pop(0)
                    total_pct -= removed.percentage_of_total or 0
                for s in segments:
                    if s.revenue:
                        s.percentage_of_total = round_val(s.revenue / total_rev * 100)
        except Exception:
            pass
        return segments

    @staticmethod
    def _income_summary(
        annual: List[IncomeMetrics],
        quarterly: List[IncomeMetrics],
        yoy: List[GrowthMomentum],
        qoq: List[GrowthMomentum],
        segments: List[SegmentRevenue],
    ) -> Dict[str, Any]:
        s: Dict[str, Any] = {}
        if annual:
            la = annual[0]
            s.update({
                "latest_annual_period":       la.period,
                "latest_annual_revenue":      la.revenue,
                "latest_annual_net_income":   la.net_income,
                "latest_gross_margin_pct":    la.gross_margin_pct,
                "latest_operating_margin_pct":la.operating_margin_pct,
                "latest_net_margin_pct":      la.net_margin_pct,
                "latest_ebitda":              la.ebitda,
            })
        if quarterly:
            lq = quarterly[0]
            s.update({"latest_quarter": lq.period, "latest_quarter_revenue": lq.revenue, "latest_quarter_net_income": lq.net_income})
        if yoy:
            s.update({
                "latest_yoy_revenue_growth_pct":    yoy[0].revenue_growth_pct,
                "latest_yoy_net_income_growth_pct": yoy[0].net_income_growth_pct,
                "latest_yoy_eps_growth_pct":        yoy[0].eps_growth_pct,
            })
        if qoq:
            s["latest_qoq_revenue_growth_pct"] = qoq[0].revenue_growth_pct

        revenues = [m.revenue for m in annual if m.revenue and m.revenue > 0]
        if len(revenues) >= 3:
            n = len(revenues) - 1
            s["revenue_cagr_pct"] = round_val(((revenues[0] / revenues[-1]) ** (1 / n) - 1) * 100)
        net_incomes = [m.net_income for m in annual if m.net_income and m.net_income > 0]
        if len(net_incomes) >= 3:
            n = len(net_incomes) - 1
            s["net_income_cagr_pct"] = round_val(((net_incomes[0] / net_incomes[-1]) ** (1 / n) - 1) * 100)
        if len(annual) >= 2:
            fm, lm = annual[0].gross_margin_pct, annual[-1].gross_margin_pct
            if fm is not None and lm is not None:
                s["gross_margin_trend"] = "expanding" if fm > lm + 0.5 else "contracting" if fm < lm - 0.5 else "stable"
        if annual:
            prof = sum(1 for m in annual if m.net_income and m.net_income > 0)
            s["profitable_years_out_of"] = f"{prof}/{len(annual)}"
        if segments:
            s.update({
                "top_revenue_segment":         segments[0].segment_name,
                "top_segment_revenue":         segments[0].revenue,
                "top_segment_pct_of_total":    segments[0].percentage_of_total,
                "num_identified_segments":     len(segments),
            })
            if len(segments) >= 2:
                s["revenue_concentration_top2_pct"] = round_val(
                    (segments[0].percentage_of_total or 0) + (segments[1].percentage_of_total or 0)
                )
        return s

    # ------------------------------------------------------------------ #
    # Balance sheet                                                        #
    # ------------------------------------------------------------------ #

    def fetch_balance_sheet_data(self, company: Company, num_years: int = 5) -> List[BalanceSheetMetrics]:
        collected: Dict[str, BalanceSheetMetrics] = {}
        for filing in company.get_filings(form="10-K").head(num_years):
            xbrl = filing.xbrl()
            if not xbrl:
                continue
            for date_info in EdgarUtils.balance_sheet_dates(xbrl.facts, num_years):
                pi = date_info["period_instant"]
                if pi in collected:
                    continue
                m = EdgarUtils.extract_balance_sheet(xbrl.facts, pi, date_info["fiscal_year"], str(filing.filing_date))
                if m:
                    collected[pi] = m
            if len(collected) >= num_years:
                break
        return sorted(collected.values(), key=lambda m: m.period, reverse=True)[:num_years]

    # ------------------------------------------------------------------ #
    # Cash flow                                                            #
    # ------------------------------------------------------------------ #

    def fetch_cash_flow_data(self, company: Company, num_years: int = 5) -> List[CashFlowMetrics]:
        collected: Dict[str, CashFlowMetrics] = {}
        for filing in company.get_filings(form="10-K").head(num_years):
            xbrl = filing.xbrl()
            if not xbrl:
                continue
            facts = xbrl.facts
            for pi in get_all_periods_in_filing(facts, "FY"):
                pe = pi["period_end"]
                if pe in collected:
                    continue
                fy = pi["fiscal_year"] or (int(pe[:4]) if pe else None)
                m  = EdgarUtils.extract_cash_flow(facts, pe, fy, str(filing.filing_date))
                if m:
                    collected[pe] = m
            if len(collected) >= num_years:
                break
        return sorted(collected.values(), key=lambda m: m.period, reverse=True)[:num_years]

    # ------------------------------------------------------------------ #
    # Company profile                                                      #
    # ------------------------------------------------------------------ #

    def fetch_company_profile_data(self, company: Company) -> Dict[str, Any]:
        def safe(attr, default=None):
            return getattr(company, attr, default)

        profile: Dict[str, Any] = {
            "company_name":                 company.name,
            "ticker":                       company.tickers[0].upper() if getattr(company, "tickers", None) else "",
            "cik":                          company.cik,
            "sic":                          company.sic,
            "industry":                     safe("industry"),
            "exchanges":                    company.get_exchanges() if hasattr(company, "get_exchanges") else [],
            "fiscal_year_end":              safe("fiscal_year_end"),
            "filer_category":               safe("filer_category"),
            "is_large_accelerated_filer":   safe("is_large_accelerated_filer", False),
            "is_smaller_reporting_company": safe("is_smaller_reporting_company", False),
            "is_emerging_growth_company":   safe("is_emerging_growth_company", False),
        }

        shares_outstanding = safe("shares_outstanding")
        public_float       = safe("public_float")
        shares: Dict[str, Any] = {}
        if shares_outstanding:
            shares["shares_outstanding"] = shares_outstanding
        if public_float:
            shares["public_float"] = public_float
        if shares_outstanding and public_float and shares_outstanding > 0:
            shares["implied_price_per_share"] = round(public_float / shares_outstanding, 2)
        profile["shares"] = shares

        try:
            tenk = company.latest_tenk
            if tenk:
                profile["latest_10k_filing_date"] = str(tenk.filing_date) if hasattr(tenk, "filing_date") else None
                try:
                    profile["business_overview"] = str(tenk.business).strip() if tenk.business else None
                except Exception:
                    profile["business_overview"] = None
                try:
                    profile["risk_factors"] = str(tenk.risk_factors).strip() if tenk.risk_factors else None
                except Exception:
                    profile["risk_factors"] = None
        except Exception:
            profile.update({"latest_10k_filing_date": None, "business_overview": None, "risk_factors": None})

        return profile
